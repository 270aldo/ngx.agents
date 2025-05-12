"""
Pruebas unitarias para el agente MotivationBehaviorCoach.

Estas pruebas verifican que el agente MotivationBehaviorCoach utiliza correctamente
el servicio de clasificación de programas para personalizar sus estrategias de motivación
y cambio de comportamiento según el tipo de programa del usuario.
"""
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest

# Añadir el directorio raíz al path para importar los módulos del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.motivation_behavior_coach.agent import MotivationBehaviorCoach
from agents.motivation_behavior_coach.schemas import (
    MotivationStrategiesInput,
    HabitFormationInput
)
from services.program_classification_service import ProgramClassificationService


class TestMotivationBehaviorCoach(unittest.TestCase):
    """Pruebas unitarias para el agente MotivationBehaviorCoach."""

    def setUp(self):
        """Configuración inicial para las pruebas."""
        # Crear mocks para los clientes y servicios
        self.mock_gemini_client = MagicMock()
        self.mock_gemini_client.generate_structured_output = AsyncMock(
            return_value={
                "analysis": "Análisis motivacional de prueba",
                "strategies": [
                    {
                        "name": "Estrategia de prueba 1",
                        "description": "Descripción de la estrategia 1",
                        "implementation": "Implementación de la estrategia 1",
                        "science_behind": "Ciencia detrás de la estrategia 1",
                        "example": "Ejemplo de la estrategia 1"
                    },
                    {
                        "name": "Estrategia de prueba 2",
                        "description": "Descripción de la estrategia 2",
                        "implementation": "Implementación de la estrategia 2",
                        "science_behind": "Ciencia detrás de la estrategia 2",
                        "example": "Ejemplo de la estrategia 2"
                    }
                ],
                "daily_practices": ["Práctica 1", "Práctica 2"],
                "long_term_approach": "Enfoque a largo plazo de prueba"
            }
        )
        
        # Mock para el servicio de clasificación de programas
        self.mock_program_classification_service = MagicMock()
        self.mock_program_classification_service.classify_program_type = AsyncMock(return_value="PRIME")
        
        # Crear el agente con mocks
        with patch('agents.motivation_behavior_coach.agent.GeminiClient', return_value=self.mock_gemini_client), \
             patch('agents.motivation_behavior_coach.agent.ProgramClassificationService', return_value=self.mock_program_classification_service), \
             patch('agents.motivation_behavior_coach.agent.SupabaseClient'):
            self.agent = MotivationBehaviorCoach()

    @pytest.mark.asyncio
    async def test_motivation_strategies_with_program_classification(self):
        """Prueba que _skill_motivation_strategies utiliza el servicio de clasificación de programas."""
        # Preparar datos de entrada
        input_data = MotivationStrategiesInput(
            user_input="Necesito estrategias para mantenerme motivado durante mi entrenamiento",
            user_profile={
                "name": "Usuario de prueba",
                "goals": ["Mejorar rendimiento", "Aumentar fuerza"],
                "challenges": ["Falta de tiempo", "Fatiga"],
                "preferences": ["Entrenamiento por la mañana"]
            }
        )
        
        # Ejecutar la skill
        result = await self.agent._skill_motivation_strategies(input_data)
        
        # Verificar que se llamó al servicio de clasificación de programas
        self.mock_program_classification_service.classify_program_type.assert_called_once()
        
        # Verificar que el resultado incluye el tipo de programa
        self.assertEqual(result.program_type, "PRIME")
        
        # Verificar que el análisis incluye información del programa
        self.assertTrue("[PRIME]" in result.analysis or "PRIME" in result.analysis)
        
        # Verificar que el enfoque a largo plazo incluye información del programa
        self.assertTrue("[PRIME]" in result.long_term_approach or "PRIME" in result.long_term_approach)

    @pytest.mark.asyncio
    async def test_motivation_strategies_with_classification_error(self):
        """Prueba que _skill_motivation_strategies maneja correctamente errores en la clasificación de programas."""
        # Configurar el mock para lanzar una excepción
        self.mock_program_classification_service.classify_program_type.side_effect = Exception("Error de clasificación")
        
        # Preparar datos de entrada
        input_data = MotivationStrategiesInput(
            user_input="Necesito estrategias para mantenerme motivado durante mi entrenamiento",
            user_profile={}
        )
        
        # Ejecutar la skill
        result = await self.agent._skill_motivation_strategies(input_data)
        
        # Verificar que el resultado tiene estrategias a pesar del error
        self.assertTrue(len(result.strategies) > 0)
        
        # Verificar que el resultado tiene prácticas diarias a pesar del error
        self.assertTrue(len(result.daily_practices) > 0)
        
        # Verificar que el resultado tiene un enfoque a largo plazo a pesar del error
        self.assertTrue(result.long_term_approach)

    @pytest.mark.asyncio
    async def test_generate_motivation_strategies_includes_program_info(self):
        """Prueba que _generate_motivation_strategies incluye información del programa en la respuesta."""
        # Ejecutar el método
        result = await self.agent._generate_motivation_strategies(
            "Necesito estrategias para mantenerme motivado",
            {"goals": ["Mejorar rendimiento"]}
        )
        
        # Verificar que el resultado incluye el tipo de programa
        self.assertTrue("program_type" in result)
        self.assertEqual(result["program_type"], "PRIME")
        
        # Verificar que el prompt enviado a Gemini incluye contexto específico del programa
        prompt_calls = [call[0][0] for call in self.mock_gemini_client.generate_structured_output.call_args_list]
        self.assertTrue(any("PRIME" in prompt for prompt in prompt_calls))


if __name__ == "__main__":
    unittest.main()
