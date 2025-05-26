"""
Punto de entrada para ejecutar el ProgressTracker como un proceso independiente.
"""

import asyncio
import os
import sys

# Añadir el directorio raíz al path para importar módulos
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from agents.progress_tracker.agent import ProgressTracker
from agents.base.adk_agent import run_agent
from core.logging_config import setup_logging, get_logger
from clients.supabase_client import SupabaseClient

# Configurar logging
setup_logging()
logger = get_logger(__name__)


async def main():
    """
    Función principal para ejecutar el ProgressTracker.
    """
    try:
        # Crear instancia de StateManager
        supabase_client = SupabaseClient()
        state_manager = StateManager(supabase_client)

        # Ejecutar ProgressTracker
        await run_agent(
            ProgressTracker,
            a2a_server_url=os.environ.get("A2A_SERVER_URL", "ws://localhost:9000"),
            state_manager=state_manager,
        )
    except Exception as e:
        logger.error(f"Error al ejecutar el ProgressTracker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """
    Punto de entrada para ejecutar el ProgressTracker como un proceso independiente.
    """
    asyncio.run(main())
