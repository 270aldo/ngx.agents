"""
Script para probar el procesamiento de voz.

Este script demuestra cómo utilizar el Adaptador de Voz para procesar
comandos de voz, generar respuestas de voz y analizar emociones.
"""

import asyncio
import os
import sys
import wave
from datetime import datetime
from typing import Dict, List, Any

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.adapters.voice_adapter import voice_adapter

async def setup_environment():
    """Configura el entorno para las pruebas de voz."""
    print("\n=== Configurando entorno para procesamiento de voz ===")
    
    # Verificar si hay credenciales de Google Cloud
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        print("ADVERTENCIA: No se encontró GOOGLE_APPLICATION_CREDENTIALS en el entorno.")
        print("El procesamiento de voz funcionará en modo mock.")
    else:
        print(f"Usando credenciales de Google Cloud: {credentials_path}")
    
    # Configurar variables de entorno para voz
    if not os.environ.get("VOICE_DEFAULT_LANGUAGE"):
        os.environ["VOICE_DEFAULT_LANGUAGE"] = "es-ES"
        print(f"Configurado idioma predeterminado: {os.environ['VOICE_DEFAULT_LANGUAGE']}")
    
    if not os.environ.get("VOICE_DEFAULT_VOICE"):
        os.environ["VOICE_DEFAULT_VOICE"] = "es-ES-Standard-A"
        print(f"Configurada voz predeterminada: {os.environ['VOICE_DEFAULT_VOICE']}")
    
    print("Entorno configurado para procesamiento de voz")

async def create_test_audio():
    """Crea un archivo de audio de prueba si no existe."""
    test_audio_path = "test_audio.wav"
    
    if os.path.exists(test_audio_path):
        print(f"Usando archivo de audio existente: {test_audio_path}")
        return test_audio_path
    
    print(f"Creando archivo de audio de prueba: {test_audio_path}")
    
    # Crear un archivo WAV con silencio (para pruebas en modo mock)
    sample_rate = 16000
    duration_seconds = 3
    
    with wave.open(test_audio_path, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b'\x00' * sample_rate * 2 * duration_seconds)
    
    print(f"Archivo de audio de prueba creado: {test_audio_path} ({duration_seconds} segundos)")
    return test_audio_path

async def test_speech_to_text(audio_path: str):
    """Prueba la conversión de voz a texto."""
    print("\n=== Probando conversión de voz a texto ===")
    
    # Cargar audio
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # Configurar contexto
    context = {
        "language_code": "es-ES",
        "analyze_emotion": True
    }
    
    # Procesar comando de voz
    print("Procesando audio...")
    result = await voice_adapter.process_voice_command(audio_data, context)
    
    # Mostrar resultados
    print(f"Texto reconocido: '{result.get('text', '')}'")
    print(f"Confianza: {result.get('confidence', 0.0):.2f}")
    
    # Mostrar información de emociones si está disponible
    if "emotion" in result:
        emotion = result["emotion"]
        print("\nAnálisis de emociones:")
        print(f"Emoción dominante: {emotion.get('dominant_emotion', 'desconocida')}")
        print(f"Confianza: {emotion.get('confidence', 0.0):.2f}")
        
        if "emotions" in emotion:
            print("\nDistribución de emociones:")
            for emo, value in emotion["emotions"].items():
                print(f"  - {emo}: {value:.2f}")
        
        if "analysis" in emotion:
            print(f"\nAnálisis: {emotion['analysis']}")
    
    return result

async def test_text_to_speech():
    """Prueba la conversión de texto a voz."""
    print("\n=== Probando conversión de texto a voz ===")
    
    # Texto de prueba
    text = "Esto es una prueba de síntesis de voz para NGX Agents. El sistema puede convertir texto a voz de manera eficiente."
    
    # Configuración de voz
    voice_config = {
        "voice_name": "es-ES-Standard-A",
        "speaking_rate": 1.0,
        "pitch": 0.0
    }
    
    print(f"Sintetizando texto: '{text}'")
    print(f"Configuración de voz: {voice_config}")
    
    # Generar audio
    audio_data, metadata = await voice_adapter.generate_voice_response(text, voice_config)
    
    # Guardar audio generado
    output_path = "test_output.wav"
    with open(output_path, 'wb') as f:
        f.write(audio_data)
    
    # Mostrar resultados
    print(f"\nAudio generado guardado en: {output_path}")
    print(f"Tamaño del audio: {len(audio_data)} bytes")
    print(f"Duración estimada: {metadata.get('duration_seconds', 0):.2f} segundos")
    
    return output_path

async def test_emotion_analysis(audio_path: str):
    """Prueba el análisis de emociones en la voz."""
    print("\n=== Probando análisis de emociones en la voz ===")
    
    # Cargar audio
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # Analizar emociones
    print("Analizando emociones en el audio...")
    result = await voice_adapter.analyze_voice_emotion(audio_data)
    
    # Mostrar resultados
    print(f"Emoción dominante: {result.get('dominant_emotion', 'desconocida')}")
    print(f"Confianza: {result.get('confidence', 0.0):.2f}")
    
    if "emotions" in result:
        print("\nDistribución de emociones:")
        for emotion, value in result["emotions"].items():
            print(f"  - {emotion}: {value:.2f}")
    
    if "analysis" in result:
        print(f"\nAnálisis: {result['analysis']}")
    
    return result

async def test_conversation(audio_path: str):
    """Prueba una conversación completa (entrada y respuesta de voz)."""
    print("\n=== Probando conversación completa ===")
    
    # Cargar audio
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    # Configurar contexto
    context = {
        "language_code": "es-ES",
        "analyze_emotion": True,
        "voice_config": {
            "voice_name": "es-ES-Standard-A",
            "speaking_rate": 1.0
        }
    }
    
    # Procesar conversación
    print("Procesando conversación...")
    result = await voice_adapter.process_conversation(audio_data, context)
    
    # Verificar si hay error
    if "error" in result:
        print(f"Error: {result['error']}")
        return result
    
    # Mostrar resultados de entrada
    input_result = result.get("input", {})
    print(f"Texto reconocido: '{input_result.get('text', '')}'")
    print(f"Confianza: {input_result.get('confidence', 0.0):.2f}")
    
    # Mostrar resultados de respuesta
    response = result.get("response", {})
    print(f"\nRespuesta generada: '{response.get('text', '')}'")
    
    # Guardar audio de respuesta
    if "audio" in response:
        output_path = "conversation_response.wav"
        with open(output_path, 'wb') as f:
            f.write(response["audio"])
        
        print(f"Audio de respuesta guardado en: {output_path}")
        print(f"Tamaño del audio: {len(response['audio'])} bytes")
        
        if "audio_metadata" in response:
            metadata = response["audio_metadata"]
            print(f"Duración estimada: {metadata.get('duration_seconds', 0):.2f} segundos")
    
    # Mostrar información de emociones si está disponible
    if "emotion" in result:
        emotion = result["emotion"]
        print("\nAnálisis de emociones:")
        print(f"Emoción dominante: {emotion.get('dominant_emotion', 'desconocida')}")
        print(f"Confianza: {emotion.get('confidence', 0.0):.2f}")
    
    return result

async def test_available_voices():
    """Prueba la obtención de voces disponibles."""
    print("\n=== Probando obtención de voces disponibles ===")
    
    # Obtener todas las voces
    print("Obteniendo todas las voces disponibles...")
    all_voices = await voice_adapter.get_available_voices()
    
    print(f"Total de voces disponibles: {len(all_voices)}")
    
    # Obtener voces en español
    print("\nObteniendo voces en español...")
    es_voices = await voice_adapter.get_available_voices("es-ES")
    
    print(f"Total de voces en español: {len(es_voices)}")
    
    # Mostrar algunas voces de ejemplo
    if es_voices:
        print("\nEjemplos de voces en español:")
        for i, voice in enumerate(es_voices[:5]):  # Mostrar hasta 5 voces
            print(f"{i+1}. {voice.get('name', 'Sin nombre')} - {voice.get('gender', 'Género desconocido')}")
    
    return all_voices, es_voices

async def show_stats():
    """Muestra estadísticas del procesamiento de voz."""
    print("\n=== Estadísticas del procesamiento de voz ===")
    
    # Obtener estadísticas
    stats = await voice_adapter.get_stats()
    
    # Mostrar estadísticas principales
    print(f"Operaciones de voz a texto: {stats.get('speech_to_text_operations', 0)}")
    print(f"Operaciones de texto a voz: {stats.get('text_to_speech_operations', 0)}")
    print(f"Operaciones de análisis de emociones: {stats.get('emotion_analysis_operations', 0)}")
    print(f"Errores: {stats.get('errors', 0)}")
    
    # Mostrar latencias promedio
    print(f"\nLatencia promedio de voz a texto: {stats.get('avg_stt_latency_ms', 0):.2f} ms")
    print(f"Latencia promedio de texto a voz: {stats.get('avg_tts_latency_ms', 0):.2f} ms")
    print(f"Latencia promedio de análisis de emociones: {stats.get('avg_emotion_latency_ms', 0):.2f} ms")
    
    # Mostrar configuración
    print(f"\nIdioma predeterminado: {stats.get('default_language', 'N/A')}")
    print(f"Voz predeterminada: {stats.get('default_voice', 'N/A')}")
    print(f"Análisis de emociones habilitado: {stats.get('analyze_emotions', False)}")
    
    # Mostrar estadísticas de clientes
    stt_stats = stats.get("stt_stats", {})
    tts_stats = stats.get("tts_stats", {})
    emotion_stats = stats.get("emotion_stats", {})
    
    print("\nEstadísticas del cliente STT:")
    print(f"  - Operaciones de transcripción: {stt_stats.get('transcribe_operations', 0)}")
    print(f"  - Errores: {stt_stats.get('errors', 0)}")
    print(f"  - Latencia promedio: {stt_stats.get('avg_latency_ms', 0):.2f} ms")
    print(f"  - Modo mock: {stt_stats.get('mock_mode', False)}")
    
    print("\nEstadísticas del cliente TTS:")
    print(f"  - Operaciones de síntesis: {tts_stats.get('synthesize_operations', 0)}")
    print(f"  - Caché hits: {tts_stats.get('cache_hits', 0)}")
    print(f"  - Caché misses: {tts_stats.get('cache_misses', 0)}")
    print(f"  - Ratio de caché hits: {tts_stats.get('cache_hit_ratio', 0):.2f}")
    print(f"  - Errores: {tts_stats.get('errors', 0)}")
    print(f"  - Latencia promedio: {tts_stats.get('avg_latency_ms', 0):.2f} ms")
    print(f"  - Modo mock: {tts_stats.get('mock_mode', False)}")
    
    print("\nEstadísticas del analizador de emociones:")
    print(f"  - Operaciones de análisis: {emotion_stats.get('analyze_operations', 0)}")
    print(f"  - Errores: {emotion_stats.get('errors', 0)}")
    print(f"  - Latencia promedio: {emotion_stats.get('avg_latency_ms', 0):.2f} ms")
    print(f"  - Modo mock: {emotion_stats.get('mock_mode', False)}")
    
    return stats

async def main():
    """Función principal."""
    try:
        print("=== Demostración de Procesamiento de Voz ===")
        
        # Configurar entorno
        await setup_environment()
        
        # Crear audio de prueba
        audio_path = await create_test_audio()
        
        # Probar conversión de voz a texto
        await test_speech_to_text(audio_path)
        
        # Probar conversión de texto a voz
        output_path = await test_text_to_speech()
        
        # Probar análisis de emociones
        await test_emotion_analysis(audio_path)
        
        # Probar conversación completa
        await test_conversation(audio_path)
        
        # Probar obtención de voces disponibles
        await test_available_voices()
        
        # Mostrar estadísticas
        await show_stats()
        
        print("\n=== Demostración completada ===")
        
    except Exception as e:
        print(f"Error en la demostración: {e}")

if __name__ == "__main__":
    # Ejecutar función principal
    asyncio.run(main())
