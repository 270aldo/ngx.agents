"""
Pruebas para el procesador de voz.

Este módulo contiene pruebas unitarias para el procesador de voz.
"""

import asyncio
import os
import pytest
from unittest.mock import MagicMock, patch

from core.voice_processor import VoiceProcessor
from clients.vertex_ai.voice.stt_client import STTClient
from clients.vertex_ai.voice.tts_client import TTSClient
from clients.vertex_ai.voice.emotion_analyzer import EmotionAnalyzer

# Datos de prueba
TEST_AUDIO = b'\x00\x00' * 1000  # Audio de prueba (silencio)
TEST_TEXT = "Texto de prueba para síntesis de voz"

@pytest.fixture
def mock_stt_client():
    """Fixture para crear un cliente STT mock."""
    client = MagicMock(spec=STTClient)
    client.transcribe.return_value = {
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
        }
    }
    client.get_stats.return_value = {
        "transcribe_operations": 1,
        "errors": 0,
        "avg_latency_ms": 100.0,
        "mock_mode": True
    }
    return client

@pytest.fixture
def mock_tts_client():
    """Fixture para crear un cliente TTS mock."""
    client = MagicMock(spec=TTSClient)
    client.synthesize.return_value = (
        b'\x00\x00' * 1000,  # Audio sintético
        {
            "duration_seconds": 2.0,
            "sample_rate": 24000,
            "channels": 1,
            "encoding": "LINEAR16"
        }
    )
    client.get_available_voices.return_value = [
        {"name": "es-ES-Standard-A", "gender": "FEMALE", "language_codes": ["es-ES"]},
        {"name": "es-ES-Standard-B", "gender": "MALE", "language_codes": ["es-ES"]}
    ]
    client.get_stats.return_value = {
        "synthesize_operations": 1,
        "cache_hits": 0,
        "cache_misses": 1,
        "cache_hit_ratio": 0.0,
        "errors": 0,
        "avg_latency_ms": 150.0,
        "mock_mode": True
    }
    return client

@pytest.fixture
def mock_emotion_analyzer():
    """Fixture para crear un analizador de emociones mock."""
    analyzer = MagicMock(spec=EmotionAnalyzer)
    analyzer.analyze.return_value = {
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
    analyzer.get_stats.return_value = {
        "analyze_operations": 1,
        "errors": 0,
        "avg_latency_ms": 200.0,
        "mock_mode": True
    }
    return analyzer

@pytest.fixture
def voice_processor(mock_stt_client, mock_tts_client, mock_emotion_analyzer):
    """Fixture para crear un procesador de voz con clientes mock."""
    processor = VoiceProcessor()
    processor.stt_client = mock_stt_client
    processor.tts_client = mock_tts_client
    processor.emotion_analyzer = mock_emotion_analyzer
    return processor

@pytest.mark.asyncio
async def test_speech_to_text(voice_processor, mock_stt_client):
    """Prueba la conversión de voz a texto."""
    # Configurar
    language_code = "es-ES"
    analyze_emotion = True
    
    # Ejecutar
    result = await voice_processor.speech_to_text(TEST_AUDIO, language_code, analyze_emotion)
    
    # Verificar
    assert "text" in result
    assert result["text"] == "Texto transcrito de prueba"
    assert result["confidence"] >= 0.9
    assert "emotion" in result
    assert result["emotion"]["dominant_emotion"] == "neutral"
    
    # Verificar llamadas a los mocks
    mock_stt_client.transcribe.assert_called_once_with(TEST_AUDIO, language_code)
    voice_processor.emotion_analyzer.analyze.assert_called_once()

@pytest.mark.asyncio
async def test_speech_to_text_without_emotion(voice_processor, mock_stt_client):
    """Prueba la conversión de voz a texto sin análisis de emociones."""
    # Configurar
    language_code = "es-ES"
    analyze_emotion = False
    
    # Ejecutar
    result = await voice_processor.speech_to_text(TEST_AUDIO, language_code, analyze_emotion)
    
    # Verificar
    assert "text" in result
    assert result["text"] == "Texto transcrito de prueba"
    assert "emotion" not in result
    
    # Verificar llamadas a los mocks
    mock_stt_client.transcribe.assert_called_once_with(TEST_AUDIO, language_code)
    voice_processor.emotion_analyzer.analyze.assert_not_called()

@pytest.mark.asyncio
async def test_text_to_speech(voice_processor, mock_tts_client):
    """Prueba la conversión de texto a voz."""
    # Configurar
    voice_config = {
        "voice_name": "es-ES-Standard-A",
        "speaking_rate": 1.0
    }
    
    # Ejecutar
    audio_data, metadata = await voice_processor.text_to_speech(TEST_TEXT, voice_config)
    
    # Verificar
    assert len(audio_data) > 0
    assert "duration_seconds" in metadata
    assert metadata["duration_seconds"] == 2.0
    
    # Verificar llamadas a los mocks
    mock_tts_client.synthesize.assert_called_once_with(TEST_TEXT, voice_config)

@pytest.mark.asyncio
async def test_analyze_voice_emotion(voice_processor, mock_emotion_analyzer):
    """Prueba el análisis de emociones en la voz."""
    # Configurar
    transcript = "Texto de prueba para análisis de emociones"
    
    # Ejecutar
    result = await voice_processor.analyze_voice_emotion(TEST_AUDIO, transcript)
    
    # Verificar
    assert "emotions" in result
    assert "dominant_emotion" in result
    assert result["dominant_emotion"] == "neutral"
    assert "confidence" in result
    
    # Verificar llamadas a los mocks
    mock_emotion_analyzer.analyze.assert_called_once_with(TEST_AUDIO, transcript)

@pytest.mark.asyncio
async def test_analyze_voice_emotion_without_transcript(voice_processor, mock_stt_client, mock_emotion_analyzer):
    """Prueba el análisis de emociones sin transcripción previa."""
    # Ejecutar
    result = await voice_processor.analyze_voice_emotion(TEST_AUDIO)
    
    # Verificar
    assert "emotions" in result
    assert "dominant_emotion" in result
    
    # Verificar llamadas a los mocks
    mock_stt_client.transcribe.assert_called_once()
    mock_emotion_analyzer.analyze.assert_called_once()

@pytest.mark.asyncio
async def test_get_available_voices(voice_processor, mock_tts_client):
    """Prueba la obtención de voces disponibles."""
    # Configurar
    language_code = "es-ES"
    
    # Ejecutar
    voices = await voice_processor.get_available_voices(language_code)
    
    # Verificar
    assert len(voices) == 2
    assert voices[0]["name"] == "es-ES-Standard-A"
    assert voices[1]["name"] == "es-ES-Standard-B"
    
    # Verificar llamadas a los mocks
    mock_tts_client.get_available_voices.assert_called_once_with(language_code)

@pytest.mark.asyncio
async def test_get_stats(voice_processor, mock_stt_client, mock_tts_client, mock_emotion_analyzer):
    """Prueba la obtención de estadísticas."""
    # Ejecutar
    stats = await voice_processor.get_stats()
    
    # Verificar
    assert "speech_to_text_operations" in stats
    assert "text_to_speech_operations" in stats
    assert "emotion_analysis_operations" in stats
    assert "stt_stats" in stats
    assert "tts_stats" in stats
    assert "emotion_stats" in stats
    
    # Verificar llamadas a los mocks
    mock_stt_client.get_stats.assert_called_once()
    mock_tts_client.get_stats.assert_called_once()
    mock_emotion_analyzer.get_stats.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling_in_speech_to_text(voice_processor, mock_stt_client):
    """Prueba el manejo de errores en la conversión de voz a texto."""
    # Configurar
    mock_stt_client.transcribe.side_effect = Exception("Error de prueba")
    
    # Ejecutar
    result = await voice_processor.speech_to_text(TEST_AUDIO)
    
    # Verificar
    assert "error" in result
    assert result["text"] == ""
    assert result["confidence"] == 0.0

@pytest.mark.asyncio
async def test_error_handling_in_text_to_speech(voice_processor, mock_tts_client):
    """Prueba el manejo de errores en la conversión de texto a voz."""
    # Configurar
    mock_tts_client.synthesize.side_effect = Exception("Error de prueba")
    
    # Ejecutar
    audio_data, metadata = await voice_processor.text_to_speech(TEST_TEXT)
    
    # Verificar
    assert len(audio_data) == 0
    assert "error" in metadata

@pytest.mark.asyncio
async def test_error_handling_in_analyze_voice_emotion(voice_processor, mock_emotion_analyzer):
    """Prueba el manejo de errores en el análisis de emociones."""
    # Configurar
    mock_emotion_analyzer.analyze.side_effect = Exception("Error de prueba")
    
    # Ejecutar
    result = await voice_processor.analyze_voice_emotion(TEST_AUDIO, "Texto de prueba")
    
    # Verificar
    assert "error" in result
    assert result["dominant_emotion"] == "neutral"
    assert result["confidence"] == 0.0
