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
# from google.adk.agents import Agent # Ya no se hereda directamente
from adk.toolkit import Toolkit # Para el parámetro adk_toolkit de BaseAgent

# Importaciones internas
from agents.base.a2a_agent import A2AAgent # Nueva clase base
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)


class ADKAgent(A2AAgent): 
    """
    Clase base unificada para agentes NGX que usan Google ADK y el protocolo A2A.
    
    Hereda de A2AAgent (que a su vez hereda de BaseAgent y google.adk.agents.Agent)
    y añade gestión de estado específica (StateManager) y otras funcionalidades comunes de NGX.
    """
    # Declarar campos específicos de ADKAgent para Pydantic si es necesario
    # agent_id: str # Heredado de BaseAgent
    state_manager: Optional[StateManager] = None # Mantenemos StateManager si tiene un uso específico

    def __init__(
        self,
        # Parámetros requeridos por A2AAgent/BaseAgent/GoogleAgent
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[str], # Para A2AAgent (genera a2a_skills) y BaseAgent

        # Parámetros específicos de google.adk.agents.Agent
        model: str, 
        instruction: str, 
        google_adk_tools: Optional[Sequence[Callable]] = None, # Skills para Google ADK

        # Parámetros específicos de A2AAgent
        a2a_skills: Optional[List[Dict[str, str]]] = None, # Skills para AgentCard A2A
        endpoint: Optional[str] = None,
        auto_register_skills: bool = True,
        a2a_server_url: Optional[str] = None,
        
        # Parámetros específicos de BaseAgent
        version: str = "1.0.0",
        adk_toolkit: Optional[Toolkit] = None, # adk.toolkit.Toolkit para BaseAgent
        
        # Otros kwargs para google.adk.agents.Agent (e.g. response_format, temperature)
        **kwargs 
    ):
        """
        Inicializa un agente NGX unificado compatible con Google ADK y A2A.
        
        Args:
            agent_id: ID del agente.
            name: Nombre del agente.
            description: Descripción del agente.
            capabilities: Lista de capacidades (para A2AAgent/BaseAgent).
            model: Modelo a usar por el agente (para google.adk.agents.Agent).
            instruction: Instrucción principal para el agente (para google.adk.agents.Agent).
            google_adk_tools: Secuencia de funciones (skills) que el agente ADK puede usar.
            a2a_skills: Lista de habilidades para la AgentCard de A2A.
            endpoint: Endpoint HTTP para A2A.
            auto_register_skills: Si True, registra automáticamente las skills de A2AAgent.
            a2a_server_url: URL del servidor A2A.
            version: Versión del agente (para BaseAgent).
            adk_toolkit: Instancia de adk.toolkit.Toolkit (para BaseAgent).
            **kwargs: Argumentos adicionales para pasar a google.adk.agents.Agent.
        """
        # Preparar kwargs para las clases base
        # google.adk.agents.Agent espera 'tools', no 'google_adk_tools'
        if google_adk_tools:
            kwargs['tools'] = google_adk_tools
        
        # BaseAgent espera 'toolkit', no 'adk_toolkit'
        if adk_toolkit:
            kwargs['toolkit'] = adk_toolkit

        # Llamar al constructor de A2AAgent
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            endpoint=endpoint,
            version=version,
            skills=a2a_skills, 
            auto_register_skills=auto_register_skills,
            a2a_server_url=a2a_server_url,
            # Pasar model, instruction y otros kwargs para BaseAgent y google.adk.agents.Agent
            model=model, 
            instruction=instruction,
            **kwargs
        )
        
        # Atributos específicos de NGX que ADKAgent gestiona adicionalmente
        # self.agent_id = agent_id # Ya gestionado por BaseAgent
        self.state_manager = self.state_manager or StateManager()
        
        # self._state: Dict[str, Any] = {} # Eliminado, se usa el de BaseAgent
        
        self._setup_telemetry()
        
        logger.info(f"Agente ADK unificado (Name: {self.name}, ID: {self.agent_id}) inicializado.")

    def _setup_telemetry(self):
        """
        Configura la telemetría para el agente.
        
        Placeholder para configuración futura de OpenTelemetry u otros.
        """
        # TODO: Implementar configuración de telemetría (ej: OpenTelemetry)
        pass

    # def get_state(self, key: str, default: Any = None) -> Any: # Eliminado, usar el de BaseAgent
    #     """
    #     Obtiene un valor del estado interno del agente.
    #     
    #     Args:
    #         key: Clave del estado
    #         default: Valor por defecto si la clave no existe
    #     
    #     Returns:
    #         Any: Valor del estado o valor por defecto
    #     """
    #     return self._state.get(key, default) # self._state ya no existe aquí

    # def update_state(self, key: str, value: Any) -> None: # Eliminado, usar el de BaseAgent
    #     """
    #     Actualiza el estado interno del agente.
    #     
    #     Args:
    #         key: Clave del estado
    #         value: Valor a almacenar
    #     """
    #     self._state[key] = value # self._state ya no existe aquí

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

    # Métodos de lógica de negocio de NGX que permanecen en ADKAgent
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
        """Obtiene el tipo de programa (PRIME/LONGEVITY/GENERAL) del perfil del cliente."""
        # Obtener el valor de program_type del perfil.
        program_value = client_profile.get("program_type")

        # Si program_type no está presente, es None, o es un string vacío, usar "PRIME" por defecto.
        if not program_value: # Esto cubre None, '', False, etc.
            selected_program = "PRIME"
        else:
            # Convertir a string (por si acaso) y luego a mayúsculas.
            selected_program = str(program_value).upper()
        
        # Lista de tipos de programa válidos que pueden ser retornados directamente.
        valid_program_types = ["PRIME", "LONGEVITY", "GENERAL"]
        
        # Si el programa seleccionado (después de uppercasing) está en la lista de válidos, retornarlo.
        # De lo contrario, retornar "GENERAL" como fallback.
        if selected_program in valid_program_types:
            return selected_program
        else:
            return "GENERAL"

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
# de vida principal y la comunicación, y A2AAgent maneja la lógica A2A.
