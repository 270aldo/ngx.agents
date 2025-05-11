"""
Adaptador para el agente MotivationBehaviorCoach que utiliza los componentes optimizados.

Este adaptador extiende el agente MotivationBehaviorCoach original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from agents.motivation_behavior_coach.agent import MotivationBehaviorCoach
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from clients.vertex_ai_client_adapter import vertex_ai_client
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

class MotivationBehaviorCoachAdapter(MotivationBehaviorCoach):
    """
    Adaptador para el agente MotivationBehaviorCoach que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente MotivationBehaviorCoach original y sobrescribe los métodos
    necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
    """
    
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el adaptador del StateManager.

        Args:
            user_id (Optional[str]): ID del usuario.
            session_id (Optional[str]): ID de la sesión.

        Returns:
            Dict[str, Any]: Contexto de la conversación.
        """
        try:
            # Intentar cargar desde el adaptador del StateManager
            if user_id and session_id:
                try:
                    state_data = await state_manager_adapter.load_state(user_id, session_id)
                    if state_data and isinstance(state_data, dict):
                        logger.debug(f"Contexto cargado desde adaptador del StateManager para user_id={user_id}, session_id={session_id}")
                        return state_data
                except Exception as e:
                    logger.warning(f"Error al cargar contexto desde adaptador del StateManager: {e}")
            
            # Si no hay contexto o hay error, crear uno nuevo
            return {
                "conversation_history": [],
                "user_profile": {},
                "habit_plans": [],
                "goal_plans": [],
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "habit_plans": [],
                "goal_plans": [],
                "last_updated": datetime.now().isoformat()
            }

    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el adaptador del StateManager.

        Args:
            context (Dict[str, Any]): Contexto actualizado.
            user_id (str): ID del usuario.
            session_id (str): ID de la sesión.
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = datetime.now().isoformat()
            
            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(user_id, session_id, context)
            logger.info(f"Contexto actualizado en adaptador del StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    async def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando el adaptador del Intent Analyzer.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        try:
            # Utilizar el adaptador del Intent Analyzer para analizar la intención
            intent_analysis = await intent_analyzer_adapter.analyze_intent(query)
            
            # Mapear la intención primaria a los tipos de consulta del agente
            primary_intent = intent_analysis.get("primary_intent", "").lower()
            
            # Mapeo de intenciones a tipos de consulta
            intent_to_query_type = {
                "habit": "habit_formation",
                "motivation": "motivation_strategies",
                "behavior": "behavior_change",
                "goal": "goal_setting",
                "obstacle": "obstacle_management"
            }
            
            # Buscar coincidencias exactas
            if primary_intent in intent_to_query_type:
                return intent_to_query_type[primary_intent]
            
            # Buscar coincidencias parciales
            for intent, query_type in intent_to_query_type.items():
                if intent in primary_intent:
                    return query_type
            
            # Si no hay coincidencias, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
        except Exception as e:
            logger.error(f"Error al clasificar consulta con Intent Analyzer: {e}", exc_info=True)
            # En caso de error, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
    
    def _classify_query_by_keywords(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando palabras clave.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()
        
        # Palabras clave para formación de hábitos
        habit_keywords = [
            "hábito", "rutina", "costumbre", "diario", "consistencia", 
            "establecer", "formar", "crear", "mantener", "desarrollar"
        ]
        
        # Palabras clave para estrategias de motivación
        motivation_keywords = [
            "motivación", "motivar", "inspirar", "impulso", "ánimo", 
            "energía", "entusiasmo", "ganas", "deseo", "voluntad"
        ]
        
        # Palabras clave para cambio de comportamiento
        behavior_keywords = [
            "comportamiento", "conducta", "cambiar", "modificar", "transformar", 
            "ajustar", "adaptar", "mejorar", "corregir", "reemplazar"
        ]
        
        # Palabras clave para establecimiento de metas
        goal_keywords = [
            "meta", "objetivo", "propósito", "plan", "logro", 
            "alcanzar", "conseguir", "cumplir", "establecer", "fijar"
        ]
        
        # Palabras clave para manejo de obstáculos
        obstacle_keywords = [
            "obstáculo", "barrera", "problema", "dificultad", "desafío", 
            "impedimento", "limitación", "resistencia", "bloqueo", "superar"
        ]
        
        # Verificar coincidencias con palabras clave
        for keyword in habit_keywords:
            if keyword in query_lower:
                return "habit_formation"
                
        for keyword in motivation_keywords:
            if keyword in query_lower:
                return "motivation_strategies"
                
        for keyword in behavior_keywords:
            if keyword in query_lower:
                return "behavior_change"
                
        for keyword in goal_keywords:
            if keyword in query_lower:
                return "goal_setting"
                
        for keyword in obstacle_keywords:
            if keyword in query_lower:
                return "obstacle_management"
                
        # Si no hay coincidencias, devolver tipo general
        return "motivation_strategies"
    
    async def _consult_other_agent(self, agent_id: str, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta a otro agente utilizando el adaptador de A2A.
        
        Args:
            agent_id: ID del agente a consultar
            query: Consulta a enviar al agente
            user_id: ID del usuario
            session_id: ID de la sesión
            context: Contexto adicional para la consulta
            
        Returns:
            Dict[str, Any]: Respuesta del agente consultado
        """
        try:
            # Crear contexto para la consulta
            task_context = {
                "user_id": user_id,
                "session_id": session_id,
                "additional_context": context or {}
            }
            
            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id,
                user_input=query,
                context=task_context
            )
            
            logger.info(f"Respuesta recibida del agente {agent_id}")
            return response
        except Exception as e:
            logger.error(f"Error al consultar al agente {agent_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al consultar al agente {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id
            }
