"""
Pruebas para el adaptador de voz.

Este módulo contiene pruebas unitarias para el adaptador de voz.
"""

import asyncio
import os
import pytest
from unittest.mock import MagicMock, patch

from infrastructure.adapters.voice_adapter import VoiceAdapter
from core.voice_processor import VoiceProcessor

# Datos de prueba
TEST_AUDIO = b'\x00\x00' * 1000  # Audio de prueba (silencio)
TEST_TEXT = "Texto de prueba para síntesis de voz"

@pytest.fixture
def mock_voice_processor():
    """Fixture para crear un procesador de voz mock."""
    processor = MagicMock(spec=VoiceProcessor)
    
    # Configurar speech_to_text
    processor.speech_to_text.return_value = {
        "text": "Texto transcrito de prueba",
        "confidence": 0.95,
        "language_code": "es-ES",
        "transcription_details": {
            "results": [
                {
                    "alternatives": [
                        {
                            "transcript": "Texto transcrito de prueba",
                            "confidence": 0.95
                        }
                    ]
                }
            ]
        },
        "emotion": {
            "emotions": {
                "happy": 0.1,
                "sad": 0.1,
                "angry": 0.1,
                "surprised": 0.1,
                "fearful": 0.1,
                "neutral": 0.5
            },
            "dominant_emotion": "neutral",
            "confidence": 0.5
        }
    }
    
    # Configurar text_to_speech
    processor.text_to_speech.return_value = (
        b'\x00\x00' * 1000,  # Audio sintético
        {
            "duration_seconds": 2.0,
            "sample_rate": 24000,
            "channels": 1,
            "encoding": "LINEAR16"
        }
    )
    
    # Configurar analyze_voice_emotion
    processor.analyze_voice_emotion.return_value = {
        "emotions": {
            "happy": 0.1,
            "sad": 0.1,
            "angry": 0.1,
            "surprised": 0.1,
            "fearful": 0.1,
            "neutral": 0.5
        },
        "dominant_emotion": "neutral",
        "confidence": 0.5,
        "analysis": "El hablante muestra principalmente un tono neutral."
    }
    
    # Configurar get_available_voices
    processor.get_available_voices.return_value = [
        {"name": "es-ES-Standard-A", "gender": "FEMALE", "language_codes": ["es-ES"]},
        {"name": "es-ES-Standard-B", "gender": "MALE", "language_codes": ["es-ES"]}
    ]
    
    # Configurar get_stats
    processor.get_stats.return_value = {
        "speech_to_text_operations": 1,
        "text_to_speech_operations": 1,
        "emotion_analysis_operations": 1,
        "errors": 0,
        "avg_stt_latency_ms": 100.0,
        "avg_tts_latency_ms": 150.0,
        "avg_emotion_latency_ms": 200.0,
        "default_language": "es-ES",
        "default_voice": "es-ES-Standard-A",
        "analyze_emotions": True,
        "min_confidence_threshold": 0.6,
        "stt_stats": {"mock_mode": True},
        "tts_stats": {"mock_mode": True},
        "emotion_stats": {"mock_mode": True}
    }
    
    return processor

@pytest.fixture
def voice_adapter(mock_voice_processor):
    """Fixture para crear un adaptador de voz con procesador mock."""
    adapter = VoiceAdapter()
    adapter.voice_processor = mock_voice_processor
    adapter._initialized = True
    return adapter

@pytest.mark.asyncio
async def test_process_voice_command(voice_adapter, mock_voice_processor):
    """Prueba el procesamiento de comandos de voz."""
    # Configurar
    context = {
        "language_code": "es-ES",
        "analyze_emotion": True
    }
    
    # Ejecutar
    result = await voice_adapter.process_voice_command(TEST_AUDIO, context)
    
    # Verificar
    assert "text" in result
    assert result["text"] == "Texto transcrito de prueba"
    assert result["confidence"] >= 0.9
    assert "emotion" in result
    
    # Verificar llamadas a los mocks
    mock_voice_processor.speech_to_text.assert_called_once_with(
        TEST_AUDIO, 
        context.get("language_code"), 
        context.get("analyze_emotion")
    )

@pytest.mark.asyncio
async def test_generate_voice_response(voice_adapter, mock_voice_processor):
    """Prueba la generación de respuestas de voz."""
    # Configurar
    voice_config = {
        "voice_name": "es-ES-Standard-A",
        "speaking_rate": 1.0
    }
    
    # Ejecutar
    audio_data, metadata = await voice_adapter.generate_voice_response(TEST_TEXT, voice_config)
    
    # Verificar
    assert len(audio_data) > 0
    assert "duration_seconds" in metadata
    assert metadata["duration_seconds"] == 2.0
    
    # Verificar llamadas a los mocks
    mock_voice_processor.text_to_speech.assert_called_once_with(TEST_TEXT, voice_config)

@pytest.mark.asyncio
async def test_analyze_voice_emotion(voice_adapter, mock_voice_processor):
    """Prueba el análisis de emociones en la voz."""
    # Configurar
    transcript = "Texto de prueba para análisis de emociones"
    
    # Ejecutar
    result = await voice_adapter.analyze_voice_emotion(TEST_AUDIO, transcript)
    
    # Verificar
    assert "emotions" in result
    assert "dominant_emotion" in result
    assert result["dominant_emotion"] == "neutral"
    
    # Verificar llamadas a los mocks
    mock_voice_processor.analyze_voice_emotion.assert_called_once_with(TEST_AUDIO, transcript)

@pytest.mark.asyncio
async def test_get_available_voices(voice_adapter, mock_voice_processor):
    """Prueba la obtención de voces disponibles."""
    # Configurar
    language_code = "es-ES"
    
    # Ejecutar
    voices = await voice_adapter.get_available_voices(language_code)
    
    # Verificar
    assert len(voices) == 2
    assert voices[0]["name"] == "es-ES-Standard-A"
    assert voices[1]["name"] == "es-ES-Standard-B"
    
    # Verificar llamadas a los mocks
    mock_voice_processor.get_available_voices.assert_called_once_with(language_code)

@pytest.mark.asyncio
async def test_process_conversation(voice_adapter, mock_voice_processor):
    """Prueba el procesamiento de una conversación completa."""
    # Configurar
    context = {
        "language_code": "es-ES",
        "analyze_emotion": True,
        "voice_config": {
            "voice_name": "es-ES-Standard-A",
            "speaking_rate": 1.0
        }
    }
    
    # Ejecutar
    result = await voice_adapter.process_conversation(TEST_AUDIO, context)
    
    # Verificar
    assert "input" in result
    assert "response" in result
    assert "text" in result["input"]
    assert "text" in result["response"]
    assert "audio" in result["response"]
    
    # Verificar llamadas a los mocks
    mock_voice_processor.speech_to_text.assert_called_once()
    mock_voice_processor.text_to_speech.assert_called_once()

@pytest.mark.asyncio
async def test_process_conversation_with_empty_text(voice_adapter, mock_voice_processor):
    """Prueba el procesamiento de una conversación con texto vacío."""
    # Configurar
    mock_voice_processor.speech_to_text.return_value = {
        "text": "",
        "confidence": 0.0
    }
    
    # Ejecutar
    result = await voice_adapter.process_conversation(TEST_AUDIO)
    
    # Verificar
    assert "input" in result
    assert "error" in result
    
    # Verificar llamadas a los mocks
    mock_voice_processor.speech_to_text.assert_called_once()
    mock_voice_processor.text_to_speech.assert_not_called()

@pytest.mark.asyncio
async def test_get_stats(voice_adapter, mock_voice_processor):
    """Prueba la obtención de estadísticas."""
    # Ejecutar
    stats = await voice_adapter.get_stats()
    
    # Verificar
    assert "speech_to_text_operations" in stats
    assert "text_to_speech_operations" in stats
    assert "emotion_analysis_operations" in stats
    
    # Verificar llamadas a los mocks
    mock_voice_processor.get_stats.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling_in_process_voice_command(voice_adapter, mock_voice_processor):
    """Prueba el manejo de errores en el procesamiento de comandos de voz."""
    # Configurar
    mock_voice_processor.speech_to_text.side_effect = Exception("Error de prueba")
    
    # Ejecutar
    result = await voice_adapter.process_voice_command(TEST_AUDIO)
    
    # Verificar
    assert "error" in result
    assert result["text"] == ""
    assert result["confidence"] == 0.0

@pytest.mark.asyncio
async def test_error_handling_in_generate_voice_response(voice_adapter, mock_voice_processor):
    """Prueba el manejo de errores en la generación de respuestas de voz."""
    # Configurar
    mock_voice_processor.text_to_speech.side_effect = Exception("Error de prueba")
    
    # Ejecutar
    audio_data, metadata = await voice_adapter.generate_voice_response(TEST_TEXT)
    
    # Verificar
    assert len(audio_data) == 0
    assert "error" in metadata

@pytest.mark.asyncio
async def test_error_handling_in_process_conversation(voice_adapter, mock_voice_processor):
    """Prueba el manejo de errores en el procesamiento de una conversación."""
    # Configurar
    mock_voice_processor.speech_to_text.side_effect = Exception("Error de prueba")
    
    # Ejecutar
    result = await voice_adapter.process_conversation(TEST_AUDIO)
    
    # Verificar
    assert "error" in result
