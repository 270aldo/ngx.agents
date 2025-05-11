"""
Servidor A2A (Agent-to-Agent) basado en Google ADK.

Este módulo proporciona funcionalidades para iniciar y gestionar un servidor A2A
que permite la comunicación entre agentes mediante WebSockets y expone endpoints
de monitorización de salud y métricas.
"""

import asyncio
import logging
import os
import signal
import sys
import json
import time
from typing import Dict, List, Optional, Any, Callable, Union
from aiohttp import web

# Importar ADK cuando esté disponible
try:
    from adk.server import Server as ADKServer
    from adk.server import ServerConfig
except ImportError:
    # Crear stubs mínimos para permitir que la aplicación se ejecute sin google-adk
    print("Advertencia: google-adk no instalado. Se usarán stubs para ADKServer/ServerConfig.")
    class ServerConfig:  # type: ignore
        """Stub de ServerConfig cuando google-adk no está disponible."""
        def __init__(self, host: str = "0.0.0.0", port: int = 9000):
            self.host = host
            self.port = port

    class ADKServer:  # type: ignore
        """Stub de ADKServer cuando google-adk no está disponible."""
        def __init__(self, config: 'ServerConfig'):
            self.config = config

        async def start(self) -> None:
            # Stub: no hace nada
            return None

        async def stop(self) -> None:
            # Stub: no hace nada
            return None

from core.logging_config import get_logger
from core.settings import settings
from infrastructure.health import health_monitor, health_endpoint, metrics_endpoint
from core.telemetry import health_tracker

# Configurar logger
logger = get_logger(__name__)

# Puerto por defecto para el servidor A2A
DEFAULT_A2A_PORT = 9000

class A2AServer:
    """
    Servidor A2A basado en Google ADK.
    
    Esta clase proporciona métodos para iniciar y gestionar un servidor A2A
    que permite la comunicación entre agentes mediante WebSockets.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_A2A_PORT):
        """
        Inicializa el servidor A2A.
        
        Args:
            host: Host en el que se ejecutará el servidor (por defecto: 0.0.0.0)
            port: Puerto en el que se ejecutará el servidor (por defecto: 9000)
        """
        self.host = host
        self.port = port
        self.server: Optional[ADKServer] = None
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"Servidor A2A inicializado en {host}:{port}")
    
    async def start(self) -> None:
        """
        Inicia el servidor A2A.
        
        Este método inicia el servidor A2A y lo mantiene en ejecución
        hasta que se llame al método stop().
        """
        try:
            # Configurar el servidor ADK
            config = ServerConfig(host=self.host, port=self.port)
            self.server = ADKServer(config)
            
            # Iniciar el servidor
            await self.server.start()
            logger.info(f"Servidor A2A iniciado en {self.host}:{self.port}")
            
            # Mantener el servidor en ejecución hasta que se solicite detenerlo
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error al iniciar el servidor A2A: {e}")
            raise
    
    async def stop(self) -> None:
        """
        Detiene el servidor A2A.
        """
        if self.server:
            await self.server.stop()
            logger.info("Servidor A2A detenido")
        
        self._shutdown_event.set()
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> None:
        """
        Registra un agente en el servidor A2A.
        
        Args:
            agent_id: ID del agente
            agent_info: Información del agente (nombre, descripción, etc.)
        """
        self.registered_agents[agent_id] = agent_info
        logger.info(f"Agente {agent_id} registrado en el servidor A2A")
        
        # Registrar el agente en el monitor de salud
        try:
            health_monitor.register_agent(agent_id)
        except Exception as e:
            logger.warning(f"No se pudo registrar el agente {agent_id} en el monitor de salud: {e}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Elimina el registro de un agente del servidor A2A.
        
        Args:
            agent_id: ID del agente
        """
        if agent_id in self.registered_agents:
            del self.registered_agents[agent_id]
            logger.info(f"Agente {agent_id} eliminado del servidor A2A")
    
    def get_registered_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene la lista de agentes registrados en el servidor A2A.
        
        Returns:
            Dict[str, Dict[str, Any]]: Diccionario de agentes registrados
        """
        return self.registered_agents


# Singleton para acceder al servidor A2A desde cualquier parte del código
_a2a_server_instance: Optional[A2AServer] = None

def get_a2a_server() -> A2AServer:
    """
    Obtiene la instancia del servidor A2A.
    
    Si no existe una instancia, la crea.
    
    Returns:
        A2AServer: Instancia del servidor A2A
    """
    global _a2a_server_instance
    
    if _a2a_server_instance is None:
        # Obtener configuración del entorno o usar valores por defecto
        host = os.environ.get("A2A_HOST", "0.0.0.0")
        port = int(os.environ.get("A2A_PORT", DEFAULT_A2A_PORT))
        
        _a2a_server_instance = A2AServer(host=host, port=port)
    
    return _a2a_server_instance


def get_a2a_server_status() -> Dict[str, Any]:
    """
    Obtiene el estado de salud del servidor A2A.
    
    Returns:
        Dict[str, Any]: Diccionario con el estado del servidor A2A
    """
    try:
        server = get_a2a_server()
        
        # Comprobar si el servidor está activo
        is_active = server.server is not None
        
        # Recopilar información de los agentes registrados
        num_agents = len(server.registered_agents)
        
        # Construir respuesta
        status_info = {
            "status": "ok" if is_active else "error",
            "timestamp": time.time(),
            "details": {
                "host": server.host,
                "port": server.port,
                "registered_agents": num_agents,
                "is_active": is_active
            }
        }
        
        # Actualizar estado en el health tracker
        health_tracker.update_status(
            component="a2a_server",
            status=is_active,
            details=f"Servidor A2A {'activo' if is_active else 'inactivo'} con {num_agents} agentes registrados",
            alert_on_degraded=True
        )
        
        return status_info
    
    except Exception as e:
        logger.error(f"Error al obtener el estado del servidor A2A: {e}")
        
        # Actualizar estado en el health tracker
        health_tracker.update_status(
            component="a2a_server",
            status=False,
            details=f"Error al obtener el estado del servidor A2A: {str(e)}",
            alert_on_degraded=True
        )
        
        return {
            "status": "error",
            "timestamp": time.time(),
            "details": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }


async def run_health_server(host: str = "0.0.0.0", port: int = 8001):
    """
    Inicia un servidor HTTP para los endpoints de salud y métricas.
    
    Args:
        host: Host en el que se ejecutará el servidor de salud
        port: Puerto en el que se ejecutará el servidor de salud
    """
    app = web.Application()
    
    # Registrar los endpoints de salud
    async def health_handler(request):
        return web.Response(
            text=health_endpoint(),
            content_type="application/json"
        )
    
    async def metrics_handler(request):
        return web.Response(
            text=metrics_endpoint(),
            content_type="application/json"
        )
    
    # Registrar rutas
    app.add_routes([
        web.get('/health', health_handler),
        web.get('/metrics', metrics_handler),
    ])
    
    # Iniciar el servidor
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Servidor de salud A2A iniciado en {host}:{port}")
    
    return runner

async def run_server():
    """
    Función principal para ejecutar el servidor A2A como un proceso independiente.
    """
    # Configurar manejo de señales para detener el servidor
    loop = asyncio.get_event_loop()
    
    # Manejador de señales para detener el servidor
    async def handle_signal():
        logger.info("Recibida señal de terminación. Deteniendo servidores...")
        if health_runner:
            await health_runner.cleanup()
        await server.stop()
    
    # Registrar manejadores de señales
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(handle_signal()))
    
    # Iniciar servidores
    server = get_a2a_server()
    
    # Obtener configuración para el servidor de salud
    health_host = os.environ.get("A2A_HEALTH_HOST", "0.0.0.0")
    health_port = int(os.environ.get("A2A_HEALTH_PORT", 8001))
    
    try:
        # Iniciar el servidor de salud
        health_runner = await run_health_server(host=health_host, port=health_port)
        
        # Iniciar el servidor A2A principal
        await server.start()
    except Exception as e:
        logger.error(f"Error en los servidores A2A: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """
    Punto de entrada para ejecutar el servidor A2A como un proceso independiente.
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Ejecutar servidor
    asyncio.run(run_server())
