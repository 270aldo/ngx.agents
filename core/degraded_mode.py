"""
Sistema de modos degradados para funcionalidad limitada.

Este módulo proporciona funcionalidades para gestionar modos degradados
que permiten al sistema seguir funcionando con capacidades reducidas
cuando hay problemas con servicios externos o recursos.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
from functools import wraps

# Configurar logger
logger = logging.getLogger(__name__)


class DegradationLevel(int, Enum):
    """Niveles de degradación del sistema."""

    NONE = 0  # Funcionamiento normal
    LOW = 1  # Degradación leve, algunas funciones no críticas desactivadas
    MEDIUM = 2  # Degradación media, varias funciones desactivadas
    HIGH = 3  # Degradación alta, solo funciones esenciales disponibles
    CRITICAL = 4  # Degradación crítica, modo de emergencia


class DegradationReason(str, Enum):
    """Razones para la degradación del sistema."""

    EXTERNAL_SERVICE = "external_service"  # Problema con servicio externo
    RESOURCE_LIMIT = "resource_limit"  # Límite de recursos alcanzado
    PERFORMANCE = "performance"  # Problemas de rendimiento
    SECURITY = "security"  # Problema de seguridad
    MAINTENANCE = "maintenance"  # Mantenimiento programado
    MANUAL = "manual"  # Activación manual
    AUTOMATIC = "automatic"  # Activación automática por el sistema


class ServiceStatus:
    """Estado de un servicio en el sistema."""

    def __init__(
        self,
        service_id: str,
        name: str,
        description: str,
        is_critical: bool = False,
        dependencies: Optional[List[str]] = None,
    ):
        """
        Inicializa el estado de un servicio.

        Args:
            service_id: Identificador único del servicio
            name: Nombre del servicio
            description: Descripción del servicio
            is_critical: Si el servicio es crítico para el funcionamiento del sistema
            dependencies: Lista de IDs de servicios de los que depende este servicio
        """
        self.service_id = service_id
        self.name = name
        self.description = description
        self.is_critical = is_critical
        self.dependencies = dependencies or []

        self.is_available = True
        self.degradation_level = DegradationLevel.NONE
        self.degradation_reason = None
        self.last_status_change = datetime.now()
        self.last_check = datetime.now()
        self.failure_count = 0
        self.success_count = 0
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el estado del servicio a un diccionario.

        Returns:
            Diccionario con los datos del estado
        """
        return {
            "service_id": self.service_id,
            "name": self.name,
            "description": self.description,
            "is_critical": self.is_critical,
            "dependencies": self.dependencies,
            "is_available": self.is_available,
            "degradation_level": (
                self.degradation_level.value if self.degradation_level else 0
            ),
            "degradation_reason": (
                self.degradation_reason.value if self.degradation_reason else None
            ),
            "last_status_change": self.last_status_change.isoformat(),
            "last_check": self.last_check.isoformat(),
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "metadata": self.metadata,
        }


class DegradedModeManager:
    """
    Gestor de modos degradados.

    Esta clase proporciona funcionalidades para gestionar modos degradados
    que permiten al sistema seguir funcionando con capacidades reducidas
    cuando hay problemas con servicios externos o recursos.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "DegradedModeManager":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(DegradedModeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Inicializa el gestor de modos degradados."""
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        # Estado global del sistema
        self.system_degradation_level = DegradationLevel.NONE
        self.system_degradation_reason = None
        self.system_degradation_start = None
        self.system_degradation_message = None

        # Registro de servicios
        self.services: Dict[str, ServiceStatus] = {}

        # Registro de funcionalidades
        self.features: Dict[str, bool] = {}

        # Registro de callbacks para notificaciones
        self.callbacks: List[
            Callable[
                [DegradationLevel, Optional[DegradationReason], Optional[str]], None
            ]
        ] = []

        # Lock para operaciones concurrentes
        self.lock = asyncio.Lock()

        # Tarea de monitorización
        self.monitor_task = None

        # Configuración
        self.check_interval = 60  # Intervalo de comprobación en segundos
        self.auto_recovery = True  # Recuperación automática
        self.recovery_threshold = (
            3  # Número de comprobaciones exitosas para recuperación
        )

        self._initialized = True

        logger.info("DegradedModeManager inicializado")

    async def start_monitoring(self) -> None:
        """Inicia la monitorización de servicios."""
        if self.monitor_task:
            logger.warning("La monitorización ya está en ejecución")
            return

        self.monitor_task = asyncio.create_task(self._monitor_services())
        logger.info("Monitorización de servicios iniciada")

    async def stop_monitoring(self) -> None:
        """Detiene la monitorización de servicios."""
        if not self.monitor_task:
            logger.warning("La monitorización no está en ejecución")
            return

        self.monitor_task.cancel()
        try:
            await self.monitor_task
        except asyncio.CancelledError:
            pass

        self.monitor_task = None
        logger.info("Monitorización de servicios detenida")

    async def _monitor_services(self) -> None:
        """Tarea de monitorización de servicios."""
        while True:
            try:
                # Comprobar servicios
                for service_id, service in self.services.items():
                    await self._check_service(service_id)

                # Actualizar estado global del sistema
                await self._update_system_status()

                # Esperar hasta la próxima comprobación
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error en monitorización de servicios: {e}", exc_info=True
                )
                await asyncio.sleep(10)  # Esperar un poco más en caso de error

    async def _check_service(self, service_id: str) -> None:
        """
        Comprueba el estado de un servicio.

        Args:
            service_id: ID del servicio a comprobar
        """
        service = self.services.get(service_id)
        if not service:
            return

        # Actualizar timestamp de última comprobación
        service.last_check = datetime.now()

        # Comprobar dependencias
        for dependency_id in service.dependencies:
            dependency = self.services.get(dependency_id)
            if dependency and not dependency.is_available:
                # Si una dependencia no está disponible, este servicio tampoco
                await self._set_service_unavailable(
                    service_id,
                    DegradationReason.EXTERNAL_SERVICE,
                    f"Dependencia no disponible: {dependency.name}",
                )
                return

        # Aquí se podrían añadir comprobaciones específicas para cada servicio
        # Por ahora, asumimos que el servicio está disponible si sus dependencias lo están
        if not service.is_available and self.auto_recovery:
            service.success_count += 1
            if service.success_count >= self.recovery_threshold:
                await self._set_service_available(service_id)
        else:
            service.success_count = 0

    async def _set_service_unavailable(
        self,
        service_id: str,
        reason: DegradationReason,
        message: Optional[str] = None,
        level: DegradationLevel = DegradationLevel.MEDIUM,
    ) -> None:
        """
        Marca un servicio como no disponible.

        Args:
            service_id: ID del servicio
            reason: Razón de la degradación
            message: Mensaje descriptivo
            level: Nivel de degradación
        """
        async with self.lock:
            service = self.services.get(service_id)
            if not service:
                return

            if service.is_available:
                service.is_available = False
                service.degradation_level = level
                service.degradation_reason = reason
                service.last_status_change = datetime.now()
                service.failure_count += 1
                service.success_count = 0
                service.metadata["last_failure_message"] = message

                logger.warning(f"Servicio {service.name} no disponible: {message}")

                # Actualizar estado global del sistema
                await self._update_system_status()

    async def _set_service_available(self, service_id: str) -> None:
        """
        Marca un servicio como disponible.

        Args:
            service_id: ID del servicio
        """
        async with self.lock:
            service = self.services.get(service_id)
            if not service:
                return

            if not service.is_available:
                service.is_available = True
                service.degradation_level = DegradationLevel.NONE
                service.degradation_reason = None
                service.last_status_change = datetime.now()
                service.failure_count = 0

                logger.info(f"Servicio {service.name} disponible nuevamente")

                # Actualizar estado global del sistema
                await self._update_system_status()

    async def _update_system_status(self) -> None:
        """Actualiza el estado global del sistema basado en los servicios."""
        async with self.lock:
            # Determinar el nivel de degradación más alto entre los servicios críticos
            max_level = DegradationLevel.NONE
            critical_reason = None
            critical_service = None

            for service in self.services.values():
                if service.is_critical and not service.is_available:
                    if service.degradation_level.value > max_level.value:
                        max_level = service.degradation_level
                        critical_reason = service.degradation_reason
                        critical_service = service

            # Actualizar estado global si ha cambiado
            if max_level != self.system_degradation_level:
                old_level = self.system_degradation_level
                self.system_degradation_level = max_level
                self.system_degradation_reason = critical_reason

                if max_level != DegradationLevel.NONE:
                    self.system_degradation_start = datetime.now()
                    self.system_degradation_message = (
                        f"Sistema en modo degradado debido a problemas con el servicio {critical_service.name}"
                        if critical_service
                        else "Sistema en modo degradado"
                    )
                else:
                    self.system_degradation_start = None
                    self.system_degradation_message = None

                # Notificar cambio de estado
                await self._notify_status_change(old_level, max_level)

    async def _notify_status_change(
        self, old_level: DegradationLevel, new_level: DegradationLevel
    ) -> None:
        """
        Notifica un cambio en el estado de degradación del sistema.

        Args:
            old_level: Nivel anterior
            new_level: Nuevo nivel
        """
        if old_level == new_level:
            return

        if new_level == DegradationLevel.NONE:
            logger.info("Sistema recuperado, funcionando normalmente")
        else:
            logger.warning(
                f"Sistema en modo degradado: nivel {new_level.name}, razón: {self.system_degradation_reason.value if self.system_degradation_reason else 'desconocida'}"
            )

        # Ejecutar callbacks
        for callback in self.callbacks:
            try:
                callback(
                    new_level,
                    self.system_degradation_reason,
                    self.system_degradation_message,
                )
            except Exception as e:
                logger.error(f"Error en callback de notificación: {e}")

    async def register_service(
        self,
        service_id: str,
        name: str,
        description: str,
        is_critical: bool = False,
        dependencies: Optional[List[str]] = None,
    ) -> ServiceStatus:
        """
        Registra un servicio en el sistema.

        Args:
            service_id: Identificador único del servicio
            name: Nombre del servicio
            description: Descripción del servicio
            is_critical: Si el servicio es crítico para el funcionamiento del sistema
            dependencies: Lista de IDs de servicios de los que depende este servicio

        Returns:
            Estado del servicio
        """
        async with self.lock:
            service = ServiceStatus(
                service_id=service_id,
                name=name,
                description=description,
                is_critical=is_critical,
                dependencies=dependencies,
            )

            self.services[service_id] = service
            logger.info(f"Servicio registrado: {name} (ID: {service_id})")

            return service

    async def unregister_service(self, service_id: str) -> bool:
        """
        Elimina un servicio del registro.

        Args:
            service_id: ID del servicio a eliminar

        Returns:
            True si se ha eliminado, False si no existía
        """
        async with self.lock:
            if service_id in self.services:
                del self.services[service_id]
                logger.info(f"Servicio eliminado: {service_id}")

                # Actualizar estado global del sistema
                await self._update_system_status()

                return True

            return False

    async def set_service_unavailable(
        self,
        service_id: str,
        reason: DegradationReason,
        message: Optional[str] = None,
        level: DegradationLevel = DegradationLevel.MEDIUM,
    ) -> bool:
        """
        Marca un servicio como no disponible.

        Args:
            service_id: ID del servicio
            reason: Razón de la degradación
            message: Mensaje descriptivo
            level: Nivel de degradación

        Returns:
            True si se ha actualizado, False si el servicio no existe
        """
        if service_id not in self.services:
            return False

        await self._set_service_unavailable(service_id, reason, message, level)
        return True

    async def set_service_available(self, service_id: str) -> bool:
        """
        Marca un servicio como disponible.

        Args:
            service_id: ID del servicio

        Returns:
            True si se ha actualizado, False si el servicio no existe
        """
        if service_id not in self.services:
            return False

        await self._set_service_available(service_id)
        return True

    async def get_service_status(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de un servicio.

        Args:
            service_id: ID del servicio

        Returns:
            Estado del servicio o None si no existe
        """
        service = self.services.get(service_id)
        if not service:
            return None

        return service.to_dict()

    async def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene el estado de todos los servicios.

        Returns:
            Diccionario con el estado de todos los servicios
        """
        return {
            service_id: service.to_dict()
            for service_id, service in self.services.items()
        }

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado global del sistema.

        Returns:
            Diccionario con el estado global del sistema
        """
        return {
            "degradation_level": self.system_degradation_level.value,
            "degradation_level_name": self.system_degradation_level.name,
            "degradation_reason": (
                self.system_degradation_reason.value
                if self.system_degradation_reason
                else None
            ),
            "degradation_start": (
                self.system_degradation_start.isoformat()
                if self.system_degradation_start
                else None
            ),
            "degradation_message": self.system_degradation_message,
            "degradation_duration": (
                (datetime.now() - self.system_degradation_start).total_seconds()
                if self.system_degradation_start
                else 0
            ),
            "services_total": len(self.services),
            "services_available": sum(
                1 for service in self.services.values() if service.is_available
            ),
            "services_unavailable": sum(
                1 for service in self.services.values() if not service.is_available
            ),
            "critical_services_total": sum(
                1 for service in self.services.values() if service.is_critical
            ),
            "critical_services_available": sum(
                1
                for service in self.services.values()
                if service.is_critical and service.is_available
            ),
            "critical_services_unavailable": sum(
                1
                for service in self.services.values()
                if service.is_critical and not service.is_available
            ),
        }

    async def set_feature_enabled(self, feature_id: str, enabled: bool) -> None:
        """
        Establece si una funcionalidad está habilitada.

        Args:
            feature_id: ID de la funcionalidad
            enabled: Si está habilitada
        """
        async with self.lock:
            self.features[feature_id] = enabled
            logger.info(
                f"Funcionalidad {feature_id} {'habilitada' if enabled else 'deshabilitada'}"
            )

    async def is_feature_enabled(self, feature_id: str, default: bool = True) -> bool:
        """
        Comprueba si una funcionalidad está habilitada.

        Args:
            feature_id: ID de la funcionalidad
            default: Valor por defecto si la funcionalidad no está registrada

        Returns:
            True si la funcionalidad está habilitada, False en caso contrario
        """
        # Si el sistema está en modo degradado crítico, deshabilitar funcionalidades no esenciales
        if (
            self.system_degradation_level == DegradationLevel.CRITICAL
            and not feature_id.startswith("essential:")
        ):
            return False

        # Si el sistema está en modo degradado alto, deshabilitar funcionalidades avanzadas
        if (
            self.system_degradation_level == DegradationLevel.HIGH
            and feature_id.startswith("advanced:")
        ):
            return False

        return self.features.get(feature_id, default)

    async def register_callback(
        self,
        callback: Callable[
            [DegradationLevel, Optional[DegradationReason], Optional[str]], None
        ],
    ) -> None:
        """
        Registra un callback para notificaciones de cambios de estado.

        Args:
            callback: Función a llamar cuando cambie el estado
        """
        self.callbacks.append(callback)

    async def unregister_callback(
        self,
        callback: Callable[
            [DegradationLevel, Optional[DegradationReason], Optional[str]], None
        ],
    ) -> bool:
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


# Función decoradora para comprobar si una funcionalidad está habilitada
def feature_check(feature_id: str, default: bool = True):
    """
    Decorador para comprobar si una funcionalidad está habilitada.

    Args:
        feature_id: ID de la funcionalidad
        default: Valor por defecto si la funcionalidad no está registrada

    Returns:
        Decorador configurado
    """

    def decorator(func):
        @wraps(func)
        async def wrapper_async(*args, **kwargs):
            # Comprobar si la funcionalidad está habilitada
            manager = DegradedModeManager()
            if not await manager.is_feature_enabled(feature_id, default):
                raise FeatureDisabledException(
                    f"Funcionalidad {feature_id} deshabilitada"
                )

            # Ejecutar función
            return await func(*args, **kwargs)

        @wraps(func)
        def wrapper_sync(*args, **kwargs):
            # Para funciones síncronas, crear una versión asíncrona y ejecutarla
            async def async_wrapper():
                # Comprobar si la funcionalidad está habilitada
                manager = DegradedModeManager()
                if not await manager.is_feature_enabled(feature_id, default):
                    raise FeatureDisabledException(
                        f"Funcionalidad {feature_id} deshabilitada"
                    )

                # Ejecutar función
                return func(*args, **kwargs)

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


class FeatureDisabledException(Exception):
    """Excepción lanzada cuando una funcionalidad está deshabilitada."""


# Instancia global para uso en toda la aplicación
degraded_mode_manager = DegradedModeManager()
