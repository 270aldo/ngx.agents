"""
Router de agentes para la API de NGX Agents.

Este módulo proporciona endpoints para interactuar con los agentes
del sistema NGX Agents.
"""

from typing import Dict, List, Any
import importlib
import inspect
import os

from fastapi import APIRouter, Depends, HTTPException, status, Path

from core.auth import get_current_user
from core.logging_config import get_logger
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from app.schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentInfo,
    AgentListResponse,
)
from agents.base.base_agent import BaseAgent
from tools.mcp_toolkit import MCPToolkit
from agents.orchestrator.agent import NGXNexusOrchestrator
from config import settings

# Configurar logger
logger = get_logger(__name__)

# Crear router
router = APIRouter(
    prefix="/agents",
    tags=["agentes"],
    responses={401: {"description": "No autorizado"}},
)


def get_state_manager() -> StateManager:
    """
    Dependencia para obtener una instancia del StateManager.

    Returns:
        Instancia del StateManager
    """
    return state_manager_adapter


def discover_agents() -> Dict[str, BaseAgent]:
    """
    Descubre todos los agentes disponibles en el sistema.

    Returns:
        Diccionario con los agentes disponibles (agent_id -> instancia)
    """
    agents = {}
    agents_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "agents"
    )

    # Excluir directorios y módulos que no son agentes
    exclude_dirs = ["__pycache__", "base"]

    # Preparar dependencias comunes
    try:
        sm_instance = get_state_manager()
        toolkit_instance = MCPToolkit()
        a2a_url = f"http://{settings.A2A_HOST}:{settings.A2A_PORT}"
    except Exception as e:
        logger.error(
            f"Error al inicializar dependencias para discover_agents: {e}",
            exc_info=True,
        )
        # Si las dependencias fallan, no podemos instanciar agentes
        return agents

    # Recorrer todos los directorios en agents/
    for item in os.listdir(agents_path):
        item_path = os.path.join(agents_path, item)

        # Verificar si es un directorio y no está excluido
        if os.path.isdir(item_path) and item not in exclude_dirs:
            # Verificar si existe el archivo agent.py
            agent_file = os.path.join(item_path, "agent.py")
            if os.path.isfile(agent_file):
                try:
                    # Importar el módulo
                    module_name = f"agents.{item}.agent"
                    module = importlib.import_module(module_name)

                    # Buscar clases que heredan de BaseAgent
                    for name, obj_class in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj_class)
                            and issubclass(obj_class, BaseAgent)
                            and obj_class != BaseAgent
                        ):

                            # Preparar argumentos del constructor
                            constructor_args = {
                                "state_manager": sm_instance,
                                "mcp_toolkit": toolkit_instance,
                            }

                            # Si es el orquestador, añadir a2a_server_url
                            if obj_class == NGXNexusOrchestrator:
                                constructor_args["a2a_server_url"] = a2a_url
                                # Opcional: pasar un model_id específico si es necesario aquí
                                # constructor_args["model_id"] = settings.ORCHESTRATOR_DEFAULT_MODEL_ID

                            # Instanciar el agente con los argumentos preparados
                            agent_instance = obj_class(**constructor_args)
                            agents[agent_instance.agent_id] = agent_instance
                            logger.info(
                                f"Agente descubierto e instanciado: {agent_instance.agent_id} ({agent_instance.name})"
                            )

                except Exception as e:
                    logger.error(
                        f"Error al cargar o instanciar agente {item} ({module_name if 'module_name' in locals() else 'N/A'}): {e}",
                        exc_info=True,
                    )

    return agents


# Caché de agentes
_agents_cache: Dict[str, BaseAgent] = {}


def get_agents() -> Dict[str, BaseAgent]:
    """
    Obtiene todos los agentes disponibles (con caché).

    Returns:
        Diccionario con los agentes disponibles (agent_id -> instancia)
    """
    global _agents_cache

    if not _agents_cache:
        _agents_cache = discover_agents()

    return _agents_cache


def get_agent(agent_id: str) -> BaseAgent:
    """
    Obtiene un agente específico por su ID.

    Args:
        agent_id: ID del agente

    Returns:
        Instancia del agente

    Raises:
        HTTPException: Si el agente no existe
    """
    agents = get_agents()

    if agent_id not in agents:
        logger.warning(f"Agente no encontrado: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado",
        )

    return agents[agent_id]


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    user_id: str = Depends(get_current_user),
) -> Dict[str, List[AgentInfo]]:
    """
    Lista todos los agentes disponibles.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Lista de agentes disponibles
    """
    agents = get_agents()

    agent_list = [
        AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            capabilities=agent.capabilities,
        )
        for agent in agents.values()
    ]

    logger.info(f"Usuario {user_id} solicitó lista de agentes")

    return {"agents": agent_list}


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
async def run_agent(
    agent_id: str = Path(..., description="ID del agente a ejecutar"),
    request: AgentRunRequest = ...,
    user_id: str = Depends(get_current_user),
    state_manager: StateManager = Depends(get_state_manager),
) -> Dict[str, Any]:
    """
    Ejecuta un agente con un texto de entrada.

    Args:
        agent_id: ID del agente a ejecutar
        request: Datos de la solicitud
        user_id: ID del usuario autenticado
        state_manager: Gestor de estados

    Returns:
        Respuesta del agente
    """
    # Obtener el agente
    agent = get_agent(agent_id)

    # Obtener o generar session_id
    session_id = request.session_id or None

    try:
        # Ejecutar el agente
        logger.info(f"Ejecutando agente {agent_id} para usuario {user_id}")

        result = await agent.run_async(
            input_text=request.input_text,
            user_id=user_id,
            session_id=session_id,
            context=request.context or {},
        )

        # Extraer session_id del resultado
        session_id = result.get("session_id", session_id)

        # Construir respuesta
        response = AgentRunResponse(
            agent_id=agent_id,
            response=result.get("response", ""),
            session_id=session_id,
            metadata=result.get("metadata", {}),
        )

        logger.info(f"Agente {agent_id} ejecutado correctamente para usuario {user_id}")

        return response

    except Exception as e:
        logger.error(f"Error al ejecutar agente {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al ejecutar agente: {str(e)}",
        )
