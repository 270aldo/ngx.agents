"""
Adaptador para el agente PrecisionNutritionArchitect que utiliza los componentes optimizados.

Este adaptador extiende el agente PrecisionNutritionArchitect original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

from typing import Dict, Any
from datetime import datetime

from agents.precision_nutrition_architect.agent import PrecisionNutritionArchitect
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)


class PrecisionNutritionArchitectAdapter(PrecisionNutritionArchitect, BaseAgentAdapter):
    """
    Adaptador para el agente PrecisionNutritionArchitect que utiliza los componentes optimizados.

    Este adaptador extiende el agente PrecisionNutritionArchitect original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """

    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente PrecisionNutritionArchitect.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "meal_plans": [],
            "supplement_recommendations": [],
            "biomarker_analyses": [],
            "last_updated": datetime.now().isoformat(),
        }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para PrecisionNutritionArchitect.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "meal_plan": "create_meal_plan",
            "supplement": "recommend_supplements",
            "biomarker": "analyze_biomarkers",
            "chrononutrition": "plan_chrononutrition",
        }
