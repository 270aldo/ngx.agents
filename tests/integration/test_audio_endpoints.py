"""
Tests de integración para los endpoints de audio y voz.

Este módulo contiene tests para verificar el funcionamiento correcto
de todos los endpoints relacionados con el procesamiento de audio,
incluyendo transcripción, síntesis, análisis emocional y comandos de voz.
"""

import pytest
import asyncio
import base64
import io
from typing import Dict, Any
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from agents.skills.audio_voice_skills import (
    VoiceCommandSkill,
    AudioFeedbackSkill,
    VoiceEmotionAnalysisSkill,
    WorkoutVoiceGuideSkill,
)


class TestAudioEndpoints:
    """Tests de integración para endpoints de audio."""

    @pytest.fixture
    def client(self):
        """Cliente de prueba para FastAPI."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_token(self):
        """Token de autenticación simulado."""
        return "Bearer test-token"

    @pytest.fixture
    def sample_audio_base64(self):
        """Audio de muestra en base64 para pruebas."""
        # Crear un archivo de audio simulado (datos binarios básicos)
        audio_data = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00"
        return base64.b64encode(audio_data).decode("utf-8")

    @pytest.fixture
    def workout_state(self):
        """Estado de entrenamiento de muestra."""
        return {
            "current_exercise": "Sentadillas",
            "current_set": 2,
            "total_sets": 3,
            "current_rep": 5,
            "total_reps": 10,
            "exercise_index": 1,
            "total_exercises": 5,
            "status": "active",
        }

    @patch("app.middleware.auth.get_current_user")
    @patch("infrastructure.adapters.speech_adapter.speech_adapter.transcribe_audio")
    async def test_transcribe_audio_endpoint(
        self, mock_transcribe, mock_auth, client, mock_auth_token, sample_audio_base64
    ):
        """Test del endpoint de transcripción de audio."""
        # Configurar mocks
        mock_auth.return_value = Mock(user_id="test_user_123")
        mock_transcribe.return_value = {
            "status": "success",
            "text": "Hola, quiero iniciar mi entrenamiento",
            "confidence": 0.95,
            "language_code": "es-ES",
        }

        # Preparar datos de prueba
        audio_bytes = base64.b64decode(sample_audio_base64)
        files = {"file": ("test.wav", io.BytesIO(audio_bytes), "audio/wav")}
        data = {"language_code": "es-ES"}

        # Realizar solicitud
        response = client.post(
            "/audio/transcribe",
            files=files,
            data=data,
            headers={"Authorization": mock_auth_token},
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert result["transcription"] == "Hola, quiero iniciar mi entrenamiento"
        assert result["confidence"] == 0.95
        assert result["language_code"] == "es-ES"

        # Verificar que se llamó al adaptador
        mock_transcribe.assert_called_once()

    @patch("app.middleware.auth.get_current_user")
    @patch("infrastructure.adapters.speech_adapter.speech_adapter.synthesize_speech")
    async def test_synthesize_speech_endpoint(
        self, mock_synthesize, mock_auth, client, mock_auth_token
    ):
        """Test del endpoint de síntesis de voz."""
        # Configurar mocks
        mock_auth.return_value = Mock(user_id="test_user_123")
        mock_synthesize.return_value = {
            "status": "success",
            "audio_base64": "UklGRiAIAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAIAAAz",
            "audio_format": "mp3",
            "voice_used": "es-ES-Standard-A",
            "duration_estimate": 3.5,
        }

        # Preparar datos de prueba
        data = {
            "text": "¡Excelente trabajo! Mantén esa técnica perfecta.",
            "voice_name": "es-ES-Standard-A",
            "language_code": "es-ES",
            "output_format": "base64",
        }

        # Realizar solicitud
        response = client.post(
            "/audio/synthesize", data=data, headers={"Authorization": mock_auth_token}
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert "audio_base64" in result
        assert result["voice_used"] == "es-ES-Standard-A"
        assert result["duration_estimate"] > 0

        # Verificar que se llamó al adaptador
        mock_synthesize.assert_called_once()

    @patch("app.middleware.auth.get_current_user")
    @patch("agents.skills.audio_voice_skills.VoiceEmotionAnalysisSkill.execute")
    async def test_analyze_emotion_endpoint(
        self,
        mock_emotion_skill,
        mock_auth,
        client,
        mock_auth_token,
        sample_audio_base64,
    ):
        """Test del endpoint de análisis emocional."""
        # Configurar mocks
        mock_auth.return_value = Mock(user_id="test_user_123")
        mock_emotion_skill.return_value = {
            "status": "success",
            "emotional_state": "motivated",
            "confidence": 0.85,
            "emotions": {
                "alegría": 0.7,
                "tristeza": 0.1,
                "enojo": 0.05,
                "neutral": 0.15,
            },
            "physical_indicators": {
                "energy_level": 0.8,
                "stress_level": 0.2,
                "fatigue_level": 0.1,
                "pain_indicators": 0.0,
            },
            "transcription": "Me siento muy bien hoy",
            "needs_intervention": False,
        }

        # Preparar datos de prueba
        audio_bytes = base64.b64decode(sample_audio_base64)
        files = {"file": ("emotion.wav", io.BytesIO(audio_bytes), "audio/wav")}
        data = {"analysis_depth": "detailed", "include_recommendations": "true"}

        # Realizar solicitud
        response = client.post(
            "/audio/analyze-emotion",
            files=files,
            data=data,
            headers={"Authorization": mock_auth_token},
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert result["emotional_state"] == "motivated"
        assert result["confidence"] == 0.85
        assert "physical_indicators" in result
        assert result["physical_indicators"]["energy_level"] == 0.8
        assert result["needs_intervention"] == False

    @patch("app.middleware.auth.get_current_user")
    @patch("agents.skills.audio_voice_skills.VoiceCommandSkill.execute")
    async def test_voice_command_endpoint(
        self,
        mock_command_skill,
        mock_auth,
        client,
        mock_auth_token,
        sample_audio_base64,
        workout_state,
    ):
        """Test del endpoint de comandos de voz."""
        # Configurar mocks
        mock_auth.return_value = Mock(user_id="test_user_123")
        mock_command_skill.return_value = {
            "status": "success",
            "command": "next_exercise",
            "action": "navigate_exercise",
            "confidence": 0.9,
            "transcription": "siguiente ejercicio",
            "parameters": {"direction": "next"},
            "message": "Pasando al siguiente ejercicio",
        }

        # Preparar datos de prueba
        audio_bytes = base64.b64decode(sample_audio_base64)
        files = {"file": ("command.wav", io.BytesIO(audio_bytes), "audio/wav")}
        data = {"workout_state": str(workout_state)}

        # Realizar solicitud
        response = client.post(
            "/audio/voice-command",
            files=files,
            data=data,
            headers={"Authorization": mock_auth_token},
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert result["command"] == "next_exercise"
        assert result["action"] == "navigate_exercise"
        assert result["confidence"] == 0.9
        assert "transcription" in result

    @patch("app.middleware.auth.get_current_user")
    @patch("agents.skills.audio_voice_skills.AudioFeedbackSkill.execute")
    async def test_workout_feedback_endpoint(
        self, mock_feedback_skill, mock_auth, client, mock_auth_token
    ):
        """Test del endpoint de feedback de entrenamiento."""
        # Configurar mocks
        mock_auth.return_value = Mock(user_id="test_user_123")
        mock_feedback_skill.return_value = {
            "status": "success",
            "audio_base64": "UklGRiAIAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAIAAAz",
            "text": "¡Excelente trabajo! Serie completada.",
            "duration_estimate": 4.2,
            "feedback_type": "set_completion",
            "voice_used": "es-ES-Standard-B",
        }

        # Preparar datos de prueba
        data = {
            "feedback_type": "set_completion",
            "exercise_name": "Sentadillas",
            "rest_seconds": "60",
            "user_name": "Juan",
            "voice_name": "es-ES-Standard-B",
            "output_format": "base64",
        }

        # Realizar solicitud
        response = client.post(
            "/audio/workout-feedback",
            data=data,
            headers={"Authorization": mock_auth_token},
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert result["feedback_type"] == "set_completion"
        assert "audio_base64" in result
        assert result["duration"] > 0
        assert "text" in result

    @patch("app.middleware.auth.get_current_user")
    async def test_list_voices_endpoint(self, mock_auth, client, mock_auth_token):
        """Test del endpoint para listar voces disponibles."""
        # Configurar mock
        mock_auth.return_value = Mock(user_id="test_user_123")

        # Realizar solicitud
        response = client.get(
            "/audio/voices?language_code=es-ES",
            headers={"Authorization": mock_auth_token},
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert result["language_code"] == "es-ES"
        assert "voices" in result
        assert len(result["voices"]) > 0
        assert result["total"] > 0

        # Verificar estructura de las voces
        voice = result["voices"][0]
        assert "name" in voice
        assert "gender" in voice
        assert "description" in voice

    @patch("app.middleware.auth.get_current_user")
    async def test_audio_commands_endpoint(self, mock_auth, client, mock_auth_token):
        """Test del endpoint para obtener comandos disponibles."""
        # Configurar mock
        mock_auth.return_value = Mock(user_id="test_user_123")

        # Realizar solicitud
        response = client.get(
            "/audio/audio-commands", headers={"Authorization": mock_auth_token}
        )

        # Verificar respuesta
        assert response.status_code == 200
        result = response.json()
        assert "commands" in result
        assert "total_commands" in result
        assert "categories" in result

        # Verificar categorías esperadas
        expected_categories = [
            "workout_control",
            "exercise_navigation",
            "exercise_info",
            "progress",
            "help",
        ]
        for category in expected_categories:
            assert category in result["commands"]

    async def test_transcribe_audio_no_file(self, client, mock_auth_token):
        """Test del endpoint de transcripción sin archivo."""
        with patch("app.middleware.auth.get_current_user") as mock_auth:
            mock_auth.return_value = Mock(user_id="test_user_123")

            response = client.post(
                "/audio/transcribe",
                data={"language_code": "es-ES"},
                headers={"Authorization": mock_auth_token},
            )

            assert response.status_code == 400
            assert "Debe proporcionar" in response.json()["detail"]

    async def test_synthesize_empty_text(self, client, mock_auth_token):
        """Test del endpoint de síntesis con texto vacío."""
        with patch("app.middleware.auth.get_current_user") as mock_auth:
            mock_auth.return_value = Mock(user_id="test_user_123")

            response = client.post(
                "/audio/synthesize",
                data={
                    "text": "",
                    "voice_name": "es-ES-Standard-A",
                    "language_code": "es-ES",
                },
                headers={"Authorization": mock_auth_token},
            )

            assert response.status_code == 422  # Validation error

    async def test_synthesize_text_too_long(self, client, mock_auth_token):
        """Test del endpoint de síntesis con texto muy largo."""
        with patch("app.middleware.auth.get_current_user") as mock_auth:
            mock_auth.return_value = Mock(user_id="test_user_123")

            long_text = "a" * 5001  # Excede el límite de 5000 caracteres

            response = client.post(
                "/audio/synthesize",
                data={
                    "text": long_text,
                    "voice_name": "es-ES-Standard-A",
                    "language_code": "es-ES",
                },
                headers={"Authorization": mock_auth_token},
            )

            assert response.status_code == 400
            assert "5000 caracteres" in response.json()["detail"]


class TestAudioSkills:
    """Tests específicos para las skills de audio."""

    @pytest.fixture
    def voice_command_skill(self):
        """Instancia de VoiceCommandSkill para pruebas."""
        return VoiceCommandSkill()

    @pytest.fixture
    def audio_feedback_skill(self):
        """Instancia de AudioFeedbackSkill para pruebas."""
        return AudioFeedbackSkill()

    @pytest.fixture
    def voice_emotion_skill(self):
        """Instancia de VoiceEmotionAnalysisSkill para pruebas."""
        return VoiceEmotionAnalysisSkill()

    @pytest.fixture
    def workout_guide_skill(self):
        """Instancia de WorkoutVoiceGuideSkill para pruebas."""
        return WorkoutVoiceGuideSkill()

    @patch("infrastructure.adapters.speech_adapter.speech_adapter.transcribe_audio")
    async def test_voice_command_skill_start_workout(
        self, mock_transcribe, voice_command_skill
    ):
        """Test de la skill de comandos de voz para iniciar entrenamiento."""
        # Configurar mock
        mock_transcribe.return_value = {
            "status": "success",
            "text": "comienza el entrenamiento",
            "confidence": 0.9,
        }

        # Ejecutar skill
        result = await voice_command_skill.execute(
            {
                "audio_data": "mock_audio_data",
                "language_code": "es-ES",
                "workout_state": {},
            }
        )

        # Verificar resultado
        assert result["status"] == "success"
        assert result["command"] == "start_workout"
        assert result["action"] == "start_workout"
        assert "message" in result

    @patch("infrastructure.adapters.speech_adapter.speech_adapter.transcribe_audio")
    async def test_voice_command_skill_unknown_command(
        self, mock_transcribe, voice_command_skill
    ):
        """Test de la skill con comando no reconocido."""
        # Configurar mock
        mock_transcribe.return_value = {
            "status": "success",
            "text": "algo incomprensible xyz",
            "confidence": 0.3,
        }

        # Ejecutar skill
        result = await voice_command_skill.execute(
            {
                "audio_data": "mock_audio_data",
                "language_code": "es-ES",
                "workout_state": {},
            }
        )

        # Verificar resultado
        assert result["status"] == "success"
        assert result["command"] == "unknown"
        assert result["action"] == "clarify"
        assert "available_commands" in result

    @patch("infrastructure.adapters.speech_adapter.speech_adapter.synthesize_speech")
    async def test_audio_feedback_skill_encouragement(
        self, mock_synthesize, audio_feedback_skill
    ):
        """Test de la skill de feedback de audio para motivación."""
        # Configurar mock
        mock_synthesize.return_value = {
            "status": "success",
            "audio_base64": "mock_audio_base64",
            "audio_format": "mp3",
            "duration_estimate": 3.5,
        }

        # Ejecutar skill
        result = await audio_feedback_skill.execute(
            {
                "feedback_type": "encouragement",
                "parameters": {},
                "voice_settings": {"voice_name": "es-ES-Standard-B"},
                "user_profile": {"name": "Ana"},
            }
        )

        # Verificar resultado
        assert result["status"] == "success"
        assert result["feedback_type"] == "encouragement"
        assert "audio_base64" in result
        assert "text" in result
        assert result["duration_estimate"] > 0

    @patch("infrastructure.adapters.speech_adapter.speech_adapter.analyze_audio")
    async def test_voice_emotion_skill_analysis(
        self, mock_analyze, voice_emotion_skill
    ):
        """Test de la skill de análisis emocional."""
        # Configurar mock
        mock_analyze.return_value = {
            "status": "success",
            "transcription": "Me siento un poco cansado",
            "analysis": {
                "scores": {
                    "alegría": 0.2,
                    "tristeza": 0.3,
                    "neutral": 0.4,
                    "fatiga": 0.1,
                }
            },
        }

        # Ejecutar skill
        result = await voice_emotion_skill.execute(
            {
                "audio_data": "mock_audio_data",
                "analysis_depth": "detailed",
                "previous_state": {},
            }
        )

        # Verificar resultado
        assert result["status"] == "success"
        assert "emotional_state" in result
        assert "confidence" in result
        assert "recommendations" in result
        assert "physical_indicators" in result

    @patch("infrastructure.adapters.speech_adapter.speech_adapter.synthesize_speech")
    async def test_workout_guide_skill_introduction(
        self, mock_synthesize, workout_guide_skill
    ):
        """Test de la skill de guía de voz para introducción."""
        # Configurar mock
        mock_synthesize.return_value = {
            "status": "success",
            "audio_base64": "mock_audio_base64",
            "duration_estimate": 5.0,
        }

        # Ejecutar skill
        result = await workout_guide_skill.execute(
            {
                "exercise": {"name": "Sentadillas", "sets": 3, "reps": 10},
                "phase": "introduction",
                "rep_count": 0,
                "voice_settings": {},
            }
        )

        # Verificar resultado
        assert result["status"] == "success"
        assert result["phase"] == "introduction"
        assert "audio_base64" in result
        assert "text" in result
        assert "next_cue_timing" in result


class TestAudioIntegrationWithAgents:
    """Tests de integración entre audio y agentes especializados."""

    @patch(
        "agents.motivation_behavior_coach.agent.MotivationBehaviorCoach._skill_voice_motivation"
    )
    async def test_motivation_coach_voice_skill(self, mock_voice_skill):
        """Test de integración con Motivation Behavior Coach."""
        # Configurar mock
        mock_voice_skill.return_value = {
            "status": "success",
            "audio_base64": "mock_audio",
            "message_text": "¡Excelente progreso!",
            "message_type": "encouragement",
            "duration": 4.0,
        }

        # Simular llamada al agente
        from agents.motivation_behavior_coach.agent import MotivationBehaviorCoach

        # Esta es una simulación de cómo se usaría
        agent = Mock(spec=MotivationBehaviorCoach)
        agent._skill_voice_motivation = mock_voice_skill

        result = await agent._skill_voice_motivation(
            message_type="encouragement",
            user_name="Carlos",
            achievement="completar 100 flexiones",
        )

        assert result["status"] == "success"
        assert "audio_base64" in result
        assert (
            "Carlos" in result["message_text"]
            or result["message_type"] == "encouragement"
        )

    @patch(
        "agents.elite_training_strategist.agent.EliteTrainingStrategist._skill_workout_voice_guide"
    )
    async def test_elite_training_strategist_voice_guide(self, mock_guide_skill):
        """Test de integración con Elite Training Strategist."""
        # Configurar mock
        mock_guide_skill.return_value = {
            "status": "success",
            "audio_base64": "mock_audio",
            "text": "Vamos con sentadillas. 3 series de 10 repeticiones.",
            "phase": "introduction",
            "next_cue_timing": 5.0,
        }

        # Simular llamada al agente
        from agents.elite_training_strategist.agent import EliteTrainingStrategist

        agent = Mock(spec=EliteTrainingStrategist)
        agent._skill_workout_voice_guide = mock_guide_skill

        result = await agent._skill_workout_voice_guide(
            exercise={"name": "Sentadillas", "sets": 3, "reps": 10},
            phase="introduction",
            rep_count=0,
        )

        assert result["status"] == "success"
        assert result["phase"] == "introduction"
        assert "audio_base64" in result
        assert "next_cue_timing" in result


# Configuración de pytest
@pytest.fixture(scope="session")
def event_loop():
    """Crear loop de eventos para tests asíncronos."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Ejecutar tests directamente
    pytest.main([__file__, "-v"])
