"""
Sistema de simulaciones de caos para pruebas de recuperación.

Este módulo proporciona funcionalidades para realizar pruebas de caos,
que permiten verificar la resiliencia del sistema ante fallos inesperados.
"""

import logging
import time
import asyncio
import random
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import threading
import signal
import os
import gc
import socket

# Configurar logger
logger = logging.getLogger(__name__)


class ChaosEventType(str, Enum):
    """Tipos de eventos de caos."""

    SERVICE_FAILURE = "service_failure"  # Fallo de un servicio
    NETWORK_LATENCY = "network_latency"  # Latencia de red
    NETWORK_PARTITION = "network_partition"  # Partición de red
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # Agotamiento de recursos
    MEMORY_PRESSURE = "memory_pressure"  # Presión de memoria
    CPU_PRESSURE = "cpu_pressure"  # Presión de CPU
    DISK_PRESSURE = "disk_pressure"  # Presión de disco
    CLOCK_SKEW = "clock_skew"  # Desviación del reloj
    PROCESS_KILL = "process_kill"  # Matar un proceso
    RANDOM_EXCEPTION = "random_exception"  # Excepción aleatoria


class ChaosEvent:
    """Evento de caos para pruebas de resiliencia."""

    def __init__(
        self,
        event_id: str,
        event_type: ChaosEventType,
        target: str,
        duration: int,  # Duración en segundos
        intensity: float = 1.0,  # Intensidad del evento (0.0-1.0)
        delay: int = 0,  # Retraso antes de iniciar el evento en segundos
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa un evento de caos.

        Args:
            event_id: Identificador único del evento
            event_type: Tipo de evento
            target: Objetivo del evento (servicio, recurso, etc.)
            duration: Duración en segundos
            intensity: Intensidad del evento (0.0-1.0)
            delay: Retraso antes de iniciar el evento en segundos
            description: Descripción del evento
            parameters: Parámetros adicionales para el evento
        """
        self.event_id = event_id
        self.event_type = event_type
        self.target = target
        self.duration = duration
        self.intensity = intensity
        self.delay = delay
        self.description = description or f"Evento de caos {event_type} en {target}"
        self.parameters = parameters or {}

        self.start_time = None
        self.end_time = None
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.result = None
        self.error = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el evento a un diccionario.

        Returns:
            Diccionario con los datos del evento
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "target": self.target,
            "duration": self.duration,
            "intensity": self.intensity,
            "delay": self.delay,
            "description": self.description,
            "parameters": self.parameters,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class ChaosTestingManager:
    """
    Gestor de pruebas de caos.

    Esta clase proporciona funcionalidades para realizar pruebas de caos,
    que permiten verificar la resiliencia del sistema ante fallos inesperados.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "ChaosTestingManager":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(ChaosTestingManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Inicializa el gestor de pruebas de caos."""
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        # Registro de eventos
        self.events: Dict[str, ChaosEvent] = {}

        # Registro de tareas en ejecución
        self.running_tasks: Dict[str, asyncio.Task] = {}

        # Registro de handlers para tipos de eventos
        self.event_handlers: Dict[ChaosEventType, Callable] = {
            ChaosEventType.SERVICE_FAILURE: self._handle_service_failure,
            ChaosEventType.NETWORK_LATENCY: self._handle_network_latency,
            ChaosEventType.NETWORK_PARTITION: self._handle_network_partition,
            ChaosEventType.RESOURCE_EXHAUSTION: self._handle_resource_exhaustion,
            ChaosEventType.MEMORY_PRESSURE: self._handle_memory_pressure,
            ChaosEventType.CPU_PRESSURE: self._handle_cpu_pressure,
            ChaosEventType.DISK_PRESSURE: self._handle_disk_pressure,
            ChaosEventType.CLOCK_SKEW: self._handle_clock_skew,
            ChaosEventType.PROCESS_KILL: self._handle_process_kill,
            ChaosEventType.RANDOM_EXCEPTION: self._handle_random_exception,
        }

        # Registro de callbacks para notificaciones
        self.callbacks: List[Callable[[ChaosEvent], None]] = []

        # Lock para operaciones concurrentes
        self.lock = asyncio.Lock()

        # Estado global
        self.is_enabled = False
        self.safe_mode = True  # Modo seguro (no ejecuta eventos destructivos)

        self._initialized = True

        logger.info("ChaosTestingManager inicializado")

    async def enable(self, safe_mode: bool = True) -> None:
        """
        Habilita las pruebas de caos.

        Args:
            safe_mode: Si se debe ejecutar en modo seguro (sin eventos destructivos)
        """
        async with self.lock:
            self.is_enabled = True
            self.safe_mode = safe_mode
            logger.info(f"Pruebas de caos habilitadas (modo seguro: {safe_mode})")

    async def disable(self) -> None:
        """Deshabilita las pruebas de caos."""
        async with self.lock:
            self.is_enabled = False

            # Cancelar todas las tareas en ejecución
            for task_id, task in self.running_tasks.items():
                if not task.done():
                    task.cancel()

            self.running_tasks.clear()

            logger.info("Pruebas de caos deshabilitadas")

    async def register_event(self, event: ChaosEvent) -> str:
        """
        Registra un evento de caos.

        Args:
            event: Evento a registrar

        Returns:
            ID del evento
        """
        async with self.lock:
            self.events[event.event_id] = event
            logger.info(
                f"Evento de caos registrado: {event.event_id} ({event.event_type})"
            )
            return event.event_id

    async def start_event(self, event_id: str) -> bool:
        """
        Inicia un evento de caos.

        Args:
            event_id: ID del evento a iniciar

        Returns:
            True si se ha iniciado, False si no se ha podido iniciar
        """
        if not self.is_enabled:
            logger.warning(
                "No se puede iniciar el evento, las pruebas de caos están deshabilitadas"
            )
            return False

        async with self.lock:
            event = self.events.get(event_id)
            if not event:
                logger.warning(f"Evento {event_id} no encontrado")
                return False

            if event.status != "pending":
                logger.warning(
                    f"No se puede iniciar el evento {event_id}, estado actual: {event.status}"
                )
                return False

            # Verificar si es un evento destructivo en modo seguro
            if self.safe_mode and event.event_type in [ChaosEventType.PROCESS_KILL]:
                logger.warning(
                    f"No se puede iniciar el evento {event_id}, es destructivo y el modo seguro está activado"
                )
                return False

            # Crear tarea para ejecutar el evento
            task = asyncio.create_task(self._execute_event(event))
            self.running_tasks[event_id] = task

            logger.info(f"Evento de caos iniciado: {event_id}")
            return True

    async def cancel_event(self, event_id: str) -> bool:
        """
        Cancela un evento de caos en ejecución.

        Args:
            event_id: ID del evento a cancelar

        Returns:
            True si se ha cancelado, False si no se ha podido cancelar
        """
        async with self.lock:
            event = self.events.get(event_id)
            if not event:
                logger.warning(f"Evento {event_id} no encontrado")
                return False

            if event.status != "running":
                logger.warning(
                    f"No se puede cancelar el evento {event_id}, estado actual: {event.status}"
                )
                return False

            # Cancelar tarea
            task = self.running_tasks.get(event_id)
            if task and not task.done():
                task.cancel()

            # Actualizar estado
            event.status = "cancelled"
            event.end_time = datetime.now()

            logger.info(f"Evento de caos cancelado: {event_id}")

            # Notificar
            await self._notify_event_update(event)

            return True

    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información sobre un evento.

        Args:
            event_id: ID del evento

        Returns:
            Información del evento o None si no existe
        """
        event = self.events.get(event_id)
        if not event:
            return None

        return event.to_dict()

    async def get_all_events(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene información sobre todos los eventos.

        Returns:
            Diccionario con información de todos los eventos
        """
        return {event_id: event.to_dict() for event_id, event in self.events.items()}

    async def register_callback(self, callback: Callable[[ChaosEvent], None]) -> None:
        """
        Registra un callback para notificaciones de eventos.

        Args:
            callback: Función a llamar cuando se actualice un evento
        """
        self.callbacks.append(callback)

    async def unregister_callback(self, callback: Callable[[ChaosEvent], None]) -> bool:
        """
        Elimina un callback del registro.

        Args:
            callback: Función a eliminar

        Returns:
            True si se ha eliminado, False si no existía
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            return True

        return False

    async def _execute_event(self, event: ChaosEvent) -> None:
        """
        Ejecuta un evento de caos.

        Args:
            event: Evento a ejecutar
        """
        try:
            # Esperar el retraso inicial
            if event.delay > 0:
                await asyncio.sleep(event.delay)

            # Actualizar estado
            event.status = "running"
            event.start_time = datetime.now()

            # Notificar
            await self._notify_event_update(event)

            # Obtener handler para el tipo de evento
            handler = self.event_handlers.get(event.event_type)
            if not handler:
                raise ValueError(
                    f"No hay handler para el tipo de evento {event.event_type}"
                )

            # Ejecutar handler
            result = await handler(event)

            # Actualizar estado
            event.status = "completed"
            event.end_time = datetime.now()
            event.result = result

            logger.info(f"Evento de caos completado: {event.event_id}")

        except asyncio.CancelledError:
            # El evento fue cancelado
            event.status = "cancelled"
            event.end_time = datetime.now()
            logger.info(f"Evento de caos cancelado: {event.event_id}")

        except Exception as e:
            # Error durante la ejecución
            event.status = "failed"
            event.end_time = datetime.now()
            event.error = str(e)
            logger.error(
                f"Error en evento de caos {event.event_id}: {e}", exc_info=True
            )

        finally:
            # Eliminar tarea del registro
            self.running_tasks.pop(event.event_id, None)

            # Notificar
            await self._notify_event_update(event)

    async def _handle_service_failure(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de fallo de servicio.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener servicio objetivo
        target_service = event.target

        # Importar gestor de modos degradados
        from core.degraded_mode import (
            degraded_mode_manager,
            DegradationReason,
            DegradationLevel,
        )

        # Calcular nivel de degradación según intensidad
        level = DegradationLevel.LOW
        if event.intensity >= 0.3:
            level = DegradationLevel.MEDIUM
        if event.intensity >= 0.6:
            level = DegradationLevel.HIGH
        if event.intensity >= 0.9:
            level = DegradationLevel.CRITICAL

        # Marcar servicio como no disponible
        await degraded_mode_manager.set_service_unavailable(
            service_id=target_service,
            reason=DegradationReason.AUTOMATIC,
            message=f"Fallo simulado por prueba de caos (evento {event.event_id})",
            level=level,
        )

        logger.info(
            f"Servicio {target_service} marcado como no disponible (evento {event.event_id})"
        )

        # Esperar la duración del evento
        await asyncio.sleep(event.duration)

        # Restaurar servicio
        await degraded_mode_manager.set_service_available(target_service)

        logger.info(f"Servicio {target_service} restaurado (evento {event.event_id})")

        return {
            "service": target_service,
            "degradation_level": level.value,
            "duration": event.duration,
        }

    async def _handle_network_latency(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de latencia de red.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        target_host = event.target
        latency_ms = int(event.parameters.get("latency_ms", 100 * event.intensity))
        jitter_ms = int(event.parameters.get("jitter_ms", 20 * event.intensity))

        # Crear función de interceptación para simular latencia
        original_socket_connect = socket.socket.connect

        def delayed_connect(self, address):
            # Solo aplicar latencia al host objetivo
            if isinstance(address, tuple) and address[0] == target_host:
                # Calcular latencia con jitter
                delay = latency_ms + random.randint(-jitter_ms, jitter_ms)
                delay = max(1, delay)  # Asegurar que la latencia sea positiva
                time.sleep(delay / 1000.0)  # Convertir a segundos

            # Llamar a la función original
            return original_socket_connect(self, address)

        # Aplicar monkey patch
        socket.socket.connect = delayed_connect

        logger.info(
            f"Latencia de red aplicada a {target_host}: {latency_ms}ms ±{jitter_ms}ms (evento {event.event_id})"
        )

        try:
            # Esperar la duración del evento
            await asyncio.sleep(event.duration)
        finally:
            # Restaurar función original
            socket.socket.connect = original_socket_connect

            logger.info(
                f"Latencia de red eliminada para {target_host} (evento {event.event_id})"
            )

        return {
            "target_host": target_host,
            "latency_ms": latency_ms,
            "jitter_ms": jitter_ms,
            "duration": event.duration,
        }

    async def _handle_network_partition(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de partición de red.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        target_hosts = event.parameters.get("target_hosts", [event.target])
        drop_rate = event.parameters.get("drop_rate", event.intensity)

        # Crear función de interceptación para simular partición
        original_socket_connect = socket.socket.connect

        def partitioned_connect(self, address):
            # Verificar si el host está en la lista de objetivos
            if isinstance(address, tuple) and address[0] in target_hosts:
                # Simular pérdida de paquetes según la tasa de drop
                if random.random() < drop_rate:
                    # Simular timeout
                    time.sleep(2)  # Esperar un tiempo antes de fallar
                    raise socket.timeout("Simulated timeout by chaos test")

            # Llamar a la función original
            return original_socket_connect(self, address)

        # Aplicar monkey patch
        socket.socket.connect = partitioned_connect

        logger.info(
            f"Partición de red aplicada a {target_hosts} con tasa de pérdida {drop_rate} (evento {event.event_id})"
        )

        try:
            # Esperar la duración del evento
            await asyncio.sleep(event.duration)
        finally:
            # Restaurar función original
            socket.socket.connect = original_socket_connect

            logger.info(f"Partición de red eliminada (evento {event.event_id})")

        return {
            "target_hosts": target_hosts,
            "drop_rate": drop_rate,
            "duration": event.duration,
        }

    async def _handle_resource_exhaustion(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de agotamiento de recursos.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        resource_type = event.parameters.get("resource_type", "memory")

        if resource_type == "memory":
            return await self._handle_memory_pressure(event)
        elif resource_type == "cpu":
            return await self._handle_cpu_pressure(event)
        elif resource_type == "disk":
            return await self._handle_disk_pressure(event)
        else:
            raise ValueError(f"Tipo de recurso no soportado: {resource_type}")

    async def _handle_memory_pressure(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de presión de memoria.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        target_mb = event.parameters.get("target_mb", int(100 * event.intensity))

        # Crear lista para almacenar referencias a los objetos creados
        memory_hogs = []

        # Calcular cuántos bloques de 1MB necesitamos
        num_blocks = target_mb

        logger.info(
            f"Aplicando presión de memoria: {target_mb}MB (evento {event.event_id})"
        )

        # Crear bloques de memoria (cada uno de aproximadamente 1MB)
        for _ in range(num_blocks):
            # Crear un bloque de 1MB (1024 * 1024 bytes)
            block = bytearray(1024 * 1024)
            memory_hogs.append(block)

            # Pequeña pausa para no bloquear completamente el event loop
            if _ % 10 == 0:
                await asyncio.sleep(0.01)

        logger.info(
            f"Presión de memoria aplicada: {len(memory_hogs)}MB (evento {event.event_id})"
        )

        try:
            # Esperar la duración del evento
            await asyncio.sleep(event.duration)
        finally:
            # Liberar memoria
            del memory_hogs
            gc.collect()

            logger.info(f"Presión de memoria liberada (evento {event.event_id})")

        return {
            "target_mb": target_mb,
            "actual_mb": len(memory_hogs),
            "duration": event.duration,
        }

    async def _handle_cpu_pressure(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de presión de CPU.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        cpu_usage = event.parameters.get("cpu_usage", event.intensity)
        num_cores = event.parameters.get("num_cores", 1)

        # Crear workers para consumir CPU
        workers = []
        stop_event = threading.Event()

        def cpu_worker():
            # Bucle que consume CPU hasta que se establece el evento de parada
            while not stop_event.is_set():
                # Ajustar la intensidad del consumo según el uso deseado
                start_time = time.time()

                # Consumir CPU durante un porcentaje del tiempo
                while time.time() - start_time < 0.01 * cpu_usage:
                    # Operación intensiva en CPU
                    _ = [i * i for i in range(1000)]

                # Dormir durante el resto del tiempo
                time.sleep(0.01 * (1 - cpu_usage))

        logger.info(
            f"Aplicando presión de CPU: {cpu_usage*100}% en {num_cores} cores (evento {event.event_id})"
        )

        # Crear y arrancar workers
        for _ in range(num_cores):
            worker = threading.Thread(target=cpu_worker)
            worker.daemon = True
            worker.start()
            workers.append(worker)

        try:
            # Esperar la duración del evento
            await asyncio.sleep(event.duration)
        finally:
            # Detener workers
            stop_event.set()

            # Esperar a que terminen
            for worker in workers:
                worker.join(timeout=1.0)

            logger.info(f"Presión de CPU liberada (evento {event.event_id})")

        return {
            "cpu_usage": cpu_usage,
            "num_cores": num_cores,
            "duration": event.duration,
        }

    async def _handle_disk_pressure(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de presión de disco.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        target_path = event.parameters.get("target_path", "/tmp")
        target_mb = event.parameters.get("target_mb", int(100 * event.intensity))

        # Crear archivo temporal
        import tempfile

        logger.info(
            f"Aplicando presión de disco: {target_mb}MB en {target_path} (evento {event.event_id})"
        )

        temp_file = None
        try:
            # Crear archivo temporal en la ruta especificada
            temp_file = tempfile.NamedTemporaryFile(dir=target_path, delete=False)

            # Escribir datos en bloques de 1MB
            for _ in range(target_mb):
                temp_file.write(b"0" * (1024 * 1024))

                # Pequeña pausa para no bloquear completamente el event loop
                if _ % 10 == 0:
                    await asyncio.sleep(0.01)

            # Forzar escritura a disco
            temp_file.flush()
            os.fsync(temp_file.fileno())

            logger.info(
                f"Presión de disco aplicada: {target_mb}MB en {temp_file.name} (evento {event.event_id})"
            )

            # Esperar la duración del evento
            await asyncio.sleep(event.duration)

        finally:
            # Eliminar archivo temporal
            if temp_file:
                temp_file_name = temp_file.name
                temp_file.close()
                try:
                    os.unlink(temp_file_name)
                except Exception as e:
                    logger.error(f"Error al eliminar archivo temporal: {e}")

            logger.info(f"Presión de disco liberada (evento {event.event_id})")

        return {
            "target_path": target_path,
            "target_mb": target_mb,
            "duration": event.duration,
        }

    async def _handle_clock_skew(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de desviación del reloj.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        skew_seconds = event.parameters.get("skew_seconds", int(60 * event.intensity))

        # Guardar la función original
        original_time = time.time

        # Crear función de interceptación para simular desviación del reloj
        def skewed_time():
            return original_time() + skew_seconds

        # Aplicar monkey patch
        time.time = skewed_time

        logger.info(
            f"Desviación del reloj aplicada: {skew_seconds} segundos (evento {event.event_id})"
        )

        try:
            # Esperar la duración del evento
            await asyncio.sleep(event.duration)
        finally:
            # Restaurar función original
            time.time = original_time

            logger.info(f"Desviación del reloj eliminada (evento {event.event_id})")

        return {"skew_seconds": skew_seconds, "duration": event.duration}

    async def _handle_process_kill(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de matar un proceso.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Este evento solo se ejecuta si no estamos en modo seguro
        if self.safe_mode:
            raise ValueError(
                "No se puede ejecutar el evento de matar proceso en modo seguro"
            )

        # Obtener parámetros
        signal_type = event.parameters.get("signal", "SIGTERM")

        # Convertir string a señal
        if isinstance(signal_type, str):
            signal_type = getattr(signal, signal_type)

        logger.warning(
            f"¡ATENCIÓN! Enviando señal {signal_type} al proceso actual (evento {event.event_id})"
        )

        # Enviar señal al proceso actual
        os.kill(os.getpid(), signal_type)

        # Nunca llegaremos aquí si la señal mata el proceso
        return {"signal": signal_type, "pid": os.getpid()}

    async def _handle_random_exception(self, event: ChaosEvent) -> Dict[str, Any]:
        """
        Maneja un evento de excepción aleatoria.

        Args:
            event: Evento a manejar

        Returns:
            Resultado del evento
        """
        # Obtener parámetros
        exception_type = event.parameters.get("exception_type", "RuntimeError")
        message = event.parameters.get(
            "message",
            f"Excepción simulada por prueba de caos (evento {event.event_id})",
        )

        # Lista de posibles excepciones
        exceptions = {
            "RuntimeError": RuntimeError,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "AttributeError": AttributeError,
            "MemoryError": MemoryError,
            "IOError": IOError,
            "OSError": OSError,
            "TimeoutError": TimeoutError,
        }

        # Obtener clase de excepción
        exception_class = exceptions.get(exception_type, RuntimeError)

        # Lanzar excepción
        logger.warning(
            f"Lanzando excepción {exception_type}: {message} (evento {event.event_id})"
        )
        raise exception_class(message)


# Instancia global para uso en toda la aplicación
chaos_testing_manager = ChaosTestingManager()
