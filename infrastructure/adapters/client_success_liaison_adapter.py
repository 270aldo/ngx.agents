"""
Adaptador para el agente ClientSuccessLiaison que utiliza los componentes optimizados.

Este adaptador extiende el agente ClientSuccessLiaison original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from agents.client_success_liaison.agent import ClientSuccessLiaison
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)


class ClientSuccessLiaisonAdapter(ClientSuccessLiaison, BaseAgentAdapter):
    """
    Adaptador para el agente ClientSuccessLiaison que utiliza los componentes optimizados.

    Este adaptador extiende el agente ClientSuccessLiaison original y sobrescribe los métodos
    necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
    """

    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente ClientSuccessLiaison.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "calendars": [],
            "journey_maps": [],
            "support_requests": [],
            "last_updated": datetime.now().isoformat(),
        }

    async def _classify_query_with_intent_analyzer(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando el Intent Analyzer.

        Args:
            query: Consulta del usuario

        Returns:
            str: Tipo de consulta clasificada
        """
        try:
            # Utilizar el Intent Analyzer para analizar la intención
            intent_analysis = await self.intent_analyzer.analyze(
                query, agent_type=self.__class__.__name__
            )

            # Obtener el mapeo de intenciones a tipos de consulta
            intent_to_query_type = self._get_intent_to_query_type_mapping()

            # Buscar coincidencias en el mapeo
            for intent, query_type in intent_to_query_type.items():
                if intent.lower() in query.lower():
                    return query_type

            # Si no hay coincidencias, devolver un tipo genérico
            return "general_inquiry"
        except Exception as e:
            logger.error(
                f"Error al clasificar consulta con Intent Analyzer: {e}", exc_info=True
            )
            # En caso de error, devolver un tipo genérico
            return "general_inquiry"

    async def _consult_other_agent(
        self,
        agent_id: str,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
                "additional_context": context or {},
            }

            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id, user_input=query, context=task_context
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
                "agent_name": agent_id,
            }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para ClientSuccessLiaison.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "community": "community_building",
            "experience": "user_experience",
            "support": "customer_support",
            "retention": "retention_strategies",
            "communication": "communication_management",
            "search": "web_search",
        }

    async def _process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        program_type: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.

        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales

        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        try:
            # Intentar clasificar la consulta con el Intent Analyzer primero
            query_type = await self._classify_query_with_intent_analyzer(query)

            # Procesar la consulta según el tipo determinado
            logger.info(f"Procesando consulta de tipo: {query_type}")

            # Aquí iría la lógica específica del agente ClientSuccessLiaison
            # Por ahora, simplemente devolvemos una respuesta genérica
            return {
                "success": True,
                "output": f"Respuesta para consulta de tipo {query_type}",
                "query_type": query_type,
                "program_type": program_type,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error al procesar consulta: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
            }
