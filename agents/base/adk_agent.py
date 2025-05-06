import asyncio
import json
import uuid
import time
import logging
import traceback
import signal
from typing import Dict, List, Any, Optional, Callable, Union, Type, Tuple, Sequence
from datetime import datetime

# Importar componentes de Google ADK directamente
from google.adk.agents import Agent

# Importaciones internas
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)


class ADKAgent(Agent): 
    """
    Clase base extendida para agentes NGX que usan Google ADK.
    
    Hereda de google.adk.agents.Agent y añade gestión de estado y 
    posiblemente otras funcionalidades comunes de NGX.
    """
    # Declarar campos específicos de ADKAgent para Pydantic
    agent_id: str
    state_manager: Optional[StateManager] = None

    def __init__(
        self,
        # Parámetros estándar de google.adk.agents.Agent (no predeterminados primero)
        agent_id: str,
        name: str,
        description: str,
        model: str, 
        instruction: str, 
        # Parámetros específicos de NGX y otros con valores predeterminados
        tools: Optional[Sequence[Callable]] = None, 
        # Otros parámetros opcionales de Agent que podríamos querer exponer
        # response_format: Optional[str] = None,
        # temperature: Optional[float] = None,
        # ... otros
        **kwargs 
    ):
        """
        Inicializa un agente NGX compatible con Google ADK.
        
        Args:
            agent_id: ID del agente.
            name: Nombre del agente (para google.adk.agents.Agent).
            description: Descripción del agente (para google.adk.agents.Agent).
            model: Modelo a usar por el agente (ej: 'gemini-1.5-flash', para google.adk.agents.Agent).
            instruction: Instrucción principal para el agente (para google.adk.agents.Agent).
            tools: Secuencia de funciones (skills) que el agente puede usar (para google.adk.agents.Agent).
            **kwargs: Argumentos adicionales para pasar a google.adk.agents.Agent.
        """
        # Llamar al constructor de la clase base google.adk.agents.Agent
        super().__init__(
            # Pasar agent_id también a la base
            agent_id=agent_id,
            name=name,
            description=description,
            model=model,
            instruction=instruction,
            tools=tools,
            # Pasar otros kwargs relevantes si los hubiera
            **kwargs
        )
        
        # Atributos específicos de NGX
        self.agent_id = agent_id
        self.state_manager = self.state_manager or StateManager()
        
        # Ya no manejamos toolkit, client, agent_card aquí
        # self.toolkit = None 
        # self.adk_client: Optional[ADKClient] = None
        # self.agent_card: GoogleAgentCard = self._create_agent_card()
        
        # Estado interno (si aún es necesario más allá de StateManager)
        self._state: Dict[str, Any] = {}
        # self._running = False 
        # self._message_queue = asyncio.Queue() 
        
        # Configurar telemetría (si aplica a nuestra capa)
        self._setup_telemetry()
        
        logger.info(f"Agente ADK (Name: {self.name}) inicializado.")

    def _setup_telemetry(self):
        """
        Configura la telemetría para el agente.
        
        Placeholder para configuración futura de OpenTelemetry u otros.
        """
        # TODO: Implementar configuración de telemetría (ej: OpenTelemetry)
        pass

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor del estado interno del agente.
        
        Args:
            key: Clave del estado
            default: Valor por defecto si la clave no existe
        
        Returns:
            Any: Valor del estado o valor por defecto
        """
        return self._state.get(key, default)

    def update_state(self, key: str, value: Any) -> None:
        """
        Actualiza el estado interno del agente.
        
        Args:
            key: Clave del estado
            value: Valor a almacenar
        """
        self._state[key] = value

    # --------------------------------------------------------------------------
    # Métodos eliminados que ahora debería manejar google.adk.agents.Agent:
    # - _create_agent_card
    # - connect_to_adk
    # - disconnect_from_adk
    # - send_task_to_agent
    # - register_skill
    # - execute_skill
    # - handle_task
    # - start / stop / run (probablemente manejados por la clase base Agent)
    # --------------------------------------------------------------------------

    # Podríamos añadir métodos específicos de NGX aquí si fuera necesario,
    # por ejemplo, para interactuar con Supabase o gestionar contexto específico.
    async def _get_context(self, user_id: str, session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Método placeholder para obtener contexto (perfil, historial) del usuario.
        Las subclases deberían implementar esto usando su cliente (ej: Supabase).
        """
        logger.warning(f"_get_context no implementado en ADKAgent base para user_id {user_id}")
        return {"client_profile": {}, "history": []}

    async def _update_context(self, user_id: str, session_id: Optional[str], interaction_data: Dict[str, Any], **kwargs) -> None:
        """
        Método placeholder para actualizar el contexto del usuario.
        Las subclases deberían implementar esto.
        """
        logger.warning(f"_update_context no implementado en ADKAgent base para user_id {user_id}")
        pass

    def _get_program_type_from_profile(self, client_profile: Dict[str, Any]) -> str:
        """Obtiene el tipo de programa (PRIME/LONGEVITY) del perfil."""
        # Implementación simple, podría ser más robusta
        program = client_profile.get("program_type", "PRIME").upper()
        return program if program in ["PRIME", "LONGEVITY"] else "PRIME"

    def _extract_profile_details(self, client_profile: Dict[str, Any]) -> str:
        """Convierte detalles clave del perfil en un string formateado."""
        details = []
        if client_profile:
            details.append(f"- Programa: {self._get_program_type_from_profile(client_profile)}")
            if goals := client_profile.get('goals'): details.append(f"- Objetivos: {goals}")
            if level := client_profile.get('experience_level'): details.append(f"- Experiencia: {level}")
            if metrics := client_profile.get('current_metrics'): details.append(f"- Métricas: {metrics}")
            if prefs := client_profile.get('preferences'): details.append(f"- Preferencias: {prefs}")
            if injuries := client_profile.get('injury_history'): details.append(f"- Lesiones: {injuries}")
        return "\n".join(details) if details else "No disponible"

# Nota: Se eliminaron los métodos _handle_adk_*, start, stop, run, _process_messages,
# ya que se asume que la clase base google.adk.agents.Agent se encarga del ciclo
# de vida principal y la comunicación.
