"""
Punto de entrada para ejecutar el GeminiTrainingAssistant como un proceso independiente.
"""

import asyncio
import os
import sys
from typing import Dict, Any, Optional

# Añadir el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.gemini_training_assistant.agent import GeminiTrainingAssistant
from agents.base.adk_agent import run_agent
from core.logging_config import setup_logging, get_logger
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from clients.supabase_client import SupabaseClient

# Configurar logging
setup_logging()
logger = get_logger(__name__)


async def main():
    """
    Función principal para ejecutar el GeminiTrainingAssistant.
    """
    try:
        # Crear instancia de StateManager
        supabase_client = SupabaseClient()
        state_manager = StateManager(supabase_client)
        
        # Ejecutar GeminiTrainingAssistant
        await run_agent(
            GeminiTrainingAssistant,
            a2a_server_url=os.environ.get("A2A_SERVER_URL", "ws://localhost:9000"),
            state_manager=state_manager
        )
    except Exception as e:
        logger.error(f"Error al ejecutar el GeminiTrainingAssistant: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """
    Punto de entrada para ejecutar el GeminiTrainingAssistant como un proceso independiente.
    """
    asyncio.run(main())
