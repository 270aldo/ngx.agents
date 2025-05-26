"""
Servidor A2A (Agent-to-Agent) optimizado para NGX Agents.

Este módulo implementa un servidor A2A mejorado con comunicación asíncrona,
mecanismos de resiliencia y monitoreo avanzado para la comunicación entre agentes.
"""

import asyncio
import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional, Callable

from core.logging_config import get_logger

# Intentar importar telemetry_manager del módulo real, si falla usar el mock
try:
    from core.telemetry import telemetry_manager
except ImportError:
    from tests.mocks.core.telemetry import telemetry_manager


# Configurar logger
logger = get_logger(__name__)


class MessagePriority(Enum):
    """Prioridades para mensajes entre agentes."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class CircuitBreakerState(Enum):
    """Estados posibles del Circuit Breaker."""

    CLOSED = 0  # Funcionamiento normal
    OPEN = 1  # Bloqueando llamadas
    HALF_OPEN = 2  # Probando recuperación


class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker.

    Protege contra fallos en cascada al detectar errores y
    bloquear temporalmente las llamadas a un servicio con problemas.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 2,
    ):
        """
        Inicializa el Circuit Breaker.

        Args:
            name: Nombre identificativo
            failure_threshold: Número de fallos para abrir el circuito
            recovery_timeout: Tiempo en segundos antes de probar recuperación
            half_open_max_calls: Máximo de llamadas en estado half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        # Estado actual
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0

        # Estadísticas
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.prevented_calls = 0

        # Lock para operaciones concurrentes
        self._lock = asyncio.Lock()

        logger.info(f"Circuit Breaker '{name}' inicializado")

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función protegida por el Circuit Breaker.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales para la función
            **kwargs: Argumentos con nombre para la función

        Returns:
            Any: Resultado de la función

        Raises:
            Exception: Si el circuito está abierto o la función falla
        """
        async with self._lock:
            self.total_calls += 1

            # Verificar si el circuito está abierto
            if self.state == CircuitBreakerState.OPEN:
                # Verificar si ha pasado el tiempo de recuperación
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    logger.info(
                        f"Circuit Breaker '{self.name}' cambiando a estado HALF_OPEN"
                    )
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    self.prevented_calls += 1
                    raise Exception(f"Circuit Breaker '{self.name}' está abierto")

            # Verificar si estamos en half-open y ya alcanzamos el máximo de llamadas
            if (
                self.state == CircuitBreakerState.HALF_OPEN
                and self.half_open_calls >= self.half_open_max_calls
            ):
                self.prevented_calls += 1
                raise Exception(
                    f"Circuit Breaker '{self.name}' ha alcanzado el máximo de llamadas en HALF_OPEN"
                )

            # Incrementar contador de llamadas en half-open
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_calls += 1

        # Ejecutar función
        try:
            result = await func(*args, **kwargs)

            # Actualizar estado en caso de éxito
            async with self._lock:
                self.successful_calls += 1

                if self.state == CircuitBreakerState.HALF_OPEN:
                    logger.info(
                        f"Circuit Breaker '{self.name}' recuperado, cambiando a CLOSED"
                    )
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0

                elif self.state == CircuitBreakerState.CLOSED:
                    # Reducir contador de fallos gradualmente con cada éxito
                    if self.failure_count > 0:
                        self.failure_count -= 1

            return result

        except Exception as e:
            # Actualizar estado en caso de fallo
            async with self._lock:
                self.failed_calls += 1
                self.failure_count += 1
                self.last_failure_time = time.time()

                # Verificar si debemos abrir el circuito
                if (
                    self.state == CircuitBreakerState.CLOSED
                    and self.failure_count >= self.failure_threshold
                ):
                    logger.warning(
                        f"Circuit Breaker '{self.name}' cambiando a estado OPEN"
                    )
                    self.state = CircuitBreakerState.OPEN

                # Si estamos en half-open y falla, volver a abrir
                elif self.state == CircuitBreakerState.HALF_OPEN:
                    logger.warning(
                        f"Circuit Breaker '{self.name}' fallo en recuperación, volviendo a OPEN"
                    )
                    self.state = CircuitBreakerState.OPEN

            # Re-lanzar la excepción
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del Circuit Breaker.

        Returns:
            Dict[str, Any]: Estadísticas
        """
        return {
            "name": self.name,
            "state": self.state.name,
            "failure_count": self.failure_count,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "prevented_calls": self.prevented_calls,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


class MessageQueue:
    """
    Cola de mensajes con prioridad para comunicación entre agentes.

    Implementa una cola asíncrona con soporte para prioridades,
    timeouts y backpressure.
    """

    def __init__(self, name: str, max_size: int = 1000, default_timeout: float = 30.0):
        """
        Inicializa la cola de mensajes.

        Args:
            name: Nombre identificativo
            max_size: Tamaño máximo de la cola
            default_timeout: Timeout por defecto en segundos
        """
        self.name = name
        self.max_size = max_size
        self.default_timeout = default_timeout

        # Colas por prioridad
        self.queues = {
            MessagePriority.CRITICAL: asyncio.Queue(maxsize=max_size),
            MessagePriority.HIGH: asyncio.Queue(maxsize=max_size),
            MessagePriority.NORMAL: asyncio.Queue(maxsize=max_size),
            MessagePriority.LOW: asyncio.Queue(maxsize=max_size),
        }

        # Evento para notificar nuevos mensajes
        self.message_event = asyncio.Event()

        # Estadísticas
        self.stats = {
            "enqueued_messages": 0,
            "dequeued_messages": 0,
            "dropped_messages": 0,
            "timeout_messages": 0,
            "current_size": 0,
            "high_watermark": 0,
        }

        logger.info(f"Cola de mensajes '{name}' inicializada")

    async def put(
        self,
        message: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """
        Añade un mensaje a la cola.

        Args:
            message: Mensaje a añadir
            priority: Prioridad del mensaje

        Returns:
            bool: True si se añadió correctamente
        """
        # Verificar si la cola está llena
        if self.queues[priority].qsize() >= self.max_size:
            self.stats["dropped_messages"] += 1
            logger.warning(f"Cola '{self.name}' llena, mensaje descartado")
            return False

        # Añadir timestamp si no existe
        if "timestamp" not in message:
            message["timestamp"] = time.time()

        # Añadir ID si no existe
        if "message_id" not in message:
            message["message_id"] = str(uuid.uuid4())

        # Añadir prioridad
        message["priority"] = priority.name

        # Añadir a la cola
        await self.queues[priority].put(message)

        # Actualizar estadísticas
        self.stats["enqueued_messages"] += 1
        self.stats["current_size"] += 1

        if self.stats["current_size"] > self.stats["high_watermark"]:
            self.stats["high_watermark"] = self.stats["current_size"]

        # Notificar nuevo mensaje
        self.message_event.set()

        return True

    async def get(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene el siguiente mensaje de la cola.

        Verifica las colas en orden de prioridad.

        Args:
            timeout: Timeout en segundos (None para usar el default)

        Returns:
            Optional[Dict[str, Any]]: Mensaje o None si hay timeout
        """
        if timeout is None:
            timeout = self.default_timeout

        # Verificar cada cola en orden de prioridad
        for priority in [
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW,
        ]:
            # Si hay mensajes en esta cola, retornar el primero
            if not self.queues[priority].empty():
                message = await self.queues[priority].get()

                # Actualizar estadísticas
                self.stats["dequeued_messages"] += 1
                self.stats["current_size"] -= 1

                # Marcar como procesado
                self.queues[priority].task_done()

                return message

        # Si no hay mensajes, esperar con timeout
        try:
            # Limpiar evento
            self.message_event.clear()

            # Esperar nuevo mensaje
            await asyncio.wait_for(self.message_event.wait(), timeout)

            # Recursivamente intentar obtener mensaje
            return await self.get(timeout)

        except asyncio.TimeoutError:
            self.stats["timeout_messages"] += 1
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la cola.

        Returns:
            Dict[str, Any]: Estadísticas
        """
        # Obtener tamaños actuales
        queue_sizes = {
            priority.name: queue.qsize() for priority, queue in self.queues.items()
        }

        return {
            "name": self.name,
            "max_size": self.max_size,
            "queue_sizes": queue_sizes,
            **self.stats,
        }


class A2AServer:
    """
    Servidor A2A (Agent-to-Agent) optimizado.

    Implementa comunicación asíncrona entre agentes con mecanismos
    de resiliencia, priorización y monitoreo.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(A2AServer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        max_queue_size: int = 1000,
        message_timeout: float = 30.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 30,
    ):
        """
        Inicializa el servidor A2A.

        Args:
            max_queue_size: Tamaño máximo de las colas
            message_timeout: Timeout para mensajes en segundos
            circuit_breaker_threshold: Umbral de fallos para Circuit Breaker
            circuit_breaker_timeout: Timeout de recuperación para Circuit Breaker
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        # Configuración
        self.max_queue_size = max_queue_size
        self.message_timeout = message_timeout
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Colas de mensajes por agente
        self.agent_queues: Dict[str, MessageQueue] = {}

        # Circuit Breakers por agente
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Manejadores de mensajes registrados
        self.message_handlers: Dict[str, Callable] = {}

        # Tareas de procesamiento
        self.processing_tasks: Dict[str, asyncio.Task] = {}

        # Lock para operaciones concurrentes
        self._lock = asyncio.Lock()

        # Estado de ejecución
        self.running = False

        # Estadísticas
        self.stats = {
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "failed_deliveries": 0,
            "active_agents": 0,
        }

        self._initialized = True
        logger.info("Servidor A2A inicializado")

    async def start(self) -> bool:
        """
        Inicia el servidor A2A.

        Returns:
            bool: True si se inició correctamente
        """
        async with self._lock:
            if self.running:
                logger.warning("El servidor A2A ya está en ejecución")
                return True

            self.running = True
            logger.info("Servidor A2A iniciado")
            return True

    async def stop(self) -> bool:
        """
        Detiene el servidor A2A.

        Returns:
            bool: True si se detuvo correctamente
        """
        async with self._lock:
            if not self.running:
                logger.warning("El servidor A2A no está en ejecución")
                return True

            # Detener tareas de procesamiento
            for agent_id, task in self.processing_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            self.processing_tasks.clear()
            self.running = False
            logger.info("Servidor A2A detenido")
            return True

    async def register_agent(self, agent_id: str, message_handler: Callable) -> bool:
        """
        Registra un agente en el servidor.

        Args:
            agent_id: ID del agente
            message_handler: Función para manejar mensajes

        Returns:
            bool: True si se registró correctamente
        """
        async with self._lock:
            # Verificar si ya está registrado
            if agent_id in self.agent_queues:
                logger.warning(f"Agente '{agent_id}' ya está registrado")
                return False

            # Crear cola de mensajes
            self.agent_queues[agent_id] = MessageQueue(
                name=f"queue_{agent_id}",
                max_size=self.max_queue_size,
                default_timeout=self.message_timeout,
            )

            # Crear Circuit Breaker
            self.circuit_breakers[agent_id] = CircuitBreaker(
                name=f"cb_{agent_id}",
                failure_threshold=self.circuit_breaker_threshold,
                recovery_timeout=self.circuit_breaker_timeout,
            )

            # Registrar manejador
            self.message_handlers[agent_id] = message_handler

            # Iniciar tarea de procesamiento
            self.processing_tasks[agent_id] = asyncio.create_task(
                self._process_messages(agent_id)
            )

            # Actualizar estadísticas
            self.stats["active_agents"] += 1

            logger.info(f"Agente '{agent_id}' registrado en el servidor A2A")
            return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Elimina un agente del servidor.

        Args:
            agent_id: ID del agente

        Returns:
            bool: True si se eliminó correctamente
        """
        async with self._lock:
            # Verificar si está registrado
            if agent_id not in self.agent_queues:
                logger.warning(f"Agente '{agent_id}' no está registrado")
                return False

            # Detener tarea de procesamiento
            if agent_id in self.processing_tasks:
                task = self.processing_tasks[agent_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                del self.processing_tasks[agent_id]

            # Eliminar recursos
            del self.agent_queues[agent_id]
            del self.circuit_breakers[agent_id]
            del self.message_handlers[agent_id]

            # Actualizar estadísticas
            self.stats["active_agents"] -= 1

            logger.info(f"Agente '{agent_id}' eliminado del servidor A2A")
            return True

    async def send_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """
        Envía un mensaje de un agente a otro.

        Args:
            from_agent_id: ID del agente emisor
            to_agent_id: ID del agente receptor
            message: Contenido del mensaje
            priority: Prioridad del mensaje

        Returns:
            bool: True si se envió correctamente
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="a2a_send_message",
            attributes={
                "from_agent": from_agent_id,
                "to_agent": to_agent_id,
                "priority": priority.name,
            },
        )

        try:
            # Verificar si el agente receptor está registrado
            if to_agent_id not in self.agent_queues:
                logger.error(f"Agente receptor '{to_agent_id}' no está registrado")
                telemetry_manager.set_span_attribute(
                    span_id, "error", "agent_not_registered"
                )
                self.stats["failed_deliveries"] += 1
                return False

            # Preparar mensaje completo
            full_message = {
                "from_agent_id": from_agent_id,
                "to_agent_id": to_agent_id,
                "timestamp": time.time(),
                "message_id": str(uuid.uuid4()),
                "content": message,
            }

            # Añadir a la cola del receptor
            result = await self.agent_queues[to_agent_id].put(
                message=full_message, priority=priority
            )

            # Actualizar estadísticas
            if result:
                self.stats["total_messages_sent"] += 1
                telemetry_manager.set_span_attribute(span_id, "success", True)
            else:
                self.stats["failed_deliveries"] += 1
                telemetry_manager.set_span_attribute(span_id, "error", "queue_full")

            return result

        except Exception as e:
            logger.error(f"Error al enviar mensaje: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["failed_deliveries"] += 1
            return False

        finally:
            telemetry_manager.end_span(span_id)

    async def _process_messages(self, agent_id: str) -> None:
        """
        Procesa mensajes para un agente.

        Esta función se ejecuta como una tarea asíncrona para cada agente.

        Args:
            agent_id: ID del agente
        """
        logger.info(f"Iniciando procesamiento de mensajes para agente '{agent_id}'")

        while self.running:
            try:
                # Obtener mensaje de la cola
                message = await self.agent_queues[agent_id].get()

                if message:
                    # Registrar inicio de telemetría
                    span_id = telemetry_manager.start_span(
                        name="a2a_process_message",
                        attributes={
                            "agent_id": agent_id,
                            "message_id": message.get("message_id", "unknown"),
                            "from_agent": message.get("from_agent_id", "unknown"),
                        },
                    )

                    try:
                        # Obtener manejador
                        handler = self.message_handlers.get(agent_id)

                        if handler:
                            # Ejecutar manejador con Circuit Breaker
                            cb = self.circuit_breakers.get(agent_id)

                            if cb:
                                await cb.execute(handler, message)
                            else:
                                await handler(message)

                            # Actualizar estadísticas
                            self.stats["total_messages_received"] += 1
                            telemetry_manager.set_span_attribute(
                                span_id, "success", True
                            )

                        else:
                            logger.warning(
                                f"No hay manejador registrado para agente '{agent_id}'"
                            )
                            telemetry_manager.set_span_attribute(
                                span_id, "error", "no_handler"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error al procesar mensaje para agente '{agent_id}': {str(e)}"
                        )
                        telemetry_manager.set_span_attribute(span_id, "error", str(e))

                    finally:
                        telemetry_manager.end_span(span_id)

            except asyncio.CancelledError:
                logger.info(
                    f"Procesamiento de mensajes cancelado para agente '{agent_id}'"
                )
                break

            except Exception as e:
                logger.error(
                    f"Error en bucle de procesamiento para agente '{agent_id}': {str(e)}"
                )
                # Pequeña pausa para evitar bucles de error rápidos
                await asyncio.sleep(1)

        logger.info(f"Procesamiento de mensajes detenido para agente '{agent_id}'")

    async def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas para un agente específico.

        Args:
            agent_id: ID del agente

        Returns:
            Dict[str, Any]: Estadísticas del agente
        """
        result = {
            "agent_id": agent_id,
            "registered": agent_id in self.agent_queues,
            "queue": None,
            "circuit_breaker": None,
        }

        # Añadir estadísticas de cola
        if agent_id in self.agent_queues:
            result["queue"] = self.agent_queues[agent_id].get_stats()

        # Añadir estadísticas de Circuit Breaker
        if agent_id in self.circuit_breakers:
            result["circuit_breaker"] = self.circuit_breakers[agent_id].get_stats()

        return result

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales del servidor.

        Returns:
            Dict[str, Any]: Estadísticas
        """
        # Estadísticas básicas
        result = {
            "running": self.running,
            "registered_agents": list(self.agent_queues.keys()),
            **self.stats,
        }

        # Añadir estadísticas por agente
        agent_stats = {}
        for agent_id in self.agent_queues:
            agent_stats[agent_id] = await self.get_agent_stats(agent_id)

        result["agents"] = agent_stats

        return result


# Crear instancia global
a2a_server = A2AServer()
