"""
Pruebas unitarias para el agente PrecisionNutritionArchitect.

Verifica la integración con el servicio de clasificación de programas.
"""

import unittest
import asyncio
import json
from unittest.mock import patch, AsyncMock

from agents.precision_nutrition_architect.agent import PrecisionNutritionArchitect


class TestPrecisionNutritionArchitect(unittest.TestCase):
    """Pruebas para el agente PrecisionNutritionArchitect."""

    def setUp(self):
        """Configuración inicial para las pruebas."""
        # Crear mocks para las dependencias
        self.gemini_client_mock = AsyncMock()
        self.gemini_client_mock.generate_text = AsyncMock()
        self.gemini_client_mock.generate_text.return_value = json.dumps(
            {
                "supplements": [
                    {
                        "name": "Suplemento de prueba",
                        "dosage": "1 cápsula diaria",
                        "timing": "Con el desayuno",
                        "benefits": ["Beneficio 1", "Beneficio 2"],
                        "precautions": ["Precaución 1"],
                        "natural_alternatives": ["Alternativa 1"],
                    }
                ],
                "general_recommendations": "Recomendaciones generales de prueba",
            }
        )

        # Crear mock para el servicio de clasificación de programas
        self.program_classification_service_mock = AsyncMock()
        self.program_classification_service_mock.classify_program_type = AsyncMock()
        self.program_classification_service_mock.classify_program_type.return_value = (
            "PRIME"
        )

        # Crear instancia del agente con mocks
        with patch(
            "agents.precision_nutrition_architect.agent.GeminiClient",
            return_value=self.gemini_client_mock,
        ):
            with patch(
                "agents.precision_nutrition_architect.agent.ProgramClassificationService",
                return_value=self.program_classification_service_mock,
            ):
                self.agent = PrecisionNutritionArchitect()
                self.agent.gemini_client = self.gemini_client_mock
                self.agent.program_classification_service = (
                    self.program_classification_service_mock
                )

    def test_init(self):
        """Verifica que el agente se inicializa correctamente con el servicio de clasificación de programas."""
        self.assertIsNotNone(self.agent.program_classification_service)
        self.assertEqual(
            self.agent.program_classification_service,
            self.program_classification_service_mock,
        )

    def test_generate_supplement_recommendation(self):
        """Verifica que el método _generate_supplement_recommendation utiliza la información del programa."""
        # Definir datos de prueba
        user_input = "Necesito suplementos para mejorar mi rendimiento deportivo"
        user_profile = {
            "age": 35,
            "gender": "Masculino",
            "weight": 75,
            "height": 180,
            "goals": ["Mejorar rendimiento", "Aumentar masa muscular"],
        }
        program_type = "PRIME"
        program_supplements = ["Proteína de suero", "Creatina", "BCAA"]

        # Ejecutar el método
        result = asyncio.run(
            self.agent._generate_supplement_recommendation(
                user_input, user_profile, program_type, program_supplements
            )
        )

        # Verificar que se llamó a generate_text con el contexto del programa
        call_args = self.gemini_client_mock.generate_text.call_args[0][0]
        self.assertIn(program_type, call_args)
        for supplement in program_supplements:
            self.assertIn(supplement, call_args)

        # Verificar el resultado
        self.assertIn("supplements", result)
        self.assertIn("general_recommendations", result)
        self.assertEqual(len(result["supplements"]), 1)
        self.assertEqual(result["supplements"][0]["name"], "Suplemento de prueba")

    def test_skill_recommend_supplements_uses_program_classification(self):
        """Verifica que la skill _skill_recommend_supplements utiliza el servicio de clasificación de programas."""
        # Crear datos de entrada para la skill
        from agents.precision_nutrition_architect.agent import RecommendSupplementsInput

        input_data = RecommendSupplementsInput(
            user_input="Necesito suplementos para mejorar mi rendimiento deportivo",
            user_profile={
                "age": 35,
                "gender": "Masculino",
                "weight": 75,
                "height": 180,
                "goals": ["Mejorar rendimiento", "Aumentar masa muscular"],
            },
        )

        # Configurar el mock para _generate_supplement_recommendation
        self.agent._generate_supplement_recommendation = AsyncMock()
        self.agent._generate_supplement_recommendation.return_value = {
            "supplements": [
                {
                    "name": "Suplemento de prueba",
                    "dosage": "1 cápsula diaria",
                    "timing": "Con el desayuno",
                    "benefits": ["Beneficio 1", "Beneficio 2"],
                    "precautions": ["Precaución 1"],
                    "natural_alternatives": ["Alternativa 1"],
                }
            ],
            "general_recommendations": "Recomendaciones generales de prueba",
            "notes": "",
        }

        # Ejecutar la skill
        result = asyncio.run(self.agent._skill_recommend_supplements(input_data))

        # Verificar que se llamó al servicio de clasificación de programas
        self.program_classification_service_mock.classify_program_type.assert_called_once()

        # Verificar que se llamó a _generate_supplement_recommendation con los parámetros correctos
        self.agent._generate_supplement_recommendation.assert_called_once()
        call_args, call_kwargs = (
            self.agent._generate_supplement_recommendation.call_args
        )
        self.assertEqual(call_kwargs["program_type"], "PRIME")

        # Verificar el resultado
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result.dict())


if __name__ == "__main__":
    unittest.main()
