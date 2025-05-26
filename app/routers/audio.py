"""
Router para endpoints de procesamiento de audio y voz.

Proporciona endpoints REST para:
- Transcripción de audio (Speech-to-Text)
- Síntesis de voz (Text-to-Speech)
- Análisis de emociones en voz
- Comandos de voz para entrenamientos
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, Optional, List
import base64
import io
import json
from datetime import datetime

from app.middleware.auth import get_current_user
from app.schemas.auth import UserPayload
from core.logging_config import get_logger
from core.telemetry import Telemetry
from infrastructure.adapters.speech_adapter import speech_adapter
from agents.skills.audio_voice_skills import AUDIO_VOICE_SKILLS
from core.state_manager_optimized import state_manager

logger = get_logger(__name__)
telemetry = Telemetry()

# Crear router
router = APIRouter(
    prefix="/audio",
    tags=["audio", "speech"],
    responses={404: {"description": "Not found"}},
)


@router.post("/transcribe")
async def transcribe_audio(
    file: Optional[UploadFile] = File(None),
    audio_url: Optional[str] = Form(None),
    audio_base64: Optional[str] = Form(None),
    language_code: str = Form("es-ES"),
    current_user: UserPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Transcribe audio a texto usando Vertex AI Speech-to-Text.

    Acepta audio en múltiples formatos:
    - Archivo subido (multipart/form-data)
    - URL de audio
    - Audio en base64

    Args:
        file: Archivo de audio subido
        audio_url: URL del archivo de audio
        audio_base64: Audio codificado en base64
        language_code: Código de idioma (default: es-ES)
        current_user: Usuario autenticado

    Returns:
        Transcripción del audio con nivel de confianza
    """
    span = telemetry.start_span("audio_transcribe_endpoint")

    try:
        # Validar que se proporcione al menos una fuente de audio
        if not file and not audio_url and not audio_base64:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un archivo de audio, URL o base64",
            )

        # Procesar el audio según la fuente
        audio_data = None

        if file:
            # Leer archivo subido
            content = await file.read()
            audio_data = base64.b64encode(content).decode("utf-8")
            telemetry.add_span_attribute(span, "audio_source", "file_upload")
            telemetry.add_span_attribute(span, "file_size", len(content))

        elif audio_url:
            # URL proporcionada
            audio_data = {"url": audio_url}
            telemetry.add_span_attribute(span, "audio_source", "url")

        elif audio_base64:
            # Base64 proporcionado
            audio_data = audio_base64
            telemetry.add_span_attribute(span, "audio_source", "base64")

        # Realizar transcripción
        logger.info(f"Transcribiendo audio para usuario {current_user.user_id}")

        result = await speech_adapter.transcribe_audio(
            audio_data=audio_data,
            language_code=language_code,
            agent_id=f"user_{current_user.user_id}",
        )

        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Error en transcripción: {result.get('error', 'Unknown error')}",
            )

        # Registrar en el historial del usuario
        await state_manager.add_to_history(
            session_id=current_user.user_id,
            message={
                "type": "audio_transcription",
                "timestamp": datetime.now().isoformat(),
                "language": language_code,
                "transcription": result.get("text", ""),
                "confidence": result.get("confidence", 0.0),
            },
        )

        telemetry.add_span_attribute(
            span, "transcription_length", len(result.get("text", ""))
        )
        telemetry.add_span_attribute(span, "confidence", result.get("confidence", 0.0))

        return {
            "transcription": result.get("text", ""),
            "confidence": result.get("confidence", 0.0),
            "language_code": language_code,
            "alternatives": result.get("alternatives", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint de transcripción: {e}")
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice_name: str = Form("es-ES-Standard-A"),
    language_code: str = Form("es-ES"),
    output_format: str = Form("base64"),  # base64 o audio_stream
    current_user: UserPayload = Depends(get_current_user),
) -> Any:
    """
    Sintetiza texto a voz usando Vertex AI Text-to-Speech.

    Args:
        text: Texto a sintetizar
        voice_name: Nombre de la voz a usar
        language_code: Código de idioma
        output_format: Formato de salida (base64 o audio_stream)
        current_user: Usuario autenticado

    Returns:
        Audio sintetizado en el formato solicitado
    """
    span = telemetry.start_span("audio_synthesize_endpoint")

    try:
        # Validar longitud del texto
        if len(text) > 5000:
            raise HTTPException(
                status_code=400, detail="El texto no puede exceder 5000 caracteres"
            )

        telemetry.add_span_attribute(span, "text_length", len(text))
        telemetry.add_span_attribute(span, "voice_name", voice_name)
        telemetry.add_span_attribute(span, "output_format", output_format)

        # Realizar síntesis
        logger.info(f"Sintetizando voz para usuario {current_user.user_id}")

        result = await speech_adapter.synthesize_speech(
            text=text,
            voice_name=voice_name,
            language_code=language_code,
            agent_id=f"user_{current_user.user_id}",
        )

        if result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Error en síntesis: {result.get('error', 'Unknown error')}",
            )

        # Registrar en el historial
        await state_manager.add_to_history(
            session_id=current_user.user_id,
            message={
                "type": "speech_synthesis",
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text),
                "voice": voice_name,
                "language": language_code,
            },
        )

        # Devolver según el formato solicitado
        if output_format == "audio_stream":
            # Decodificar base64 y devolver como stream de audio
            audio_data = base64.b64decode(result.get("audio_base64", ""))
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg",
                headers={"Content-Disposition": "attachment; filename=speech.mp3"},
            )
        else:
            # Devolver como JSON con base64
            return {
                "audio_base64": result.get("audio_base64", ""),
                "audio_format": result.get("audio_format", "mp3"),
                "voice_used": voice_name,
                "text_length": len(text),
                "duration_estimate": result.get("duration_estimate", 0.0),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint de síntesis: {e}")
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.post("/analyze-emotion")
async def analyze_voice_emotion(
    file: Optional[UploadFile] = File(None),
    audio_url: Optional[str] = Form(None),
    audio_base64: Optional[str] = Form(None),
    analysis_depth: str = Form("detailed"),
    include_recommendations: bool = Form(True),
    current_user: UserPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Analiza las emociones y estado del usuario a través de su voz.

    Args:
        file: Archivo de audio subido
        audio_url: URL del archivo de audio
        audio_base64: Audio codificado en base64
        analysis_depth: Profundidad del análisis (basic/detailed)
        include_recommendations: Si incluir recomendaciones
        current_user: Usuario autenticado

    Returns:
        Análisis emocional con estado detectado y recomendaciones
    """
    span = telemetry.start_span("audio_analyze_emotion_endpoint")

    try:
        # Validar fuente de audio
        if not file and not audio_url and not audio_base64:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un archivo de audio, URL o base64",
            )

        # Procesar el audio
        audio_data = None

        if file:
            content = await file.read()
            audio_data = base64.b64encode(content).decode("utf-8")
        elif audio_url:
            audio_data = {"url": audio_url}
        elif audio_base64:
            audio_data = audio_base64

        # Obtener estado emocional previo del usuario
        user_state = await state_manager.get_state(current_user.user_id)
        previous_emotional_state = user_state.get("emotional_state", {})

        # Usar la skill de análisis emocional
        emotion_skill = AUDIO_VOICE_SKILLS["voice_emotion_analysis"]

        analysis_result = await emotion_skill.execute(
            {
                "audio_data": audio_data,
                "analysis_depth": analysis_depth,
                "previous_state": previous_emotional_state,
            }
        )

        if analysis_result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Error en análisis: {analysis_result.get('error', 'Unknown error')}",
            )

        # Actualizar estado emocional del usuario
        await state_manager.update_state(
            session_id=current_user.user_id,
            updates={
                "emotional_state": {
                    "current": analysis_result.get("emotional_state"),
                    "timestamp": datetime.now().isoformat(),
                    "confidence": analysis_result.get("confidence", 0.0),
                    "emotions": analysis_result.get("emotions", {}),
                }
            },
        )

        # Preparar respuesta
        response = {
            "emotional_state": analysis_result.get("emotional_state"),
            "confidence": analysis_result.get("confidence", 0.0),
            "emotions": analysis_result.get("emotions", {}),
            "physical_indicators": analysis_result.get("physical_indicators", {}),
            "transcription": analysis_result.get("transcription", ""),
            "needs_intervention": analysis_result.get("needs_intervention", False),
        }

        if include_recommendations:
            response["recommendations"] = analysis_result.get("recommendations", [])

        telemetry.add_span_attribute(
            span, "emotional_state", response["emotional_state"]
        )
        telemetry.add_span_attribute(span, "confidence", response["confidence"])

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en análisis de emociones: {e}")
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.post("/voice-command")
async def process_voice_command(
    file: Optional[UploadFile] = File(None),
    audio_url: Optional[str] = Form(None),
    audio_base64: Optional[str] = Form(None),
    workout_state: Optional[str] = Form(
        "{}"
    ),  # JSON string del estado del entrenamiento
    current_user: UserPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Procesa comandos de voz para controlar entrenamientos.

    Args:
        file: Archivo de audio con el comando
        audio_url: URL del archivo de audio
        audio_base64: Audio codificado en base64
        workout_state: Estado actual del entrenamiento (JSON)
        current_user: Usuario autenticado

    Returns:
        Comando identificado y acción a ejecutar
    """
    span = telemetry.start_span("audio_voice_command_endpoint")

    try:
        # Validar fuente de audio
        if not file and not audio_url and not audio_base64:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar un archivo de audio, URL o base64",
            )

        # Procesar el audio
        audio_data = None

        if file:
            content = await file.read()
            audio_data = base64.b64encode(content).decode("utf-8")
        elif audio_url:
            audio_data = {"url": audio_url}
        elif audio_base64:
            audio_data = audio_base64

        # Parsear estado del entrenamiento
        try:
            workout_state_dict = json.loads(workout_state)
        except:
            workout_state_dict = {}

        # Usar la skill de comandos de voz
        command_skill = AUDIO_VOICE_SKILLS["voice_command"]

        command_result = await command_skill.execute(
            {
                "audio_data": audio_data,
                "language_code": "es-ES",
                "workout_state": workout_state_dict,
            }
        )

        if command_result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Error procesando comando: {command_result.get('error', 'Unknown error')}",
            )

        # Registrar comando en el historial
        await state_manager.add_to_history(
            session_id=current_user.user_id,
            message={
                "type": "voice_command",
                "timestamp": datetime.now().isoformat(),
                "command": command_result.get("command"),
                "transcription": command_result.get("transcription", ""),
                "action": command_result.get("action"),
                "confidence": command_result.get("confidence", 0.0),
            },
        )

        telemetry.add_span_attribute(span, "command", command_result.get("command"))
        telemetry.add_span_attribute(span, "action", command_result.get("action"))
        telemetry.add_span_attribute(
            span, "confidence", command_result.get("confidence", 0.0)
        )

        return command_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando comando de voz: {e}")
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.post("/workout-feedback")
async def generate_workout_feedback(
    feedback_type: str = Form(...),
    exercise_name: Optional[str] = Form(None),
    rest_seconds: Optional[int] = Form(None),
    user_name: Optional[str] = Form(None),
    voice_name: str = Form("es-ES-Standard-B"),
    output_format: str = Form("base64"),
    current_user: UserPayload = Depends(get_current_user),
) -> Any:
    """
    Genera feedback de audio personalizado para entrenamientos.

    Args:
        feedback_type: Tipo de feedback (encouragement, form_correction, etc.)
        exercise_name: Nombre del ejercicio actual
        rest_seconds: Segundos de descanso (si aplica)
        user_name: Nombre del usuario para personalización
        voice_name: Voz a utilizar
        output_format: Formato de salida
        current_user: Usuario autenticado

    Returns:
        Audio del feedback en el formato solicitado
    """
    span = telemetry.start_span("audio_workout_feedback_endpoint")

    try:
        # Validar tipo de feedback
        valid_types = [
            "encouragement",
            "form_correction",
            "rest_reminder",
            "set_completion",
            "workout_start",
            "workout_end",
        ]

        if feedback_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de feedback inválido. Debe ser uno de: {valid_types}",
            )

        # Usar la skill de feedback de audio
        feedback_skill = AUDIO_VOICE_SKILLS["audio_feedback"]

        # Preparar contexto
        context = {
            "feedback_type": feedback_type,
            "parameters": {},
            "voice_settings": {"voice_name": voice_name, "language_code": "es-ES"},
            "user_profile": {},
        }

        # Agregar parámetros específicos
        if rest_seconds:
            context["parameters"]["rest_seconds"] = rest_seconds

        if user_name:
            context["user_profile"]["name"] = user_name

        # Generar feedback
        feedback_result = await feedback_skill.execute(context)

        if feedback_result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Error generando feedback: {feedback_result.get('error', 'Unknown error')}",
            )

        telemetry.add_span_attribute(span, "feedback_type", feedback_type)
        telemetry.add_span_attribute(span, "voice_name", voice_name)

        # Devolver según formato
        if output_format == "audio_stream":
            audio_data = base64.b64decode(feedback_result.get("audio_base64", ""))
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"attachment; filename=feedback_{feedback_type}.mp3"
                },
            )
        else:
            return {
                "audio_base64": feedback_result.get("audio_base64", ""),
                "text": feedback_result.get("text", ""),
                "duration": feedback_result.get("duration_estimate", 0.0),
                "feedback_type": feedback_type,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando feedback de audio: {e}")
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.get("/voices")
async def list_available_voices(
    language_code: str = "es-ES", current_user: UserPayload = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista las voces disponibles para síntesis de voz.

    Args:
        language_code: Código de idioma para filtrar voces
        current_user: Usuario autenticado

    Returns:
        Lista de voces disponibles con sus características
    """
    try:
        # Por ahora devolver lista estática de voces de Google
        # En el futuro podría consultar dinámicamente a Vertex AI

        voices = {
            "es-ES": [
                {
                    "name": "es-ES-Standard-A",
                    "gender": "FEMALE",
                    "description": "Voz femenina estándar en español",
                },
                {
                    "name": "es-ES-Standard-B",
                    "gender": "MALE",
                    "description": "Voz masculina estándar en español",
                },
                {
                    "name": "es-ES-Standard-C",
                    "gender": "MALE",
                    "description": "Voz masculina alternativa en español",
                },
                {
                    "name": "es-ES-Standard-D",
                    "gender": "FEMALE",
                    "description": "Voz femenina alternativa en español",
                },
                {
                    "name": "es-ES-Wavenet-B",
                    "gender": "MALE",
                    "description": "Voz masculina WaveNet de alta calidad",
                },
                {
                    "name": "es-ES-Wavenet-C",
                    "gender": "FEMALE",
                    "description": "Voz femenina WaveNet de alta calidad",
                },
            ],
            "en-US": [
                {
                    "name": "en-US-Standard-A",
                    "gender": "MALE",
                    "description": "Standard US English male voice",
                },
                {
                    "name": "en-US-Standard-C",
                    "gender": "FEMALE",
                    "description": "Standard US English female voice",
                },
                {
                    "name": "en-US-Wavenet-D",
                    "gender": "MALE",
                    "description": "WaveNet US English male voice",
                },
                {
                    "name": "en-US-Wavenet-F",
                    "gender": "FEMALE",
                    "description": "WaveNet US English female voice",
                },
            ],
        }

        return {
            "language_code": language_code,
            "voices": voices.get(language_code, []),
            "total": len(voices.get(language_code, [])),
        }

    except Exception as e:
        logger.error(f"Error listando voces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio-commands")
async def get_available_commands(
    current_user: UserPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Obtiene la lista de comandos de voz disponibles.

    Args:
        current_user: Usuario autenticado

    Returns:
        Lista de comandos disponibles con ejemplos
    """
    try:
        commands = {
            "workout_control": {
                "start_workout": {
                    "description": "Iniciar entrenamiento",
                    "examples": [
                        "Comienza el entrenamiento",
                        "Empezar",
                        "Vamos a entrenar",
                    ],
                },
                "pause_workout": {
                    "description": "Pausar entrenamiento",
                    "examples": ["Pausa", "Detener", "Para un momento"],
                },
                "resume_workout": {
                    "description": "Continuar entrenamiento",
                    "examples": ["Continuar", "Reanudar", "Seguir"],
                },
            },
            "exercise_navigation": {
                "next_exercise": {
                    "description": "Ir al siguiente ejercicio",
                    "examples": ["Siguiente ejercicio", "Próximo", "Adelante"],
                },
                "previous_exercise": {
                    "description": "Volver al ejercicio anterior",
                    "examples": ["Ejercicio anterior", "Atrás", "Previo"],
                },
                "repeat_exercise": {
                    "description": "Repetir ejercicio actual",
                    "examples": ["Repetir ejercicio", "Otra vez", "De nuevo"],
                },
            },
            "exercise_info": {
                "show_form": {
                    "description": "Mostrar técnica correcta",
                    "examples": ["Muéstrame la forma", "Cómo se hace", "Técnica"],
                },
                "rest_time": {
                    "description": "Consultar tiempo de descanso",
                    "examples": ["Cuánto descanso", "Tiempo de descanso", "Break"],
                },
            },
            "progress": {
                "set_complete": {
                    "description": "Marcar serie como completada",
                    "examples": ["Serie completa", "Terminé", "Listo"],
                },
                "workout_status": {
                    "description": "Ver progreso actual",
                    "examples": ["Cómo voy", "Mi progreso", "Estado"],
                },
            },
            "help": {
                "help": {
                    "description": "Obtener ayuda",
                    "examples": ["Ayuda", "Qué comandos hay", "Qué puedo decir"],
                }
            },
        }

        return {
            "commands": commands,
            "total_commands": sum(len(category) for category in commands.values()),
            "categories": list(commands.keys()),
        }

    except Exception as e:
        logger.error(f"Error obteniendo comandos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Incluir el router en la aplicación principal
def include_router(app):
    """Incluye este router en la aplicación FastAPI principal."""
    app.include_router(router)
