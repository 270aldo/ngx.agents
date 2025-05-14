"""
Adaptador para el agente BiohackingInnovator que utiliza los componentes optimizados.

Este adaptador extiende el agente BiohackingInnovator original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union

from agents.biohacking_innovator.agent import BiohackingInnovator
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

class BiohackingInnovatorAdapter(BiohackingInnovator, BaseAgentAdapter):
    """
    Adaptador para el agente BiohackingInnovator que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente BiohackingInnovator original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """
    
    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente BiohackingInnovator.
        
        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "protocols": [],
            "resources_used": [],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para BiohackingInnovator.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "hormonal": "hormonal_optimization",
            "hormonal_optimization": "hormonal_optimization",
            "cognitive": "cognitive_enhancement",
            "cognitive_enhancement": "cognitive_enhancement",
            "longevity": "longevity",
            "biohacking": "biohacking"
        }
