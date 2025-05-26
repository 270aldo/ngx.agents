"""
Módulo de health checks para NGX Agents.

Este módulo proporciona funcionalidades para verificar el estado de la aplicación
y sus dependencias, incluyendo endpoints de health check para Kubernetes.
"""

import time
from typing import Dict, Any, Tuple

# Local imports
from core.logging_config import configure_logging
from clients.supabase_client import SupabaseClient
from clients.vertex_ai import vertex_ai_client
from infrastructure.a2a_optimized import a2a_server as a2a_optimized_server

# Configurar logger
logger = configure_logging(__name__)

# Constantes
STARTUP_TIME = time.time()


class HealthCheck:
    """
    Clase para gestionar health checks de la aplicación.

    Esta clase proporciona métodos para verificar el estado de la aplicación
    y sus dependencias, incluyendo endpoints de health check para Kubernetes.
    """

    def __init__(self):
        """
        Inicializa el gestor de health checks.
        """
        self.dependencies = []
        self.startup_checks_passed = False
        self.startup_check_time = None

    def register_dependency(
        self, name: str, check_func: callable, critical: bool = True
    ) -> None:
        """
        Registra una dependencia para verificar en los health checks.

        Args:
            name: Nombre de la dependencia.
            check_func: Función que verifica el estado de la dependencia.
                Debe devolver un tuple (bool, str) con el estado y un mensaje.
            critical: Si la dependencia es crítica para la aplicación.
        """
        self.dependencies.append(
            {"name": name, "check": check_func, "critical": critical}
        )
        logger.info(
            f"Dependencia registrada para health check: {name} (crítica: {critical})"
        )

    async def check_liveness(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si la aplicación está viva.

        Este método verifica si la aplicación está en ejecución y responde
        a solicitudes básicas. No verifica dependencias externas.

        Returns:
            Tuple[bool, Dict[str, Any]]: Estado de la aplicación y detalles.
        """
        uptime = time.time() - STARTUP_TIME

        return True, {
            "status": "UP",
            "uptime_seconds": uptime,
            "timestamp": time.time(),
        }

    async def check_readiness(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si la aplicación está lista para recibir tráfico.

        Este método verifica si la aplicación y sus dependencias críticas
        están listas para procesar solicitudes.

        Returns:
            Tuple[bool, Dict[str, Any]]: Estado de la aplicación y detalles.
        """
        dependency_results = []
        all_critical_ok = True

        # Verificar cada dependencia
        for dep in self.dependencies:
            try:
                is_ok, message = await dep["check"]()

                if not is_ok and dep["critical"]:
                    all_critical_ok = False

                dependency_results.append(
                    {
                        "name": dep["name"],
                        "status": "UP" if is_ok else "DOWN",
                        "critical": dep["critical"],
                        "message": message,
                    }
                )
            except Exception as e:
                logger.exception(f"Error verificando dependencia {dep['name']}")

                if dep["critical"]:
                    all_critical_ok = False

                dependency_results.append(
                    {
                        "name": dep["name"],
                        "status": "ERROR",
                        "critical": dep["critical"],
                        "message": str(e),
                    }
                )

        return all_critical_ok, {
            "status": "READY" if all_critical_ok else "NOT_READY",
            "timestamp": time.time(),
            "dependencies": dependency_results,
        }

    async def check_startup(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica si la aplicación se ha inicializado correctamente.

        Este método verifica si la aplicación ha completado su inicialización
        y está lista para recibir tráfico. Se ejecuta una sola vez durante
        el inicio de la aplicación.

        Returns:
            Tuple[bool, Dict[str, Any]]: Estado de la aplicación y detalles.
        """
        # Si ya pasó el startup check, devolver resultado almacenado
        if self.startup_checks_passed:
            return True, {
                "status": "STARTED",
                "timestamp": time.time(),
                "startup_time": self.startup_check_time,
            }

        # Verificar readiness
        is_ready, details = await self.check_readiness()

        if is_ready:
            self.startup_checks_passed = True
            self.startup_check_time = time.time() - STARTUP_TIME

            return True, {
                "status": "STARTED",
                "timestamp": time.time(),
                "startup_time": self.startup_check_time,
                "dependencies": details.get("dependencies", []),
            }
        else:
            return False, {
                "status": "STARTING",
                "timestamp": time.time(),
                "dependencies": details.get("dependencies", []),
            }

    async def check_supabase(self) -> Tuple[bool, str]:
        """
        Verifica la conexión con Supabase.

        Returns:
            Tuple[bool, str]: Estado de la conexión y mensaje.
        """
        try:
            client = SupabaseClient.get_instance()
            # Realizar una consulta simple para verificar la conexión
            result = await client.health_check()
            return True, "Conexión con Supabase establecida correctamente"
        except Exception as e:
            logger.error(f"Error verificando conexión con Supabase: {e}")
            return False, f"Error de conexión con Supabase: {str(e)}"

    async def check_vertex_ai(self) -> Tuple[bool, str]:
        """
        Verifica la conexión con Vertex AI.

        Returns:
            Tuple[bool, str]: Estado de la conexión y mensaje.
        """
        try:
            # Inicializar cliente si es necesario
            if not vertex_ai_client.is_initialized:
                await vertex_ai_client.initialize()

            # Verificar la conexión con una solicitud simple
            stats = await vertex_ai_client.get_stats()

            if stats.get("vertex_ai_available", False):
                return True, "Conexión con Vertex AI establecida correctamente"
            else:
                return False, "Vertex AI no está disponible en este entorno"
        except Exception as e:
            logger.error(f"Error verificando conexión con Vertex AI: {e}")
            return False, f"Error de conexión con Vertex AI: {str(e)}"

    async def check_a2a_optimized(self) -> Tuple[bool, str]:
        """
        Verifica el estado del servidor A2A optimizado.

        Returns:
            Tuple[bool, str]: Estado del servidor y mensaje.
        """
        try:
            # Obtener estadísticas del servidor
            stats = await a2a_optimized_server.get_stats()

            if stats.get("running", False):
                num_agents = len(stats.get("registered_agents", []))
                return (
                    True,
                    f"Servidor A2A optimizado activo con {num_agents} agentes registrados",
                )
            else:
                return False, "Servidor A2A optimizado no está en ejecución"
        except Exception as e:
            logger.error(f"Error verificando servidor A2A optimizado: {e}")
            return False, f"Error al verificar servidor A2A optimizado: {str(e)}"

    def get_full_health_report(self) -> Dict[str, Any]:
        """
        Obtiene un informe completo del estado de la aplicación.

        Este método recopila información detallada sobre el estado de la aplicación,
        incluyendo métricas, configuración y estado de las dependencias.

        Returns:
            Dict[str, Any]: Informe completo del estado de la aplicación.
        """
        return {
            "application": {
                "name": "NGX Agents",
                "version": "1.0.0",
                "uptime_seconds": time.time() - STARTUP_TIME,
                "startup_time": self.startup_check_time,
                "startup_complete": self.startup_checks_passed,
            },
            "system": {"timestamp": time.time(), "environment": "production"},
        }


# Instancia global para health checks
health_check = HealthCheck()

# Registrar dependencias comunes
health_check.register_dependency("supabase", health_check.check_supabase, critical=True)
health_check.register_dependency(
    "vertex_ai", health_check.check_vertex_ai, critical=True
)
health_check.register_dependency(
    "a2a_optimized", health_check.check_a2a_optimized, critical=True
)
