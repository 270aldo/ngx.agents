"""
Implementación de almacenamiento de feature flags basado en Redis.

Este módulo proporciona una implementación de almacenamiento para feature flags
utilizando Redis como backend, permitiendo una gestión distribuida y escalable.
"""

import json
import time
from typing import Dict, Any, Optional, List, Tuple

import redis.asyncio as redis
from core.settings import settings
from core.redis_pool import redis_pool_manager
from infrastructure.adapters import get_telemetry_adapter


class RedisFeatureFlagStore:
    """
    Almacén de feature flags basado en Redis.

    Esta clase proporciona métodos para almacenar y recuperar el estado de
    feature flags utilizando Redis como backend.
    """

    def __init__(self, redis_client=None):
        """
        Inicializa el almacén de feature flags.

        Args:
            redis_client: Cliente de Redis opcional. Si no se proporciona,
                          se creará uno nuevo utilizando la configuración.
        """
        self.redis_client = redis_client
        self.telemetry = get_telemetry_adapter()
        self._initialized = False

    async def _ensure_initialized(self):
        """Asegura que el cliente de Redis está inicializado."""
        if not self._initialized:
            if not self.redis_client:
                # Usar el pool manager para obtener el cliente
                self.redis_client = await redis_pool_manager.get_client()
                if not self.redis_client:
                    # Fallback: crear cliente directo si el pool no está disponible
                    self.redis_client = redis.Redis(
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_feature_flags_db,
                        password=settings.redis_password,
                        decode_responses=True,
                    )
            self._initialized = True

    async def set_flag(
        self, flag_name: str, enabled: bool, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Establece el estado global de un feature flag.

        Args:
            flag_name: Nombre del feature flag.
            enabled: Estado del feature flag (True=habilitado, False=deshabilitado).
            metadata: Metadatos adicionales para el feature flag.

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        span = self.telemetry.start_span(
            "feature_flags.set_flag", {"flag_name": flag_name, "enabled": enabled}
        )

        try:
            await self._ensure_initialized()

            # Clave para el estado global del flag
            key = f"feature:{flag_name}:global"

            # Datos a almacenar
            data = {
                "enabled": enabled,
                "updated_at": time.time(),
                "metadata": metadata or {},
            }

            # Almacenar en Redis
            await self.redis_client.set(key, json.dumps(data))

            # Registrar evento de telemetría
            self.telemetry.add_span_event(
                span,
                "feature_flag_updated",
                {"flag_name": flag_name, "enabled": enabled},
            )

            return True
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
        finally:
            self.telemetry.end_span(span)

    async def get_flag(
        self, flag_name: str, default: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Obtiene el estado global de un feature flag.

        Args:
            flag_name: Nombre del feature flag.
            default: Valor por defecto si el flag no existe.

        Returns:
            Tuple[bool, Dict[str, Any]]: Estado del flag y sus metadatos.
        """
        span = self.telemetry.start_span(
            "feature_flags.get_flag", {"flag_name": flag_name}
        )

        try:
            await self._ensure_initialized()

            # Clave para el estado global del flag
            key = f"feature:{flag_name}:global"

            # Obtener de Redis
            data_str = await self.redis_client.get(key)

            if not data_str:
                return default, {}

            # Parsear datos
            data = json.loads(data_str)

            return data.get("enabled", default), data.get("metadata", {})
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return default, {}
        finally:
            self.telemetry.end_span(span)

    async def set_user_override(
        self, flag_name: str, user_id: str, enabled: bool
    ) -> bool:
        """
        Establece un override de feature flag para un usuario específico.

        Args:
            flag_name: Nombre del feature flag.
            user_id: ID del usuario.
            enabled: Estado del feature flag para este usuario.

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        span = self.telemetry.start_span(
            "feature_flags.set_user_override",
            {"flag_name": flag_name, "user_id": user_id, "enabled": enabled},
        )

        try:
            await self._ensure_initialized()

            # Clave para el override del usuario
            key = f"feature:{flag_name}:user:{user_id}"

            # Almacenar en Redis
            await self.redis_client.set(key, "1" if enabled else "0")

            return True
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
        finally:
            self.telemetry.end_span(span)

    async def get_user_override(self, flag_name: str, user_id: str) -> Optional[bool]:
        """
        Obtiene el override de feature flag para un usuario específico.

        Args:
            flag_name: Nombre del feature flag.
            user_id: ID del usuario.

        Returns:
            Optional[bool]: Estado del flag para el usuario, o None si no hay override.
        """
        span = self.telemetry.start_span(
            "feature_flags.get_user_override",
            {"flag_name": flag_name, "user_id": user_id},
        )

        try:
            await self._ensure_initialized()

            # Clave para el override del usuario
            key = f"feature:{flag_name}:user:{user_id}"

            # Obtener de Redis
            value = await self.redis_client.get(key)

            if value is None:
                return None

            return value == "1"
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return None
        finally:
            self.telemetry.end_span(span)

    async def set_rollout_percentage(self, flag_name: str, percentage: int) -> bool:
        """
        Establece el porcentaje de rollout para un feature flag.

        Args:
            flag_name: Nombre del feature flag.
            percentage: Porcentaje de usuarios que verán el flag habilitado (0-100).

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        span = self.telemetry.start_span(
            "feature_flags.set_rollout_percentage",
            {"flag_name": flag_name, "percentage": percentage},
        )

        try:
            await self._ensure_initialized()

            # Validar porcentaje
            if not 0 <= percentage <= 100:
                raise ValueError("El porcentaje debe estar entre 0 y 100")

            # Clave para el porcentaje de rollout
            key = f"feature:{flag_name}:rollout"

            # Almacenar en Redis
            await self.redis_client.set(key, str(percentage))

            # Registrar evento de telemetría
            self.telemetry.add_span_event(
                span,
                "rollout_percentage_updated",
                {"flag_name": flag_name, "percentage": percentage},
            )

            return True
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
        finally:
            self.telemetry.end_span(span)

    async def get_rollout_percentage(self, flag_name: str) -> Optional[int]:
        """
        Obtiene el porcentaje de rollout para un feature flag.

        Args:
            flag_name: Nombre del feature flag.

        Returns:
            Optional[int]: Porcentaje de rollout, o None si no está configurado.
        """
        span = self.telemetry.start_span(
            "feature_flags.get_rollout_percentage", {"flag_name": flag_name}
        )

        try:
            await self._ensure_initialized()

            # Clave para el porcentaje de rollout
            key = f"feature:{flag_name}:rollout"

            # Obtener de Redis
            value = await self.redis_client.get(key)

            if value is None:
                return None

            return int(value)
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return None
        finally:
            self.telemetry.end_span(span)

    async def list_flags(self) -> List[Dict[str, Any]]:
        """
        Lista todos los feature flags configurados.

        Returns:
            List[Dict[str, Any]]: Lista de feature flags con su configuración.
        """
        span = self.telemetry.start_span("feature_flags.list_flags")

        try:
            await self._ensure_initialized()

            # Obtener todas las claves de flags globales
            keys = await self.redis_client.keys("feature:*:global")

            result = []
            for key in keys:
                # Extraer nombre del flag
                flag_name = key.split(":")[1]

                # Obtener datos del flag
                enabled, metadata = await self.get_flag(flag_name)

                # Obtener porcentaje de rollout
                rollout_percentage = await self.get_rollout_percentage(flag_name)

                result.append(
                    {
                        "name": flag_name,
                        "enabled": enabled,
                        "rollout_percentage": rollout_percentage,
                        "metadata": metadata,
                    }
                )

            return result
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return []
        finally:
            self.telemetry.end_span(span)
