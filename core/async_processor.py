"""
Procesador asíncrono para operaciones no críticas.

Este módulo proporciona funcionalidades para ejecutar operaciones no críticas
de forma asíncrona, liberando el hilo principal para operaciones críticas.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable, Tuple
from enum import Enum
from datetime import datetime
from functools import wraps

# Configurar logger
logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    """Prioridades para las tareas asíncronas."""

    HIGH = 0
    MEDIUM = 1
    LOW = 2
    BACKGROUND = 3


class TaskStatus(str, Enum):
    """Estados posibles de las tareas asíncronas."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AsyncTask:
    """Representación de una tarea asíncrona."""

    def __init__(
        self,
        task_id: str,
        func: Callable[..., Any],
        args: Tuple = (),
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: Optional[float] = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa una tarea asíncrona.

        Args:
            task_id: Identificador único de la tarea
            func: Función a ejecutar
            args: Argumentos posicionales para la función
            kwargs: Argumentos con nombre para la función
            priority: Prioridad de la tarea
            timeout: Tiempo máximo de ejecución en segundos (None = sin límite)
            max_retries: Número máximo de reintentos en caso de fallo
            retry_delay: Tiempo de espera entre reintentos en segundos
            agent_id: ID del agente asociado a la tarea
            user_id: ID del usuario asociado a la tarea
            metadata: Metadatos adicionales
        """
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.agent_id = agent_id
        self.user_id = user_id
        self.metadata = metadata or {}

        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.retry_count = 0
        self.future = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la tarea a un diccionario.

        Returns:
            Diccionario con los datos de la tarea
        """
        return {
            "task_id": self.task_id,
            "priority": self.priority.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
            "execution_time": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at
                else None
            ),
        }


class AsyncProcessor:
    """
    Procesador de tareas asíncronas.

    Esta clase proporciona funcionalidades para ejecutar operaciones no críticas
    de forma asíncrona, liberando el hilo principal para operaciones críticas.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "AsyncProcessor":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(AsyncProcessor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        max_workers: int = 10,
        queue_size: int = 1000,
        default_timeout: Optional[float] = None,
        default_max_retries: int = 3,
        default_retry_delay: float = 1.0,
    ):
        """
        Inicializa el procesador asíncrono.

        Args:
            max_workers: Número máximo de workers
            queue_size: Tamaño máximo de la cola de tareas
            default_timeout: Tiempo máximo de ejecución por defecto en segundos
            default_max_retries: Número máximo de reintentos por defecto
            default_retry_delay: Tiempo de espera entre reintentos por defecto en segundos
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        self.max_workers = max_workers
        self.queue_size = queue_size
        self.default_timeout = default_timeout
        self.default_max_retries = default_max_retries
        self.default_retry_delay = default_retry_delay

        # Colas de tareas por prioridad
        self.queues = {
            TaskPriority.HIGH: asyncio.PriorityQueue(maxsize=queue_size),
            TaskPriority.MEDIUM: asyncio.PriorityQueue(maxsize=queue_size),
            TaskPriority.LOW: asyncio.PriorityQueue(maxsize=queue_size),
            TaskPriority.BACKGROUND: asyncio.PriorityQueue(maxsize=queue_size),
        }

        # Diccionario de tareas
        self.tasks: Dict[str, AsyncTask] = {}

        # Semáforo para limitar el número de tareas concurrentes
        self.semaphore = asyncio.Semaphore(max_workers)

        # Evento para señalizar parada
        self.stop_event = asyncio.Event()

        # Estadísticas
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "timeout_tasks": 0,
            "retried_tasks": 0,
            "avg_execution_time": 0.0,
        }

        # Inicializar workers
        self.workers = []
        self._initialized = True

        logger.info(
            f"AsyncProcessor inicializado (max_workers={max_workers}, queue_size={queue_size})"
        )

    async def start(self) -> None:
        """Inicia los workers del procesador."""
        if self.workers:
            logger.warning("AsyncProcessor ya está en ejecución")
            return

        # Crear workers para cada prioridad
        for priority in TaskPriority:
            for _ in range(self._get_workers_for_priority(priority)):
                worker = asyncio.create_task(self._worker(priority))
                self.workers.append(worker)

        logger.info(f"AsyncProcessor iniciado con {len(self.workers)} workers")

    def _get_workers_for_priority(self, priority: TaskPriority) -> int:
        """
        Determina el número de workers para una prioridad.

        Args:
            priority: Prioridad de las tareas

        Returns:
            Número de workers
        """
        # Distribuir workers según prioridad
        if priority == TaskPriority.HIGH:
            return max(1, int(self.max_workers * 0.5))  # 50% para alta prioridad
        elif priority == TaskPriority.MEDIUM:
            return max(1, int(self.max_workers * 0.3))  # 30% para prioridad media
        elif priority == TaskPriority.LOW:
            return max(1, int(self.max_workers * 0.15))  # 15% para baja prioridad
        else:  # BACKGROUND
            return max(
                1, int(self.max_workers * 0.05)
            )  # 5% para tareas en segundo plano

    async def stop(self) -> None:
        """Detiene los workers del procesador."""
        if not self.workers:
            logger.warning("AsyncProcessor no está en ejecución")
            return

        # Señalizar parada
        self.stop_event.set()

        # Esperar a que terminen los workers
        await asyncio.gather(*self.workers, return_exceptions=True)

        # Limpiar
        self.workers = []
        self.stop_event.clear()

        logger.info("AsyncProcessor detenido")

    async def _worker(self, priority: TaskPriority) -> None:
        """
        Worker para procesar tareas de una prioridad específica.

        Args:
            priority: Prioridad de las tareas a procesar
        """
        queue = self.queues[priority]

        while not self.stop_event.is_set():
            try:
                # Obtener tarea de la cola con timeout para poder comprobar stop_event
                try:
                    _, task_id = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                # Obtener tarea del diccionario
                task = self.tasks.get(task_id)
                if not task:
                    logger.warning(f"Tarea {task_id} no encontrada en el diccionario")
                    queue.task_done()
                    continue

                # Procesar tarea
                async with self.semaphore:
                    await self._process_task(task)

                # Marcar como completada en la cola
                queue.task_done()

            except Exception as e:
                logger.error(
                    f"Error en worker de prioridad {priority.name}: {e}", exc_info=True
                )

    async def _process_task(self, task: AsyncTask) -> None:
        """
        Procesa una tarea asíncrona.

        Args:
            task: Tarea a procesar
        """
        # Actualizar estado
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            # Ejecutar con timeout si está configurado
            if task.timeout:
                task.result = await asyncio.wait_for(
                    self._execute_task(task.func, *task.args, **task.kwargs),
                    timeout=task.timeout,
                )
            else:
                task.result = await self._execute_task(
                    task.func, *task.args, **task.kwargs
                )

            # Actualizar estado
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            # Actualizar estadísticas
            self.stats["completed_tasks"] += 1
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.stats["avg_execution_time"] = (
                self.stats["avg_execution_time"] * (self.stats["completed_tasks"] - 1)
                + execution_time
            ) / self.stats["completed_tasks"]

            logger.debug(f"Tarea {task.task_id} completada en {execution_time:.2f}s")

        except asyncio.TimeoutError:
            # Timeout
            task.status = TaskStatus.TIMEOUT
            task.error = "Timeout"
            task.completed_at = datetime.now()
            self.stats["timeout_tasks"] += 1

            logger.warning(
                f"Timeout en tarea {task.task_id} después de {task.timeout}s"
            )

            # Reintentar si es necesario
            if task.retry_count < task.max_retries:
                await self._retry_task(task)

        except Exception as e:
            # Error
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self.stats["failed_tasks"] += 1

            logger.error(f"Error en tarea {task.task_id}: {e}", exc_info=True)

            # Reintentar si es necesario
            if task.retry_count < task.max_retries:
                await self._retry_task(task)

    async def _execute_task(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """
        Ejecuta una función, ya sea síncrona o asíncrona.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos con nombre

        Returns:
            Resultado de la función
        """
        if asyncio.iscoroutinefunction(func):
            # Función asíncrona
            return await func(*args, **kwargs)
        else:
            # Función síncrona, ejecutar en un executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _retry_task(self, task: AsyncTask) -> None:
        """
        Reintenta una tarea fallida.

        Args:
            task: Tarea a reintentar
        """
        task.retry_count += 1
        task.status = TaskStatus.PENDING
        task.started_at = None
        task.completed_at = None
        task.error = None
        task.result = None

        # Actualizar estadísticas
        self.stats["retried_tasks"] += 1

        # Esperar antes de reintentar
        await asyncio.sleep(task.retry_delay)

        # Encolar de nuevo
        await self.enqueue_task(task)

        logger.info(
            f"Tarea {task.task_id} reencolada para reintento {task.retry_count}/{task.max_retries}"
        )

    async def enqueue_task(self, task: AsyncTask) -> None:
        """
        Encola una tarea para su ejecución.

        Args:
            task: Tarea a encolar
        """
        # Guardar en el diccionario
        self.tasks[task.task_id] = task

        # Encolar con prioridad
        # El primer elemento de la tupla es el tiempo de creación (para ordenar tareas de la misma prioridad)
        await self.queues[task.priority].put(
            (task.created_at.timestamp(), task.task_id)
        )

        # Actualizar estadísticas
        self.stats["total_tasks"] += 1

        logger.debug(
            f"Tarea {task.task_id} encolada con prioridad {task.priority.name}"
        )

    async def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Envía una tarea para su ejecución asíncrona.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales para la función
            priority: Prioridad de la tarea
            timeout: Tiempo máximo de ejecución en segundos
            max_retries: Número máximo de reintentos
            retry_delay: Tiempo de espera entre reintentos en segundos
            agent_id: ID del agente asociado a la tarea
            user_id: ID del usuario asociado a la tarea
            metadata: Metadatos adicionales
            **kwargs: Argumentos con nombre para la función

        Returns:
            ID de la tarea
        """
        # Generar ID de tarea
        task_id = str(uuid.uuid4())

        # Usar valores por defecto si no se especifican
        if timeout is None:
            timeout = self.default_timeout
        if max_retries is None:
            max_retries = self.default_max_retries
        if retry_delay is None:
            retry_delay = self.default_retry_delay

        # Crear tarea
        task = AsyncTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            agent_id=agent_id,
            user_id=user_id,
            metadata=metadata,
        )

        # Encolar tarea
        await self.enqueue_task(task)

        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancela una tarea pendiente.

        Args:
            task_id: ID de la tarea a cancelar

        Returns:
            True si se canceló correctamente, False si no se encontró o no se pudo cancelar
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Tarea {task_id} no encontrada")
            return False

        if task.status != TaskStatus.PENDING:
            logger.warning(
                f"No se puede cancelar tarea {task_id} con estado {task.status.value}"
            )
            return False

        # Actualizar estado
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()

        # Actualizar estadísticas
        self.stats["cancelled_tasks"] += 1

        logger.info(f"Tarea {task_id} cancelada")
        return True

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información sobre una tarea.

        Args:
            task_id: ID de la tarea

        Returns:
            Diccionario con información de la tarea o None si no se encontró
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        return task.to_dict()

    async def get_result(
        self, task_id: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Obtiene el resultado de una tarea.

        Args:
            task_id: ID de la tarea
            wait: Si se debe esperar a que la tarea termine
            timeout: Tiempo máximo de espera en segundos

        Returns:
            Diccionario con el resultado de la tarea
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Tarea {task_id} no encontrada")

        if wait and task.status == TaskStatus.PENDING:
            # Esperar a que la tarea termine
            start_time = time.time()
            while (
                task.status == TaskStatus.PENDING or task.status == TaskStatus.RUNNING
            ):
                await asyncio.sleep(0.1)

                if timeout and time.time() - start_time > timeout:
                    raise asyncio.TimeoutError(
                        f"Timeout esperando resultado de tarea {task_id}"
                    )

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "execution_time": (
                (task.completed_at - task.started_at).total_seconds()
                if task.completed_at and task.started_at
                else None
            ),
        }

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del procesador.

        Returns:
            Diccionario con estadísticas
        """
        # Contar tareas por estado
        status_counts = {status.value: 0 for status in TaskStatus}
        for task in self.tasks.values():
            status_counts[task.status.value] += 1

        # Contar tareas por prioridad
        priority_counts = {priority.name: 0 for priority in TaskPriority}
        for task in self.tasks.values():
            priority_counts[task.priority.name] += 1

        # Contar tareas por agente
        agent_counts = {}
        for task in self.tasks.values():
            if task.agent_id:
                agent_counts[task.agent_id] = agent_counts.get(task.agent_id, 0) + 1

        return {
            **self.stats,
            "queue_sizes": {
                priority.name: queue.qsize() for priority, queue in self.queues.items()
            },
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "agent_counts": agent_counts,
            "active_workers": len(self.workers),
            "max_workers": self.max_workers,
        }

    async def clear_completed_tasks(self, older_than: Optional[int] = None) -> int:
        """
        Elimina tareas completadas del diccionario.

        Args:
            older_than: Eliminar tareas completadas hace más de X segundos

        Returns:
            Número de tareas eliminadas
        """
        to_remove = []
        now = datetime.now()

        for task_id, task in self.tasks.items():
            if task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
                TaskStatus.TIMEOUT,
            ]:
                if older_than is None or (
                    task.completed_at
                    and (now - task.completed_at).total_seconds() > older_than
                ):
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]

        logger.info(f"Eliminadas {len(to_remove)} tareas completadas")
        return len(to_remove)


# Función decoradora para ejecutar funciones de forma asíncrona
def async_task(
    priority: TaskPriority = TaskPriority.MEDIUM,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
):
    """
    Decorador para ejecutar una función de forma asíncrona.

    Args:
        priority: Prioridad de la tarea
        timeout: Tiempo máximo de ejecución en segundos
        max_retries: Número máximo de reintentos
        retry_delay: Tiempo de espera entre reintentos en segundos

    Returns:
        Decorador configurado
    """

    def decorator(func):
        @wraps(func)
        async def wrapper_async(*args, **kwargs):
            # Obtener procesador
            processor = AsyncProcessor()

            # Extraer agent_id y user_id de kwargs si existen
            agent_id = kwargs.pop("agent_id", None)
            user_id = kwargs.pop("user_id", None)
            metadata = kwargs.pop("metadata", None)

            # Enviar tarea
            task_id = await processor.submit(
                func,
                *args,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
                agent_id=agent_id,
                user_id=user_id,
                metadata=metadata,
                **kwargs,
            )

            return task_id

        @wraps(func)
        def wrapper_sync(*args, **kwargs):
            # Para funciones síncronas, crear una versión asíncrona y ejecutarla
            async def async_wrapper():
                # Obtener procesador
                processor = AsyncProcessor()

                # Extraer agent_id y user_id de kwargs si existen
                agent_id = kwargs.pop("agent_id", None)
                user_id = kwargs.pop("user_id", None)
                metadata = kwargs.pop("metadata", None)

                # Enviar tarea
                task_id = await processor.submit(
                    func,
                    *args,
                    priority=priority,
                    timeout=timeout,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                    agent_id=agent_id,
                    user_id=user_id,
                    metadata=metadata,
                    **kwargs,
                )

                return task_id

            # Ejecutar la versión asíncrona
            import asyncio

            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper())

        # Determinar si la función original es asíncrona
        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        else:
            return wrapper_sync

    return decorator


# Instancia global para uso en toda la aplicación
async_processor = AsyncProcessor()
