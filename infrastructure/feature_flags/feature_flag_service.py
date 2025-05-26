"""
Servicio de Feature Flags para NGX Agents.

Este módulo proporciona un servicio para gestionar feature flags,
permitiendo habilitar o deshabilitar características de forma controlada
y realizar despliegues graduales.
"""

import hashlib
from typing import Dict, Any, Optional, List

from infrastructure.adapters import get_telemetry_adapter
from infrastructure.feature_flags.redis_store import RedisFeatureFlagStore


class FeatureFlagService:
    """
    Servicio para gestionar feature flags.

    Esta clase proporciona métodos para verificar si un feature flag está
    habilitado para un usuario específico, considerando overrides por usuario
    y porcentajes de rollout.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(FeatureFlagService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, store=None):
        """
        Inicializa el servicio de feature flags.

        Args:
            store: Almacén de feature flags opcional. Si no se proporciona,
                  se utilizará RedisFeatureFlagStore.
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        self.store = store or RedisFeatureFlagStore()
        self.telemetry = get_telemetry_adapter()
        self._initialized = True

    async def is_enabled(
        self, flag_name: str, user_id: Optional[str] = None, default: bool = False
    ) -> bool:
        """
        Verifica si un feature flag está habilitado para un usuario.

        Este método considera:
        1. Override específico para el usuario
        2. Estado global del flag
        3. Porcentaje de rollout

        Args:
            flag_name: Nombre del feature flag.
            user_id: ID del usuario opcional.
            default: Valor por defecto si el flag no existe.

        Returns:
            bool: True si el flag está habilitado, False en caso contrario.
        """
        span = self.telemetry.start_span(
            "feature_flags.is_enabled",
            {"flag_name": flag_name, "user_id": user_id or "anonymous"},
        )

        try:
            # 1. Verificar override específico para el usuario
            if user_id:
                user_override = await self.store.get_user_override(flag_name, user_id)
                if user_override is not None:
                    self.telemetry.add_span_event(
                        span,
                        "user_override_applied",
                        {
                            "flag_name": flag_name,
                            "user_id": user_id,
                            "enabled": user_override,
                        },
                    )
                    return user_override

            # 2. Verificar estado global del flag
            global_enabled, metadata = await self.store.get_flag(flag_name, default)

            # Si el flag está deshabilitado globalmente, retornar False
            if not global_enabled:
                return False

            # 3. Verificar porcentaje de rollout
            rollout_percentage = await self.store.get_rollout_percentage(flag_name)

            # Si no hay porcentaje de rollout, usar el estado global
            if rollout_percentage is None or rollout_percentage == 100:
                return global_enabled

            # Si el porcentaje es 0, el flag está deshabilitado
            if rollout_percentage == 0:
                return False

            # Si no hay user_id, no podemos aplicar rollout
            if not user_id:
                return global_enabled

            # Calcular hash del user_id para determinar si está en el porcentaje
            hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100

            # El usuario está en el porcentaje si su hash es menor que el porcentaje
            is_in_rollout = hash_value < rollout_percentage

            self.telemetry.add_span_event(
                span,
                "rollout_check",
                {
                    "flag_name": flag_name,
                    "user_id": user_id,
                    "rollout_percentage": rollout_percentage,
                    "hash_value": hash_value,
                    "is_in_rollout": is_in_rollout,
                },
            )

            return is_in_rollout
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return default
        finally:
            self.telemetry.end_span(span)

    async def set_enabled(
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
            "feature_flags.set_enabled", {"flag_name": flag_name, "enabled": enabled}
        )

        try:
            result = await self.store.set_flag(flag_name, enabled, metadata)

            self.telemetry.add_span_event(
                span,
                "flag_updated",
                {"flag_name": flag_name, "enabled": enabled, "success": result},
            )

            return result
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
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
            result = await self.store.set_user_override(flag_name, user_id, enabled)

            self.telemetry.add_span_event(
                span,
                "user_override_set",
                {
                    "flag_name": flag_name,
                    "user_id": user_id,
                    "enabled": enabled,
                    "success": result,
                },
            )

            return result
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
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
            result = await self.store.set_rollout_percentage(flag_name, percentage)

            self.telemetry.add_span_event(
                span,
                "rollout_percentage_set",
                {"flag_name": flag_name, "percentage": percentage, "success": result},
            )

            return result
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
        finally:
            self.telemetry.end_span(span)

    async def list_flags(self) -> List[Dict[str, Any]]:
        """
        Lista todos los feature flags configurados.

        Returns:
            List[Dict[str, Any]]: Lista de feature flags con su configuración.
        """
        return await self.store.list_flags()

    async def create_staged_rollout(
        self, flag_name: str, stages: List[Dict[str, Any]]
    ) -> bool:
        """
        Crea un plan de rollout por etapas para un feature flag.

        Args:
            flag_name: Nombre del feature flag.
            stages: Lista de etapas del rollout, cada una con:
                   - percentage: Porcentaje de usuarios
                   - duration_hours: Duración en horas de la etapa

        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        span = self.telemetry.start_span(
            "feature_flags.create_staged_rollout",
            {"flag_name": flag_name, "stages_count": len(stages)},
        )

        try:
            import json
            import time

            # Validar etapas
            for i, stage in enumerate(stages):
                if "percentage" not in stage or "duration_hours" not in stage:
                    raise ValueError(
                        f"La etapa {i} debe tener percentage y duration_hours"
                    )

            # Crear plan de rollout
            rollout_plan = {
                "flag_name": flag_name,
                "created_at": time.time(),
                "current_stage": 0,
                "stages": stages,
            }

            # Almacenar plan
            key = f"feature:{flag_name}:rollout_plan"
            await self.store.redis_client.set(key, json.dumps(rollout_plan))

            # Establecer porcentaje inicial
            initial_percentage = stages[0]["percentage"]
            await self.set_rollout_percentage(flag_name, initial_percentage)

            self.telemetry.add_span_event(
                span,
                "staged_rollout_created",
                {
                    "flag_name": flag_name,
                    "stages_count": len(stages),
                    "initial_percentage": initial_percentage,
                },
            )

            return True
        except Exception as e:
            self.telemetry.record_exception(span, e)
            return False
        finally:
            self.telemetry.end_span(span)


def get_feature_flag_service() -> FeatureFlagService:
    """
    Obtiene la instancia global del servicio de feature flags.

    Returns:
        FeatureFlagService: Instancia global del servicio.
    """
    return FeatureFlagService()
