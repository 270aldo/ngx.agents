"""
Pruebas unitarias para el agente ProgressTracker.

Estas pruebas verifican que el agente ProgressTracker utiliza correctamente
el servicio de clasificación de programas para personalizar sus análisis,
visualizaciones y comparaciones según el tipo de programa del usuario.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import matplotlib.pyplot as plt

# Añadir el directorio raíz al path para importar los módulos del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.progress_tracker.agent import ProgressTracker
from agents.progress_tracker.schemas import (
    AnalyzeProgressInput,
    VisualizeProgressInput,
    CompareProgressInput,
)


class TestProgressTracker(unittest.TestCase):
    """Pruebas unitarias para el agente ProgressTracker."""

    def setUp(self):
        """Configuración inicial para las pruebas."""
        # Crear mocks para los clientes y servicios
        self.mock_gemini_client = MagicMock()
        self.mock_gemini_client.generate_structured_output = AsyncMock(
            return_value={
                "analysis": "Análisis de prueba",
                "trends": ["tendencia1", "tendencia2"],
            }
        )

        # Mock para el servicio de clasificación de programas
        self.mock_program_classification_service = MagicMock()
        self.mock_program_classification_service.classify_program_type = AsyncMock(
            return_value="PRIME"
        )

        # Crear el agente con mocks
        with (
            patch(
                "agents.progress_tracker.agent.GeminiClient",
                return_value=self.mock_gemini_client,
            ),
            patch(
                "agents.progress_tracker.agent.ProgramClassificationService",
                return_value=self.mock_program_classification_service,
            ),
            patch("agents.progress_tracker.agent.SupabaseClient"),
            patch("os.makedirs"),
        ):
            self.agent = ProgressTracker()
            # Reemplazar el método _get_user_data con un mock
            self.agent._get_user_data = AsyncMock(
                return_value={
                    "weight": [
                        {"date": "2023-01-01", "value": 80.5},
                        {"date": "2023-01-08", "value": 79.8},
                        {"date": "2023-01-15", "value": 79.2},
                    ],
                    "performance": [
                        {"date": "2023-01-01", "value": 65.0},
                        {"date": "2023-01-08", "value": 68.5},
                        {"date": "2023-01-15", "value": 72.0},
                    ],
                }
            )

            # Parchear plt.savefig para evitar guardar archivos durante las pruebas
            plt.savefig = MagicMock()
            plt.close = MagicMock()

    @pytest.mark.asyncio
    async def test_analyze_progress_with_program_classification(self):
        """Prueba que _skill_analyze_progress utiliza el servicio de clasificación de programas."""
        # Preparar datos de entrada
        input_data = AnalyzeProgressInput(
            user_id="test_user",
            time_period="last_month",
            metrics=["weight", "performance"],
            user_profile={
                "name": "Usuario de prueba",
                "goals": ["Mejorar rendimiento", "Aumentar fuerza"],
                "training_history": "Entrenamiento de alta intensidad",
            },
        )

        # Ejecutar la skill
        result = await self.agent._skill_analyze_progress(input_data)

        # Verificar que se llamó al servicio de clasificación de programas
        self.mock_program_classification_service.classify_program_type.assert_called_once()

        # Verificar que el resultado incluye el tipo de programa
        self.assertEqual(result.result.get("program_type"), "PRIME")

        # Verificar que el prompt enviado a Gemini incluye contexto específico del programa
        prompt_calls = [
            call[0][0]
            for call in self.mock_gemini_client.generate_structured_output.call_args_list
        ]
        self.assertTrue(any("PRIME" in prompt for prompt in prompt_calls))

    @pytest.mark.asyncio
    async def test_visualize_progress_with_program_classification(self):
        """Prueba que _skill_visualize_progress utiliza el servicio de clasificación de programas."""
        # Preparar datos de entrada
        input_data = VisualizeProgressInput(
            user_id="test_user",
            metric="weight",
            time_period="last_month",
            chart_type="line",
            user_profile={
                "name": "Usuario de prueba",
                "goals": ["Mejorar rendimiento", "Aumentar fuerza"],
                "training_history": "Entrenamiento de alta intensidad",
            },
        )

        # Ejecutar la skill
        result = await self.agent._skill_visualize_progress(input_data)

        # Verificar que se llamó al servicio de clasificación de programas
        self.mock_program_classification_service.classify_program_type.assert_called_once()

        # Verificar que el resultado tiene status de éxito
        self.assertEqual(result.status, "success")

        # Verificar que se generó una visualización
        self.assertTrue(result.visualization_url.startswith("file://"))

    @pytest.mark.asyncio
    async def test_compare_progress_with_program_classification(self):
        """Prueba que _skill_compare_progress utiliza el servicio de clasificación de programas."""
        # Preparar datos de entrada
        input_data = CompareProgressInput(
            user_id="test_user",
            period1="last_month",
            period2="current_month",
            metrics=["weight", "performance"],
            user_profile={
                "name": "Usuario de prueba",
                "goals": ["Mejorar rendimiento", "Aumentar fuerza"],
                "training_history": "Entrenamiento de alta intensidad",
            },
        )

        # Ejecutar la skill
        result = await self.agent._skill_compare_progress(input_data)

        # Verificar que se llamó al servicio de clasificación de programas
        self.mock_program_classification_service.classify_program_type.assert_called_once()

        # Verificar que el resultado incluye el tipo de programa
        self.assertEqual(result.result.get("program_type"), "PRIME")

        # Verificar que el prompt enviado a Gemini incluye contexto específico del programa
        prompt_calls = [
            call[0][0]
            for call in self.mock_gemini_client.generate_structured_output.call_args_list
        ]
        self.assertTrue(any("PRIME" in prompt for prompt in prompt_calls))

    @pytest.mark.asyncio
    async def test_analyze_progress_with_classification_error(self):
        """Prueba que _skill_analyze_progress maneja correctamente errores en la clasificación de programas."""
        # Configurar el mock para lanzar una excepción
        self.mock_program_classification_service.classify_program_type.side_effect = (
            Exception("Error de clasificación")
        )

        # Preparar datos de entrada
        input_data = AnalyzeProgressInput(
            user_id="test_user",
            time_period="last_month",
            metrics=["weight", "performance"],
            user_profile={},
        )

        # Ejecutar la skill
        result = await self.agent._skill_analyze_progress(input_data)

        # Verificar que el resultado usa "GENERAL" como tipo de programa por defecto
        self.assertEqual(result.result.get("program_type"), "GENERAL")

        # Verificar que el resultado tiene status de éxito a pesar del error
        self.assertEqual(result.status, "success")


if __name__ == "__main__":
    unittest.main()
