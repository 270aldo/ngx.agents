"""
Pruebas unitarias para el agente BiohackingInnovator.

Estas pruebas verifican que el agente BiohackingInnovator utiliza correctamente
el servicio de clasificación de programas para personalizar sus recomendaciones
de biohacking según el tipo de programa del usuario.
"""
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest

# Añadir el directorio raíz al path para importar los módulos del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.biohacking_innovator.agent import BiohackingInnovator, BiohackingProtocolInput
from services.program_classification_service import ProgramClassificationService


class TestBiohackingInnovator(unittest.TestCase):
    """Pruebas unitarias para el agente BiohackingInnovator."""

    def setUp(self):
        """Configuración inicial para las pruebas."""
        # Crear mocks para los clientes y servicios
        self.mock_gemini_client = MagicMock()
        self.mock_gemini_client.generate_response = AsyncMock(
            return_value="Respuesta de prueba para protocolo de biohacking"
        )
        self.mock_gemini_client.generate_structured_output = AsyncMock(
            return_value={
                "objective": "Optimizar rendimiento y recuperación",
                "duration": "4-8 semanas",
                "program_type": "PRIME",
                "interventions": {
                    "diet": "Dieta alta en proteínas y baja en carbohidratos procesados",
                    "supplements": "Creatina, Omega-3, Vitamina D",
                    "exercise": "Entrenamiento de alta intensidad 4 veces por semana",
                    "sleep": "8 horas de sueño con optimización de ciclos"
                },
                "schedule": {
                    "daily": "Exposición a luz natural por la mañana, ejercicio antes del mediodía",
                    "weekly": "Entrenamiento de fuerza lunes/miércoles/viernes, recuperación activa martes/jueves"
                },
                "metrics": [
                    "Variabilidad de la frecuencia cardíaca (HRV)",
                    "Tiempo de recuperación",
                    "Rendimiento en entrenamientos"
                ],
                "precautions": "Consultar con un profesional de la salud antes de iniciar el protocolo"
            }
        )
        
        # Mock para el servicio de clasificación de programas
        self.mock_program_classification_service = MagicMock()
        self.mock_program_classification_service.classify_program_type = AsyncMock(return_value="PRIME")
        
        # Crear el agente con mocks
        with patch('agents.biohacking_innovator.agent.GeminiClient', return_value=self.mock_gemini_client), \
             patch('agents.biohacking_innovator.agent.ProgramClassificationService', return_value=self.mock_program_classification_service), \
             patch('agents.biohacking_innovator.agent.SupabaseClient'), \
             patch('agents.biohacking_innovator.agent.state_manager_adapter'), \
             patch('agents.biohacking_innovator.agent.intent_analyzer_adapter'):
            self.agent = BiohackingInnovator()
            # Mock para el método _classify_query
            self.agent._classify_query = AsyncMock(return_value="biohacking")

    @pytest.mark.asyncio
    async def test_run_async_impl_uses_program_classification(self):
        """Prueba que _run_async_impl utiliza el servicio de clasificación de programas."""
        # Ejecutar el método
        result = await self.agent._run_async_impl(
            "Necesito un protocolo de biohacking para mejorar mi rendimiento",
            user_id="test_user"
        )
        
        # Verificar que se llamó al servicio de clasificación de programas
        self.mock_program_classification_service.classify_program_type.assert_called_once()
        
        # Verificar que el resultado incluye el tipo de programa en los metadatos
        self.assertEqual(result["metadata"]["program_type"], "PRIME")
        
        # Verificar que se utilizó la capacidad de biohacking
        self.assertIn("biohacking", result["capabilities_used"])

    @pytest.mark.asyncio
    async def test_biohacking_protocol_skill_uses_program_context(self):
        """Prueba que la skill de protocolo de biohacking utiliza el contexto del programa."""
        # Configurar el agente con un tipo de programa
        self.agent.program_type = "PRIME"
        
        # Crear una instancia de la skill desde el agente
        biohacking_skill = next((skill for skill in self.agent.skills if skill.name == "biohacking_protocol"), None)
        
        # Verificar que la skill existe
        self.assertIsNotNone(biohacking_skill)
        
        # Ejecutar la skill
        input_data = BiohackingProtocolInput(
            query="Necesito un protocolo de biohacking para mejorar mi rendimiento",
            age=35,
            gender="masculino",
            goals=["Mejorar rendimiento", "Optimizar recuperación"]
        )
        result = await biohacking_skill.handler(input_data)
        
        # Verificar que la respuesta se generó correctamente
        self.assertIsNotNone(result.response)
        self.assertIsNotNone(result.protocol)
        
        # Verificar que el protocolo incluye el tipo de programa
        self.assertEqual(result.protocol.get("program_type"), "PRIME")
        
        # Verificar que el prompt enviado a Gemini incluye contexto específico del programa
        prompt_calls = [call[0][0] for call in self.mock_gemini_client.generate_response.call_args_list]
        self.assertTrue(any("PRIME" in prompt for prompt in prompt_calls))
        
        # Verificar que el prompt para generar el protocolo JSON incluye el tipo de programa
        json_prompt_calls = [call[0][0] for call in self.mock_gemini_client.generate_structured_output.call_args_list]
        self.assertTrue(any("PRIME" in prompt for prompt in json_prompt_calls))

    @pytest.mark.asyncio
    async def test_run_async_impl_with_classification_error(self):
        """Prueba que _run_async_impl maneja correctamente errores en la clasificación de programas."""
        # Configurar el mock para lanzar una excepción
        self.mock_program_classification_service.classify_program_type.side_effect = Exception("Error de clasificación")
        
        # Ejecutar el método
        result = await self.agent._run_async_impl(
            "Necesito un protocolo de biohacking para mejorar mi rendimiento",
            user_id="test_user"
        )
        
        # Verificar que el resultado incluye "GENERAL" como tipo de programa por defecto
        self.assertEqual(result["metadata"]["program_type"], "GENERAL")
        
        # Verificar que se utilizó la capacidad de biohacking a pesar del error
        self.assertIn("biohacking", result["capabilities_used"])


if __name__ == "__main__":
    unittest.main()
