"""
Procesador por lotes para paralelización avanzada.

Este módulo proporciona funcionalidades para procesar grandes cantidades de datos
en paralelo, utilizando técnicas avanzadas de paralelización y distribución de carga.
"""

import asyncio
import logging
import uuid
from typing import (
    Dict,
    List,
    Any,
    Optional,
    Callable,
    Awaitable,
    Tuple,
    TypeVar,
    Generic,
)
from enum import Enum
from datetime import datetime
import math
import os
import tempfile

# Configurar logger
logger = logging.getLogger(__name__)

# Tipo genérico para los elementos de entrada
T = TypeVar("T")
# Tipo genérico para los resultados
R = TypeVar("R")


class BatchStrategy(str, Enum):
    """Estrategias de procesamiento por lotes."""

    CHUNK_SIZE = "chunk_size"  # Dividir en lotes de tamaño fijo
    CHUNK_COUNT = "chunk_count"  # Dividir en un número fijo de lotes
    ADAPTIVE = "adaptive"  # Adaptar el tamaño de los lotes según la carga


class BatchStatus(str, Enum):
    """Estados posibles de los lotes."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Completado parcialmente (algunos elementos fallaron)


class BatchResult(Generic[T, R]):
    """Resultado de un procesamiento por lotes."""

    def __init__(self, batch_id: str):
        """
        Inicializa un resultado de procesamiento por lotes.

        Args:
            batch_id: Identificador único del lote
        """
        self.batch_id = batch_id
        self.status = BatchStatus.PENDING
        self.results: Dict[int, R] = {}  # Índice -> Resultado
        self.errors: Dict[int, str] = {}  # Índice -> Error
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_items = 0
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el resultado a un diccionario.

        Returns:
            Diccionario con los datos del resultado
        """
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "progress": (
                (self.processed_items / self.total_items) * 100
                if self.total_items > 0
                else 0
            ),
            "execution_time": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time and self.start_time
                else None
            ),
            "metadata": self.metadata,
        }

    def get_results(self) -> List[R]:
        """
        Obtiene los resultados exitosos.

        Returns:
            Lista de resultados exitosos
        """
        return list(self.results.values())

    def get_errors(self) -> Dict[int, str]:
        """
        Obtiene los errores.

        Returns:
            Diccionario con los errores (índice -> mensaje)
        """
        return self.errors.copy()

    def update_status(self) -> None:
        """Actualiza el estado según los resultados."""
        if self.processed_items == 0:
            self.status = BatchStatus.PENDING
        elif self.processed_items < self.total_items:
            self.status = BatchStatus.PROCESSING
        elif self.failed_items == 0:
            self.status = BatchStatus.COMPLETED
        elif self.successful_items == 0:
            self.status = BatchStatus.FAILED
        else:
            self.status = BatchStatus.PARTIAL


class BatchProcessor:
    """
    Procesador por lotes para paralelización avanzada.

    Esta clase proporciona funcionalidades para procesar grandes cantidades de datos
    en paralelo, utilizando técnicas avanzadas de paralelización y distribución de carga.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "BatchProcessor":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(BatchProcessor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        max_workers: int = 10,
        default_chunk_size: int = 100,
        default_timeout: Optional[float] = None,
        temp_dir: Optional[str] = None,
    ):
        """
        Inicializa el procesador por lotes.

        Args:
            max_workers: Número máximo de workers
            default_chunk_size: Tamaño de lote por defecto
            default_timeout: Tiempo máximo de ejecución por defecto en segundos
            temp_dir: Directorio temporal para almacenar resultados grandes
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        self.max_workers = max_workers
        self.default_chunk_size = default_chunk_size
        self.default_timeout = default_timeout
        self.temp_dir = temp_dir or tempfile.gettempdir()

        # Asegurar que el directorio temporal existe
        os.makedirs(self.temp_dir, exist_ok=True)

        # Diccionario de resultados
        self.results: Dict[str, BatchResult] = {}

        # Semáforo para limitar el número de tareas concurrentes
        self.semaphore = asyncio.Semaphore(max_workers)

        # Estadísticas
        self.stats = {
            "total_batches": 0,
            "completed_batches": 0,
            "failed_batches": 0,
            "cancelled_batches": 0,
            "partial_batches": 0,
            "total_items_processed": 0,
            "successful_items": 0,
            "failed_items": 0,
            "avg_execution_time": 0.0,
        }

        self._initialized = True

        logger.info(
            f"BatchProcessor inicializado (max_workers={max_workers}, default_chunk_size={default_chunk_size})"
        )

    def _split_into_chunks(
        self,
        items: List[T],
        strategy: BatchStrategy,
        chunk_size: Optional[int] = None,
        chunk_count: Optional[int] = None,
    ) -> List[List[T]]:
        """
        Divide una lista de elementos en lotes.

        Args:
            items: Lista de elementos a dividir
            strategy: Estrategia de división
            chunk_size: Tamaño de cada lote (para CHUNK_SIZE)
            chunk_count: Número de lotes (para CHUNK_COUNT)

        Returns:
            Lista de lotes
        """
        total_items = len(items)

        if total_items == 0:
            return []

        if strategy == BatchStrategy.CHUNK_SIZE:
            # Dividir en lotes de tamaño fijo
            size = chunk_size or self.default_chunk_size
            return [items[i : i + size] for i in range(0, total_items, size)]

        elif strategy == BatchStrategy.CHUNK_COUNT:
            # Dividir en un número fijo de lotes
            count = chunk_count or min(self.max_workers, math.ceil(total_items / 10))
            size = math.ceil(total_items / count)
            return [items[i : i + size] for i in range(0, total_items, size)]

        elif strategy == BatchStrategy.ADAPTIVE:
            # Adaptar el tamaño de los lotes según la carga
            # Usar entre 1 y max_workers lotes, dependiendo del tamaño total
            count = min(self.max_workers, max(1, math.ceil(total_items / 100)))
            size = math.ceil(total_items / count)
            return [items[i : i + size] for i in range(0, total_items, size)]

        else:
            # Estrategia no reconocida, usar CHUNK_SIZE por defecto
            size = chunk_size or self.default_chunk_size
            return [items[i : i + size] for i in range(0, total_items, size)]

    async def _process_chunk(
        self,
        chunk: List[T],
        processor_func: Callable[[T], Awaitable[R]],
        chunk_index: int,
        batch_result: BatchResult[T, R],
        start_index: int,
    ) -> None:
        """
        Procesa un lote de elementos.

        Args:
            chunk: Lista de elementos a procesar
            processor_func: Función para procesar cada elemento
            chunk_index: Índice del lote
            batch_result: Objeto para almacenar los resultados
            start_index: Índice inicial de los elementos en el lote original
        """
        async with self.semaphore:
            for i, item in enumerate(chunk):
                item_index = start_index + i
                try:
                    # Procesar elemento
                    result = await processor_func(item)

                    # Guardar resultado
                    batch_result.results[item_index] = result
                    batch_result.successful_items += 1

                except Exception as e:
                    # Registrar error
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    batch_result.errors[item_index] = error_msg
                    batch_result.failed_items += 1
                    logger.error(
                        f"Error procesando elemento {item_index} en lote {batch_result.batch_id}: {error_msg}"
                    )

                # Actualizar contador
                batch_result.processed_items += 1

                # Actualizar estado
                batch_result.update_status()

    async def process_batch(
        self,
        items: List[T],
        processor_func: Callable[[T], Awaitable[R]],
        strategy: BatchStrategy = BatchStrategy.ADAPTIVE,
        chunk_size: Optional[int] = None,
        chunk_count: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Procesa un lote de elementos en paralelo.

        Args:
            items: Lista de elementos a procesar
            processor_func: Función para procesar cada elemento
            strategy: Estrategia de división en lotes
            chunk_size: Tamaño de cada lote (para CHUNK_SIZE)
            chunk_count: Número de lotes (para CHUNK_COUNT)
            timeout: Tiempo máximo de ejecución en segundos
            metadata: Metadatos adicionales

        Returns:
            ID del lote
        """
        # Generar ID de lote
        batch_id = str(uuid.uuid4())

        # Crear resultado
        batch_result = BatchResult[T, R](batch_id)
        batch_result.total_items = len(items)
        batch_result.metadata = metadata or {}
        batch_result.start_time = datetime.now()

        # Guardar en el diccionario
        self.results[batch_id] = batch_result

        # Actualizar estadísticas
        self.stats["total_batches"] += 1

        # Dividir en lotes
        chunks = self._split_into_chunks(items, strategy, chunk_size, chunk_count)

        # Crear tareas para procesar cada lote
        tasks = []
        start_index = 0

        for i, chunk in enumerate(chunks):
            task = asyncio.create_task(
                self._process_chunk(chunk, processor_func, i, batch_result, start_index)
            )
            tasks.append(task)
            start_index += len(chunk)

        # Ejecutar tareas con timeout
        try:
            if timeout:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
            else:
                await asyncio.gather(*tasks)

            # Actualizar estado final
            batch_result.end_time = datetime.now()
            batch_result.update_status()

            # Actualizar estadísticas
            if batch_result.status == BatchStatus.COMPLETED:
                self.stats["completed_batches"] += 1
            elif batch_result.status == BatchStatus.FAILED:
                self.stats["failed_batches"] += 1
            elif batch_result.status == BatchStatus.PARTIAL:
                self.stats["partial_batches"] += 1

            self.stats["total_items_processed"] += batch_result.processed_items
            self.stats["successful_items"] += batch_result.successful_items
            self.stats["failed_items"] += batch_result.failed_items

            if batch_result.end_time and batch_result.start_time:
                execution_time = (
                    batch_result.end_time - batch_result.start_time
                ).total_seconds()
                completed_count = (
                    self.stats["completed_batches"] + self.stats["partial_batches"]
                )

                if completed_count > 0:
                    self.stats["avg_execution_time"] = (
                        self.stats["avg_execution_time"] * (completed_count - 1)
                        + execution_time
                    ) / completed_count

        except asyncio.TimeoutError:
            # Cancelar tareas pendientes
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Actualizar estado
            batch_result.end_time = datetime.now()
            batch_result.status = BatchStatus.CANCELLED
            self.stats["cancelled_batches"] += 1

            logger.warning(f"Timeout en lote {batch_id} después de {timeout}s")

        return batch_id

    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de un lote.

        Args:
            batch_id: ID del lote

        Returns:
            Diccionario con el estado del lote o None si no existe
        """
        batch_result = self.results.get(batch_id)
        if not batch_result:
            return None

        return batch_result.to_dict()

    async def get_batch_results(
        self,
        batch_id: str,
        include_errors: bool = False,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Obtiene los resultados de un lote.

        Args:
            batch_id: ID del lote
            include_errors: Si se deben incluir los errores
            max_results: Número máximo de resultados a devolver

        Returns:
            Diccionario con los resultados del lote
        """
        batch_result = self.results.get(batch_id)
        if not batch_result:
            raise ValueError(f"Lote {batch_id} no encontrado")

        # Obtener estado
        status = batch_result.to_dict()

        # Limitar resultados si es necesario
        results = batch_result.get_results()
        if max_results is not None and max_results > 0:
            results = results[:max_results]

        # Preparar respuesta
        response = {**status, "results": results}

        # Incluir errores si se solicitan
        if include_errors:
            response["errors"] = batch_result.get_errors()

        return response

    async def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancela un lote en ejecución.

        Args:
            batch_id: ID del lote

        Returns:
            True si se canceló correctamente, False si no se encontró o no se pudo cancelar
        """
        batch_result = self.results.get(batch_id)
        if not batch_result:
            return False

        if batch_result.status not in [BatchStatus.PENDING, BatchStatus.PROCESSING]:
            return False

        # Actualizar estado
        batch_result.status = BatchStatus.CANCELLED
        batch_result.end_time = datetime.now()

        # Actualizar estadísticas
        self.stats["cancelled_batches"] += 1

        logger.info(f"Lote {batch_id} cancelado")
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del procesador.

        Returns:
            Diccionario con estadísticas
        """
        # Contar lotes por estado
        status_counts = {status.value: 0 for status in BatchStatus}
        for batch_result in self.results.values():
            status_counts[batch_result.status.value] += 1

        return {
            **self.stats,
            "status_counts": status_counts,
            "active_workers": self.max_workers - self.semaphore._value,
            "max_workers": self.max_workers,
        }

    async def clear_completed_batches(self, older_than: Optional[int] = None) -> int:
        """
        Elimina lotes completados del diccionario.

        Args:
            older_than: Eliminar lotes completados hace más de X segundos

        Returns:
            Número de lotes eliminados
        """
        to_remove = []
        now = datetime.now()

        for batch_id, batch_result in self.results.items():
            if batch_result.status in [
                BatchStatus.COMPLETED,
                BatchStatus.FAILED,
                BatchStatus.CANCELLED,
                BatchStatus.PARTIAL,
            ]:
                if older_than is None or (
                    batch_result.end_time
                    and (now - batch_result.end_time).total_seconds() > older_than
                ):
                    to_remove.append(batch_id)

        for batch_id in to_remove:
            del self.results[batch_id]

        logger.info(f"Eliminados {len(to_remove)} lotes completados")
        return len(to_remove)

    async def process_map(
        self, func: Callable[[T], Awaitable[R]], items: List[T], **kwargs: Any
    ) -> List[R]:
        """
        Aplica una función a cada elemento de una lista en paralelo.

        Similar a map() pero en paralelo y asíncrono.

        Args:
            func: Función a aplicar a cada elemento
            items: Lista de elementos
            **kwargs: Argumentos adicionales para process_batch

        Returns:
            Lista de resultados
        """
        batch_id = await self.process_batch(items, func, **kwargs)

        # Esperar a que termine el procesamiento
        batch_result = self.results[batch_id]
        while batch_result.status in [BatchStatus.PENDING, BatchStatus.PROCESSING]:
            await asyncio.sleep(0.1)

        # Obtener resultados
        return batch_result.get_results()

    async def process_filter(
        self, predicate: Callable[[T], Awaitable[bool]], items: List[T], **kwargs: Any
    ) -> List[T]:
        """
        Filtra una lista de elementos en paralelo.

        Similar a filter() pero en paralelo y asíncrono.

        Args:
            predicate: Función que devuelve True para los elementos a mantener
            items: Lista de elementos
            **kwargs: Argumentos adicionales para process_batch

        Returns:
            Lista de elementos que cumplen el predicado
        """

        # Crear función que devuelve el elemento si cumple el predicado, o None si no
        async def filter_func(item: T) -> Tuple[T, bool]:
            result = await predicate(item)
            return (item, result)

        # Procesar en paralelo
        batch_id = await self.process_batch(items, filter_func, **kwargs)

        # Esperar a que termine el procesamiento
        batch_result = self.results[batch_id]
        while batch_result.status in [BatchStatus.PENDING, BatchStatus.PROCESSING]:
            await asyncio.sleep(0.1)

        # Filtrar resultados
        filtered_items = []
        for item_result in batch_result.get_results():
            item, keep = item_result
            if keep:
                filtered_items.append(item)

        return filtered_items

    async def process_reduce(
        self,
        func: Callable[[R, T], Awaitable[R]],
        items: List[T],
        initial: R,
        **kwargs: Any,
    ) -> R:
        """
        Reduce una lista de elementos en paralelo.

        Similar a reduce() pero con paralelización parcial.

        Args:
            func: Función de reducción
            items: Lista de elementos
            initial: Valor inicial
            **kwargs: Argumentos adicionales para process_batch

        Returns:
            Resultado de la reducción
        """
        if not items:
            return initial

        # Procesar elementos en paralelo
        results = await self.process_map(lambda x: x, items, **kwargs)

        # Reducir secuencialmente
        result = initial
        for item in results:
            result = await func(result, item)

        return result


# Instancia global para uso en toda la aplicación
batch_processor = BatchProcessor()
