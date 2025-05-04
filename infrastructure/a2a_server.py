"""
Servidor A2A (Agent-to-Agent) basado en Google ADK.

Este módulo proporciona funcionalidades para iniciar y gestionar un servidor A2A
que permite la comunicación entre agentes mediante WebSockets.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, List, Optional, Any, Callable

# Importar ADK cuando esté disponible
try:
    from adk.server import Server as ADKServer
    from adk.server import ServerConfig
except ImportError:
    print("Error: No se pudo importar el módulo 'adk'. Asegúrate de instalar google-adk.")
    print("Ejecuta: poetry add google-adk")
    sys.exit(1)

from core.logging_config import get_logger
from core.settings import settings

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


async def run_server():
    """
    Función principal para ejecutar el servidor A2A como un proceso independiente.
    """
    # Configurar manejo de señales para detener el servidor
    loop = asyncio.get_event_loop()
    
    # Manejador de señales para detener el servidor
    async def handle_signal():
        logger.info("Recibida señal de terminación. Deteniendo servidor A2A...")
        await server.stop()
    
    # Registrar manejadores de señales
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(handle_signal()))
    
    # Iniciar servidor
    server = get_a2a_server()
    try:
        await server.start()
    except Exception as e:
        logger.error(f"Error en el servidor A2A: {e}")
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
