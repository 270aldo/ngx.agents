"""
Pruebas unitarias para el agente RecoveryCorrective.

Verifica la integración con el servicio de clasificación de programas.
"""

import unittest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

from agents.recovery_corrective.agent import RecoveryCorrective
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition


class TestRecoveryCorrective(unittest.TestCase):
    """Pruebas para el agente RecoveryCorrective."""

    def setUp(self):
        """Configuración inicial para las pruebas."""
        # Crear mocks para las dependencias
        self.gemini_client_mock = AsyncMock()
        self.gemini_client_mock.generate_text = AsyncMock()
        self.gemini_client_mock.generate_response = AsyncMock()
        self.gemini_client_mock.generate_structured_output = AsyncMock()
        
        # Configurar respuestas predeterminadas para los mocks
        self.gemini_client_mock.generate_response.return_value = "Respuesta de prueba"
        self.gemini_client_mock.generate_structured_output.return_value = {"test": "data"}

        # Crear mock para el servicio de clasificación de programas
        self.program_classification_service_mock = AsyncMock()
        self.program_classification_service_mock.classify_program_type = AsyncMock()
        self.program_classification_service_mock.classify_program_type.return_value = "PRIME"
        
        # Crear instancia del agente con mocks
        with patch('agents.recovery_corrective.agent.GeminiClient', return_value=self.gemini_client_mock):
            with patch('agents.recovery_corrective.agent.ProgramClassificationService', return_value=self.program_classification_service_mock):
                self.agent = RecoveryCorrective()
                self.agent.gemini_client = self.gemini_client_mock
                self.agent.program_classification_service = self.program_classification_service_mock

    def test_init(self):
        """Verifica que el agente se inicializa correctamente con el servicio de clasificación de programas."""
        self.assertIsNotNone(self.agent.program_classification_service)
        self.assertEqual(self.agent.program_classification_service, self.program_classification_service_mock)

    def test_injury_prevention_skill_uses_program_classification(self):
        """Verifica que la skill de prevención de lesiones utiliza el servicio de clasificación de programas."""
        # Obtener la skill de prevención de lesiones
        injury_prevention_skill = None
        for skill in self.agent.toolkit.skills:
            if skill.name == "injury_prevention":
                injury_prevention_skill = skill
                break
        
        self.assertIsNotNone(injury_prevention_skill, "No se encontró la skill de prevención de lesiones")
        
        # Crear datos de entrada para la skill
        from agents.recovery_corrective.agent import InjuryPreventionInput
        
        input_data = InjuryPreventionInput(
            query="¿Cómo puedo prevenir lesiones al correr?",
            activity_type="Running",
            user_profile={
                "age": 35,
                "gender": "Masculino",
                "goals": ["Mejorar rendimiento", "Prevenir lesiones"]
            }
        )
        
        # Ejecutar la skill
        asyncio.run(injury_prevention_skill.handler(input_data))
        
        # Verificar que se llamó al servicio de clasificación de programas
        self.program_classification_service_mock.classify_program_type.assert_called_once()
        
        # Verificar que se utilizó el tipo de programa en el prompt
        call_args = self.gemini_client_mock.generate_response.call_args[0][0]
        self.assertIn("PRIME", call_args)

    def test_rehabilitation_skill_uses_program_classification(self):
        """Verifica que la skill de rehabilitación utiliza el servicio de clasificación de programas."""
        # Obtener la skill de rehabilitación
        rehabilitation_skill = None
        for skill in self.agent.toolkit.skills:
            if skill.name == "rehabilitation":
                rehabilitation_skill = skill
                break
        
        self.assertIsNotNone(rehabilitation_skill, "No se encontró la skill de rehabilitación")
        
        # Crear datos de entrada para la skill
        from agents.recovery_corrective.agent import RehabilitationInput
        
        input_data = RehabilitationInput(
            query="Tengo una lesión en el hombro, ¿cómo puedo rehabilitarlo?",
            injury_type="Hombro",
            injury_phase="Subaguda",
            user_profile={
                "age": 35,
                "gender": "Masculino",
                "goals": ["Recuperación", "Volver a entrenar"]
            }
        )
        
        # Ejecutar la skill
        asyncio.run(rehabilitation_skill.handler(input_data))
        
        # Verificar que se llamó al servicio de clasificación de programas
        self.program_classification_service_mock.classify_program_type.assert_called_once()
        
        # Verificar que se utilizó el tipo de programa en el prompt
        call_args = self.gemini_client_mock.generate_response.call_args[0][0]
        self.assertIn("PRIME", call_args)

    def test_sleep_optimization_skill_uses_program_classification(self):
        """Verifica que la skill de optimización del sueño utiliza el servicio de clasificación de programas."""
        # Obtener la skill de optimización del sueño
        sleep_optimization_skill = None
        for skill in self.agent.toolkit.skills:
            if skill.name == "sleep_optimization":
                sleep_optimization_skill = skill
                break
        
        self.assertIsNotNone(sleep_optimization_skill, "No se encontró la skill de optimización del sueño")
        
        # Crear datos de entrada para la skill
        from agents.recovery_corrective.agent import SleepOptimizationInput
        
        input_data = SleepOptimizationInput(
            query="¿Cómo puedo mejorar mi calidad de sueño?",
            sleep_issues=["Dificultad para conciliar el sueño", "Despertares nocturnos"],
            user_profile={
                "age": 35,
                "gender": "Masculino",
                "goals": ["Mejorar recuperación", "Optimizar rendimiento"]
            }
        )
        
        # Ejecutar la skill
        asyncio.run(sleep_optimization_skill.handler(input_data))
        
        # Verificar que se llamó al servicio de clasificación de programas
        self.program_classification_service_mock.classify_program_type.assert_called_once()
        
        # Verificar que se utilizó el tipo de programa en el prompt
        call_args = self.gemini_client_mock.generate_response.call_args[0][0]
        self.assertIn("PRIME", call_args)


if __name__ == "__main__":
    unittest.main()
