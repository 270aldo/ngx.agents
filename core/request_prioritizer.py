"""
Sistema de priorización de solicitudes basado en SLAs.

Este módulo proporciona funcionalidades para priorizar solicitudes según
acuerdos de nivel de servicio (SLAs) y gestionar la cola de solicitudes.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime
import heapq

# Configurar logger
logger = logging.getLogger(__name__)


class SLATier(str, Enum):
    """Niveles de SLA para priorización de solicitudes."""

    PLATINUM = "platinum"  # Máxima prioridad, tiempo de respuesta garantizado
    GOLD = "gold"  # Alta prioridad, tiempo de respuesta rápido
    SILVER = "silver"  # Prioridad media, tiempo de respuesta estándar
    BRONZE = "bronze"  # Prioridad baja, sin garantías de tiempo
    FREE = "free"  # Sin prioridad, atendido cuando haya recursos disponibles


class RequestStatus(str, Enum):
    """Estados posibles de las solicitudes."""

    QUEUED = "queued"  # En cola, esperando ser procesada
    PROCESSING = "processing"  # En procesamiento
    COMPLETED = "completed"  # Procesada correctamente
    FAILED = "failed"  # Error durante el procesamiento
    TIMEOUT = "timeout"  # Tiempo de espera agotado
    REJECTED = "rejected"  # Rechazada (por ejemplo, por cuota excedida)


class SLAConfig:
    """Configuración de SLA para un nivel."""

    def __init__(
        self,
        tier: SLATier,
        max_wait_time: int,  # Tiempo máximo de espera en segundos
        priority_boost: int,  # Incremento de prioridad por segundo de espera
        max_concurrent: int,  # Máximo de solicitudes concurrentes
        daily_quota: Optional[int] = None,  # Cuota diaria (None = sin límite)
        rate_limit: Optional[
            int
        ] = None,  # Límite de solicitudes por minuto (None = sin límite)
        timeout: Optional[int] = None,  # Timeout en segundos (None = sin timeout)
    ):
        """
        Inicializa una configuración de SLA.

        Args:
            tier: Nivel de SLA
            max_wait_time: Tiempo máximo de espera en segundos
            priority_boost: Incremento de prioridad por segundo de espera
            max_concurrent: Máximo de solicitudes concurrentes
            daily_quota: Cuota diaria (None = sin límite)
            rate_limit: Límite de solicitudes por minuto (None = sin límite)
            timeout: Timeout en segundos (None = sin timeout)
        """
        self.tier = tier
        self.max_wait_time = max_wait_time
        self.priority_boost = priority_boost
        self.max_concurrent = max_concurrent
        self.daily_quota = daily_quota
        self.rate_limit = rate_limit
        self.timeout = timeout

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la configuración a un diccionario.

        Returns:
            Diccionario con los datos de la configuración
        """
        return {
            "tier": self.tier.value,
            "max_wait_time": self.max_wait_time,
            "priority_boost": self.priority_boost,
            "max_concurrent": self.max_concurrent,
            "daily_quota": self.daily_quota,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
        }


class Request:
    """Representación de una solicitud priorizada."""

    def __init__(
        self,
        request_id: str,
        user_id: str,
        agent_id: Optional[str],
        sla_tier: SLATier,
        data: Any,
        handler: Callable[[Any], Awaitable[Any]],
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa una solicitud.

        Args:
            request_id: Identificador único de la solicitud
            user_id: ID del usuario que realiza la solicitud
            agent_id: ID del agente asociado a la solicitud
            sla_tier: Nivel de SLA del usuario
            data: Datos de la solicitud
            handler: Función para procesar la solicitud
            created_at: Fecha de creación (None = ahora)
            metadata: Metadatos adicionales
        """
        self.request_id = request_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.sla_tier = sla_tier
        self.data = data
        self.handler = handler
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}

        self.status = RequestStatus.QUEUED
        self.priority = self._get_base_priority()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.wait_time = 0  # Tiempo de espera en segundos
        self.processing_time = 0  # Tiempo de procesamiento en segundos

    def _get_base_priority(self) -> int:
        """
        Obtiene la prioridad base según el nivel de SLA.

        Returns:
            Prioridad base (menor número = mayor prioridad)
        """
        # Prioridades base por nivel de SLA
        priorities = {
            SLATier.PLATINUM: 0,
            SLATier.GOLD: 100,
            SLATier.SILVER: 200,
            SLATier.BRONZE: 300,
            SLATier.FREE: 400,
        }

        return priorities.get(self.sla_tier, 500)

    def update_priority(self, wait_time: float, config: SLAConfig) -> None:
        """
        Actualiza la prioridad según el tiempo de espera.

        Args:
            wait_time: Tiempo de espera en segundos
            config: Configuración de SLA
        """
        self.wait_time = wait_time

        # Calcular boost de prioridad según tiempo de espera
        # Menor número = mayor prioridad
        priority_boost = int(wait_time * config.priority_boost)

        # Actualizar prioridad (restando el boost para aumentar la prioridad)
        self.priority = self._get_base_priority() - priority_boost

        # Asegurar que la prioridad no sea negativa
        self.priority = max(0, self.priority)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la solicitud a un diccionario.

        Returns:
            Diccionario con los datos de la solicitud
        """
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "sla_tier": self.sla_tier.value,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "wait_time": self.wait_time,
            "processing_time": self.processing_time,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
            "metadata": self.metadata,
        }


class UserQuota:
    """Gestión de cuotas por usuario."""

    def __init__(
        self, user_id: str, sla_tier: SLATier, daily_quota: Optional[int] = None
    ):
        """
        Inicializa una cuota de usuario.

        Args:
            user_id: ID del usuario
            sla_tier: Nivel de SLA del usuario
            daily_quota: Cuota diaria (None = sin límite)
        """
        self.user_id = user_id
        self.sla_tier = sla_tier
        self.daily_quota = daily_quota

        self.usage_today = 0
        self.last_reset = datetime.now().date()
        self.requests_per_minute: List[datetime] = []
        self.concurrent_requests = 0

    def reset_if_needed(self) -> None:
        """Resetea la cuota diaria si es un nuevo día."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.usage_today = 0
            self.last_reset = today

    def can_make_request(self, rate_limit: Optional[int], max_concurrent: int) -> bool:
        """
        Verifica si el usuario puede realizar una solicitud.

        Args:
            rate_limit: Límite de solicitudes por minuto
            max_concurrent: Máximo de solicitudes concurrentes

        Returns:
            True si puede realizar la solicitud, False en caso contrario
        """
        self.reset_if_needed()

        # Verificar cuota diaria
        if self.daily_quota is not None and self.usage_today >= self.daily_quota:
            return False

        # Verificar límite de concurrencia
        if self.concurrent_requests >= max_concurrent:
            return False

        # Verificar límite de tasa
        if rate_limit is not None:
            # Limpiar solicitudes antiguas (más de 1 minuto)
            now = datetime.now()
            self.requests_per_minute = [
                t for t in self.requests_per_minute if (now - t).total_seconds() < 60
            ]

            # Verificar límite
            if len(self.requests_per_minute) >= rate_limit:
                return False

        return True

    def record_request(self) -> None:
        """Registra una nueva solicitud."""
        self.reset_if_needed()

        self.usage_today += 1
        self.requests_per_minute.append(datetime.now())
        self.concurrent_requests += 1

    def complete_request(self) -> None:
        """Registra la finalización de una solicitud."""
        self.concurrent_requests = max(0, self.concurrent_requests - 1)


class RequestPrioritizer:
    """
    Sistema de priorización de solicitudes basado en SLAs.

    Esta clase proporciona funcionalidades para priorizar solicitudes según
    acuerdos de nivel de servicio (SLAs) y gestionar la cola de solicitudes.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "RequestPrioritizer":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(RequestPrioritizer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_workers: int = 10):
        """
        Inicializa el priorizador de solicitudes.

        Args:
            max_workers: Número máximo de workers
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        self.max_workers = max_workers

        # Configuraciones de SLA por defecto
        self.sla_configs = {
            SLATier.PLATINUM: SLAConfig(
                tier=SLATier.PLATINUM,
                max_wait_time=5,  # 5 segundos máximo de espera
                priority_boost=10,  # +10 prioridad por segundo de espera
                max_concurrent=10,  # 10 solicitudes concurrentes
                daily_quota=None,  # Sin límite diario
                rate_limit=60,  # 60 solicitudes por minuto
                timeout=30,  # 30 segundos de timeout
            ),
            SLATier.GOLD: SLAConfig(
                tier=SLATier.GOLD,
                max_wait_time=15,  # 15 segundos máximo de espera
                priority_boost=5,  # +5 prioridad por segundo de espera
                max_concurrent=5,  # 5 solicitudes concurrentes
                daily_quota=1000,  # 1000 solicitudes diarias
                rate_limit=30,  # 30 solicitudes por minuto
                timeout=60,  # 60 segundos de timeout
            ),
            SLATier.SILVER: SLAConfig(
                tier=SLATier.SILVER,
                max_wait_time=30,  # 30 segundos máximo de espera
                priority_boost=2,  # +2 prioridad por segundo de espera
                max_concurrent=3,  # 3 solicitudes concurrentes
                daily_quota=500,  # 500 solicitudes diarias
                rate_limit=15,  # 15 solicitudes por minuto
                timeout=120,  # 120 segundos de timeout
            ),
            SLATier.BRONZE: SLAConfig(
                tier=SLATier.BRONZE,
                max_wait_time=60,  # 60 segundos máximo de espera
                priority_boost=1,  # +1 prioridad por segundo de espera
                max_concurrent=2,  # 2 solicitudes concurrentes
                daily_quota=200,  # 200 solicitudes diarias
                rate_limit=10,  # 10 solicitudes por minuto
                timeout=180,  # 180 segundos de timeout
            ),
            SLATier.FREE: SLAConfig(
                tier=SLATier.FREE,
                max_wait_time=120,  # 120 segundos máximo de espera
                priority_boost=0.5,  # +0.5 prioridad por segundo de espera
                max_concurrent=1,  # 1 solicitud concurrente
                daily_quota=50,  # 50 solicitudes diarias
                rate_limit=5,  # 5 solicitudes por minuto
                timeout=240,  # 240 segundos de timeout
            ),
        }

        # Cola de prioridad (heap)
        self.priority_queue = []

        # Diccionario de solicitudes
        self.requests: Dict[str, Request] = {}

        # Diccionario de cuotas por usuario
        self.user_quotas: Dict[str, UserQuota] = {}

        # Semáforo para limitar el número de solicitudes concurrentes
        self.semaphore = asyncio.Semaphore(max_workers)

        # Lock para operaciones en la cola
        self.queue_lock = asyncio.Lock()

        # Evento para señalizar parada
        self.stop_event = asyncio.Event()

        # Tarea de actualización de prioridades
        self.priority_updater_task = None

        # Tarea de procesamiento de solicitudes
        self.processor_task = None

        # Estadísticas
        self.stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "timeout_requests": 0,
            "rejected_requests": 0,
            "avg_wait_time": 0.0,
            "avg_processing_time": 0.0,
            "max_wait_time": 0.0,
            "max_processing_time": 0.0,
        }

        self._initialized = True

        logger.info(f"RequestPrioritizer inicializado (max_workers={max_workers})")

    async def start(self) -> None:
        """Inicia las tareas de actualización de prioridades y procesamiento."""
        if self.priority_updater_task or self.processor_task:
            logger.warning("RequestPrioritizer ya está en ejecución")
            return

        # Iniciar tarea de actualización de prioridades
        self.priority_updater_task = asyncio.create_task(self._priority_updater())

        # Iniciar tarea de procesamiento
        self.processor_task = asyncio.create_task(self._processor())

        logger.info("RequestPrioritizer iniciado")

    async def stop(self) -> None:
        """Detiene las tareas de actualización de prioridades y procesamiento."""
        if not (self.priority_updater_task or self.processor_task):
            logger.warning("RequestPrioritizer no está en ejecución")
            return

        # Señalizar parada
        self.stop_event.set()

        # Esperar a que terminen las tareas
        if self.priority_updater_task:
            await asyncio.wait([self.priority_updater_task], timeout=5)
            self.priority_updater_task = None

        if self.processor_task:
            await asyncio.wait([self.processor_task], timeout=5)
            self.processor_task = None

        # Limpiar
        self.stop_event.clear()

        logger.info("RequestPrioritizer detenido")

    async def _priority_updater(self) -> None:
        """Tarea para actualizar las prioridades de las solicitudes en cola."""
        while not self.stop_event.is_set():
            try:
                async with self.queue_lock:
                    now = datetime.now()

                    # Actualizar prioridades de las solicitudes en cola
                    updated_queue = []

                    for _, request_id in self.priority_queue:
                        request = self.requests.get(request_id)
                        if not request or request.status != RequestStatus.QUEUED:
                            continue

                        # Calcular tiempo de espera
                        wait_time = (now - request.created_at).total_seconds()

                        # Obtener configuración de SLA
                        sla_config = self.sla_configs.get(request.sla_tier)
                        if not sla_config:
                            continue

                        # Actualizar prioridad
                        request.update_priority(wait_time, sla_config)

                        # Verificar tiempo máximo de espera
                        if wait_time > sla_config.max_wait_time:
                            # Aumentar prioridad significativamente
                            request.priority = max(0, request.priority - 1000)

                        # Añadir a la nueva cola
                        heapq.heappush(updated_queue, (request.priority, request_id))

                    # Reemplazar cola
                    self.priority_queue = updated_queue

                # Esperar antes de la próxima actualización
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(
                    f"Error en actualización de prioridades: {e}", exc_info=True
                )
                await asyncio.sleep(5)  # Esperar más tiempo en caso de error

    async def _processor(self) -> None:
        """Tarea para procesar solicitudes de la cola."""
        while not self.stop_event.is_set():
            try:
                # Obtener solicitud de mayor prioridad
                request = None

                async with self.queue_lock:
                    if self.priority_queue:
                        _, request_id = heapq.heappop(self.priority_queue)
                        request = self.requests.get(request_id)

                        # Verificar que la solicitud esté en estado QUEUED
                        if request and request.status != RequestStatus.QUEUED:
                            request = None

                if not request:
                    # No hay solicitudes en cola, esperar
                    await asyncio.sleep(0.1)
                    continue

                # Procesar solicitud
                asyncio.create_task(self._process_request(request))

                # Pequeña pausa para evitar saturación
                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Error en procesador de solicitudes: {e}", exc_info=True)
                await asyncio.sleep(1)  # Esperar en caso de error

    async def _process_request(self, request: Request) -> None:
        """
        Procesa una solicitud.

        Args:
            request: Solicitud a procesar
        """
        # Obtener cuota de usuario
        user_quota = self.user_quotas.get(request.user_id)
        if not user_quota:
            logger.warning(f"Cuota de usuario no encontrada para {request.user_id}")
            return

        # Obtener configuración de SLA
        sla_config = self.sla_configs.get(request.sla_tier)
        if not sla_config:
            logger.warning(
                f"Configuración de SLA no encontrada para {request.sla_tier}"
            )
            return

        # Actualizar estado
        request.status = RequestStatus.PROCESSING
        request.started_at = datetime.now()
        request.wait_time = (request.started_at - request.created_at).total_seconds()

        # Actualizar estadísticas de tiempo de espera
        self.stats["avg_wait_time"] = (
            self.stats["avg_wait_time"] * self.stats["completed_requests"]
            + request.wait_time
        ) / (self.stats["completed_requests"] + 1)
        self.stats["max_wait_time"] = max(
            self.stats["max_wait_time"], request.wait_time
        )

        try:
            # Procesar con timeout
            if sla_config.timeout:
                result = await asyncio.wait_for(
                    self._execute_handler(request), timeout=sla_config.timeout
                )
            else:
                result = await self._execute_handler(request)

            # Actualizar estado
            request.status = RequestStatus.COMPLETED
            request.result = result
            request.completed_at = datetime.now()

            # Calcular tiempo de procesamiento
            request.processing_time = (
                request.completed_at - request.started_at
            ).total_seconds()

            # Actualizar estadísticas
            self.stats["completed_requests"] += 1
            self.stats["avg_processing_time"] = (
                self.stats["avg_processing_time"]
                * (self.stats["completed_requests"] - 1)
                + request.processing_time
            ) / self.stats["completed_requests"]
            self.stats["max_processing_time"] = max(
                self.stats["max_processing_time"], request.processing_time
            )

            logger.debug(
                f"Solicitud {request.request_id} completada en {request.processing_time:.2f}s (espera: {request.wait_time:.2f}s)"
            )

        except asyncio.TimeoutError:
            # Timeout
            request.status = RequestStatus.TIMEOUT
            request.error = "Timeout"
            request.completed_at = datetime.now()

            # Actualizar estadísticas
            self.stats["timeout_requests"] += 1

            logger.warning(
                f"Timeout en solicitud {request.request_id} después de {sla_config.timeout}s"
            )

        except Exception as e:
            # Error
            request.status = RequestStatus.FAILED
            request.error = str(e)
            request.completed_at = datetime.now()

            # Actualizar estadísticas
            self.stats["failed_requests"] += 1

            logger.error(f"Error en solicitud {request.request_id}: {e}", exc_info=True)

        finally:
            # Actualizar cuota de usuario
            user_quota.complete_request()

    async def _execute_handler(self, request: Request) -> Any:
        """
        Ejecuta el handler de una solicitud.

        Args:
            request: Solicitud a procesar

        Returns:
            Resultado del handler
        """
        async with self.semaphore:
            return await request.handler(request.data)

    async def submit_request(
        self,
        user_id: str,
        data: Any,
        handler: Callable[[Any], Awaitable[Any]],
        agent_id: Optional[str] = None,
        sla_tier: Optional[SLATier] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Envía una solicitud para su procesamiento priorizado.

        Args:
            user_id: ID del usuario
            data: Datos de la solicitud
            handler: Función para procesar la solicitud
            agent_id: ID del agente asociado a la solicitud
            sla_tier: Nivel de SLA (None = obtener del usuario)
            metadata: Metadatos adicionales

        Returns:
            ID de la solicitud
        """
        # Obtener o crear cuota de usuario
        user_quota = await self._get_or_create_user_quota(user_id, sla_tier)

        # Obtener configuración de SLA
        sla_config = self.sla_configs.get(user_quota.sla_tier)
        if not sla_config:
            raise ValueError(
                f"Configuración de SLA no encontrada para {user_quota.sla_tier}"
            )

        # Verificar si el usuario puede realizar la solicitud
        if not user_quota.can_make_request(
            sla_config.rate_limit, sla_config.max_concurrent
        ):
            # Rechazar solicitud
            request_id = str(uuid.uuid4())

            # Crear solicitud rechazada para registro
            request = Request(
                request_id=request_id,
                user_id=user_id,
                agent_id=agent_id,
                sla_tier=user_quota.sla_tier,
                data=data,
                handler=handler,
                metadata=metadata,
            )

            request.status = RequestStatus.REJECTED
            request.error = "Cuota excedida o límite de concurrencia alcanzado"
            request.completed_at = datetime.now()

            # Guardar en el diccionario
            self.requests[request_id] = request

            # Actualizar estadísticas
            self.stats["total_requests"] += 1
            self.stats["rejected_requests"] += 1

            logger.warning(
                f"Solicitud {request_id} rechazada para usuario {user_id} (cuota excedida)"
            )

            raise ValueError(
                f"Cuota excedida o límite de concurrencia alcanzado para usuario {user_id}"
            )

        # Registrar solicitud en la cuota
        user_quota.record_request()

        # Generar ID de solicitud
        request_id = str(uuid.uuid4())

        # Crear solicitud
        request = Request(
            request_id=request_id,
            user_id=user_id,
            agent_id=agent_id,
            sla_tier=user_quota.sla_tier,
            data=data,
            handler=handler,
            metadata=metadata,
        )

        # Guardar en el diccionario
        self.requests[request_id] = request

        # Añadir a la cola de prioridad
        async with self.queue_lock:
            heapq.heappush(self.priority_queue, (request.priority, request_id))

        # Actualizar estadísticas
        self.stats["total_requests"] += 1

        logger.debug(
            f"Solicitud {request_id} encolada para usuario {user_id} con prioridad {request.priority}"
        )

        return request_id

    async def _get_or_create_user_quota(
        self, user_id: str, sla_tier: Optional[SLATier] = None
    ) -> UserQuota:
        """
        Obtiene o crea una cuota de usuario.

        Args:
            user_id: ID del usuario
            sla_tier: Nivel de SLA (None = usar FREE)

        Returns:
            Cuota de usuario
        """
        if user_id in self.user_quotas:
            quota = self.user_quotas[user_id]

            # Actualizar nivel de SLA si se proporciona
            if sla_tier and quota.sla_tier != sla_tier:
                quota.sla_tier = sla_tier

                # Actualizar cuota diaria según el nuevo nivel
                sla_config = self.sla_configs.get(sla_tier)
                if sla_config:
                    quota.daily_quota = sla_config.daily_quota

            return quota

        # Determinar nivel de SLA
        tier = sla_tier or SLATier.FREE

        # Obtener configuración de SLA
        sla_config = self.sla_configs.get(tier)
        if not sla_config:
            # Usar FREE como fallback
            tier = SLATier.FREE
            sla_config = self.sla_configs.get(tier)

        # Crear cuota
        quota = UserQuota(
            user_id=user_id,
            sla_tier=tier,
            daily_quota=sla_config.daily_quota if sla_config else None,
        )

        # Guardar en el diccionario
        self.user_quotas[user_id] = quota

        return quota

    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una solicitud.

        Args:
            request_id: ID de la solicitud

        Returns:
            Diccionario con el estado de la solicitud o None si no existe
        """
        request = self.requests.get(request_id)
        if not request:
            return None

        return request.to_dict()

    async def get_request_result(
        self, request_id: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Obtiene el resultado de una solicitud.

        Args:
            request_id: ID de la solicitud
            wait: Si se debe esperar a que la solicitud termine
            timeout: Tiempo máximo de espera en segundos

        Returns:
            Diccionario con el resultado de la solicitud
        """
        request = self.requests.get(request_id)
        if not request:
            raise ValueError(f"Solicitud {request_id} no encontrada")

        if wait and request.status in [RequestStatus.QUEUED, RequestStatus.PROCESSING]:
            # Esperar a que la solicitud termine
            start_time = time.time()
            while request.status in [RequestStatus.QUEUED, RequestStatus.PROCESSING]:
                await asyncio.sleep(0.1)

                if timeout and time.time() - start_time > timeout:
                    raise asyncio.TimeoutError(
                        f"Timeout esperando resultado de solicitud {request_id}"
                    )

        return {
            "request_id": request.request_id,
            "status": request.status.value,
            "result": request.result,
            "error": request.error,
            "wait_time": request.wait_time,
            "processing_time": request.processing_time,
            "total_time": (
                request.wait_time + request.processing_time
                if request.completed_at
                else None
            ),
        }

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del priorizador.

        Returns:
            Diccionario con estadísticas
        """
        # Contar solicitudes por estado
        status_counts = {status.value: 0 for status in RequestStatus}
        for request in self.requests.values():
            status_counts[request.status.value] += 1

        # Contar solicitudes por nivel de SLA
        sla_counts = {tier.value: 0 for tier in SLATier}
        for request in self.requests.values():
            sla_counts[request.sla_tier.value] += 1

        # Contar solicitudes por agente
        agent_counts = {}
        for request in self.requests.values():
            if request.agent_id:
                agent_counts[request.agent_id] = (
                    agent_counts.get(request.agent_id, 0) + 1
                )

        return {
            **self.stats,
            "queue_size": len(self.priority_queue),
            "status_counts": status_counts,
            "sla_counts": sla_counts,
            "agent_counts": agent_counts,
            "active_workers": self.max_workers - self.semaphore._value,
            "max_workers": self.max_workers,
            "user_count": len(self.user_quotas),
        }

    async def clear_completed_requests(self, older_than: Optional[int] = None) -> int:
        """
        Elimina solicitudes completadas del diccionario.

        Args:
            older_than: Eliminar solicitudes completadas hace más de X segundos

        Returns:
            Número de solicitudes eliminadas
        """
        to_remove = []
        now = datetime.now()

        for request_id, request in self.requests.items():
            if request.status in [
                RequestStatus.COMPLETED,
                RequestStatus.FAILED,
                RequestStatus.TIMEOUT,
                RequestStatus.REJECTED,
            ]:
                if older_than is None or (
                    request.completed_at
                    and (now - request.completed_at).total_seconds() > older_than
                ):
                    to_remove.append(request_id)

        for request_id in to_remove:
            del self.requests[request_id]

        logger.info(f"Eliminadas {len(to_remove)} solicitudes completadas")
        return len(to_remove)


# Instancia global para uso en toda la aplicación
request_prioritizer = RequestPrioritizer()
