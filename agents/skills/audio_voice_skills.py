"""
Skills especializadas para procesamiento de audio y voz en NGX Agents.

Este módulo contiene skills que permiten a los agentes:
- Procesar comandos de voz para entrenamientos
- Sintetizar respuestas de audio
- Analizar el tono emocional del usuario
- Proporcionar feedback verbal durante ejercicios
"""

from typing import Dict, Any, List, Optional, Union
import asyncio
from datetime import datetime
import json
import re

from core.skill import Skill
from core.logging_config import get_logger
from infrastructure.adapters.speech_adapter import speech_adapter

logger = get_logger(__name__)


class VoiceCommandSkill(Skill):
    """
    Skill para procesar comandos de voz durante entrenamientos.

    Permite a los usuarios controlar sus sesiones de entrenamiento mediante
    comandos de voz como "siguiente ejercicio", "pausar", "repetir", etc.
    """

    def __init__(self):
        super().__init__(
            name="Voice Command Processing",
            description="Procesa comandos de voz para controlar entrenamientos",
        )

        # Definir comandos reconocidos y sus intenciones
        self.command_patterns = {
            "start_workout": [
                r"comien[zc]a.*entrenamiento",
                r"empie[zc]a.*entrenamiento",
                r"inicia.*entrenamiento",
                r"vamos.*entrenar",
                r"start.*workout",
            ],
            "next_exercise": [
                r"siguiente.*ejercicio",
                r"próximo.*ejercicio",
                r"next.*exercise",
                r"continuar",
                r"adelante",
            ],
            "previous_exercise": [
                r"anterior.*ejercicio",
                r"ejercicio.*anterior",
                r"atrás",
                r"previo",
                r"previous",
            ],
            "pause_workout": [r"paus[ae]", r"detener", r"parar", r"stop", r"espera"],
            "resume_workout": [
                r"continua[r]?",
                r"reanudar",
                r"seguir",
                r"resume",
                r"vamos",
            ],
            "repeat_exercise": [
                r"repet[ie].*ejercicio",
                r"otra.*vez",
                r"de.*nuevo",
                r"repeat",
                r"again",
            ],
            "show_form": [
                r"muestra.*forma",
                r"cómo.*hace",
                r"técnica",
                r"form",
                r"postura",
            ],
            "rest_time": [
                r"cuánto.*descanso",
                r"tiempo.*descanso",
                r"rest.*time",
                r"break",
            ],
            "set_complete": [
                r"serie.*completa",
                r"terminé.*serie",
                r"listo",
                r"done",
                r"completado",
            ],
            "workout_status": [
                r"cómo.*voy",
                r"progreso",
                r"estado",
                r"status",
                r"dónde.*estoy",
            ],
            "help": [r"ayuda", r"comandos", r"qué.*puedo.*decir", r"help", r"opciones"],
        }

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un comando de voz y devuelve la acción correspondiente.

        Args:
            context: Debe contener:
                - audio_data: Datos del audio (base64, URL o path)
                - language_code: Código de idioma (default: "es-ES")
                - workout_state: Estado actual del entrenamiento (opcional)

        Returns:
            Dict con:
                - command: Comando identificado
                - action: Acción a ejecutar
                - confidence: Nivel de confianza
                - transcription: Texto transcrito
                - parameters: Parámetros adicionales extraídos
        """
        try:
            audio_data = context.get("audio_data")
            if not audio_data:
                return {
                    "error": "No se proporcionaron datos de audio",
                    "status": "error",
                }

            language_code = context.get("language_code", "es-ES")
            workout_state = context.get("workout_state", {})

            # Transcribir el audio
            logger.info("Transcribiendo comando de voz...")
            transcription_result = await speech_adapter.transcribe_audio(
                audio_data=audio_data,
                language_code=language_code,
                agent_id="voice_command_skill",
            )

            if transcription_result.get("status") != "success":
                return {
                    "error": f"Error en transcripción: {transcription_result.get('error')}",
                    "status": "error",
                }

            transcribed_text = transcription_result.get("text", "").lower()
            logger.info(f"Texto transcrito: {transcribed_text}")

            # Identificar el comando
            identified_command = None
            max_confidence = 0.0

            for command, patterns in self.command_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, transcribed_text, re.IGNORECASE):
                        # Calcular confianza basada en la longitud del match
                        match = re.search(pattern, transcribed_text, re.IGNORECASE)
                        confidence = len(match.group()) / len(transcribed_text)

                        if confidence > max_confidence:
                            max_confidence = confidence
                            identified_command = command

            # Si no se identificó ningún comando con suficiente confianza
            if not identified_command or max_confidence < 0.3:
                return {
                    "command": "unknown",
                    "action": "clarify",
                    "confidence": max_confidence,
                    "transcription": transcribed_text,
                    "message": "No entendí el comando. ¿Puedes repetirlo?",
                    "available_commands": list(self.command_patterns.keys()),
                    "status": "success",
                }

            # Generar acción basada en el comando y el estado actual
            action_result = self._generate_action(
                identified_command, workout_state, transcribed_text
            )

            return {
                "command": identified_command,
                "action": action_result["action"],
                "confidence": max_confidence,
                "transcription": transcribed_text,
                "parameters": action_result.get("parameters", {}),
                "message": action_result.get("message", ""),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error procesando comando de voz: {e}")
            return {"error": str(e), "status": "error"}

    def _generate_action(
        self, command: str, workout_state: Dict[str, Any], text: str
    ) -> Dict[str, Any]:
        """Genera la acción apropiada basada en el comando y estado actual."""

        actions = {
            "start_workout": {
                "action": "start_workout",
                "message": "Iniciando entrenamiento. ¡Vamos a comenzar!",
                "parameters": {"timestamp": datetime.now().isoformat()},
            },
            "next_exercise": {
                "action": "navigate_exercise",
                "message": "Pasando al siguiente ejercicio",
                "parameters": {"direction": "next"},
            },
            "previous_exercise": {
                "action": "navigate_exercise",
                "message": "Volviendo al ejercicio anterior",
                "parameters": {"direction": "previous"},
            },
            "pause_workout": {
                "action": "pause",
                "message": "Entrenamiento pausado",
                "parameters": {"timestamp": datetime.now().isoformat()},
            },
            "resume_workout": {
                "action": "resume",
                "message": "Continuando con el entrenamiento",
                "parameters": {"timestamp": datetime.now().isoformat()},
            },
            "repeat_exercise": {
                "action": "repeat_current",
                "message": "Repitiendo el ejercicio actual",
                "parameters": {},
            },
            "show_form": {
                "action": "display_form_guide",
                "message": "Mostrando guía de forma correcta",
                "parameters": {"exercise": workout_state.get("current_exercise", "")},
            },
            "rest_time": {
                "action": "show_rest_timer",
                "message": f"Tiempo de descanso: {workout_state.get('rest_seconds', 60)} segundos",
                "parameters": {"duration": workout_state.get("rest_seconds", 60)},
            },
            "set_complete": {
                "action": "mark_set_complete",
                "message": "Serie marcada como completada",
                "parameters": {
                    "set_number": workout_state.get("current_set", 1),
                    "timestamp": datetime.now().isoformat(),
                },
            },
            "workout_status": {
                "action": "show_progress",
                "message": self._generate_progress_message(workout_state),
                "parameters": {"detailed": True},
            },
            "help": {
                "action": "show_help",
                "message": "Comandos disponibles: iniciar, siguiente, anterior, pausar, continuar, repetir, forma, descanso, completado, progreso",
                "parameters": {"commands": list(self.command_patterns.keys())},
            },
        }

        return actions.get(
            command,
            {"action": "unknown", "message": "Comando no reconocido", "parameters": {}},
        )

    def _generate_progress_message(self, workout_state: Dict[str, Any]) -> str:
        """Genera un mensaje de progreso basado en el estado del entrenamiento."""
        current_exercise = workout_state.get("current_exercise_index", 0)
        total_exercises = workout_state.get("total_exercises", 0)
        current_set = workout_state.get("current_set", 0)
        total_sets = workout_state.get("total_sets", 0)

        if total_exercises > 0:
            progress_percent = (current_exercise / total_exercises) * 100
            return f"Ejercicio {current_exercise + 1} de {total_exercises} ({progress_percent:.0f}% completado). Serie {current_set} de {total_sets}."
        else:
            return "No hay información de progreso disponible"


class AudioFeedbackSkill(Skill):
    """
    Skill para proporcionar feedback de audio durante entrenamientos.

    Genera respuestas de voz para guiar, motivar y corregir al usuario
    durante sus ejercicios.
    """

    def __init__(self):
        super().__init__(
            name="Audio Feedback Generation",
            description="Genera feedback de audio personalizado durante entrenamientos",
        )

        # Templates de feedback por categoría
        self.feedback_templates = {
            "encouragement": [
                "¡Excelente trabajo! Sigue así.",
                "¡Muy bien! Mantén ese ritmo.",
                "¡Perfecto! Tu forma es impecable.",
                "¡Increíble esfuerzo! No te detengas.",
                "¡Así se hace campeón!",
            ],
            "form_correction": [
                "Recuerda mantener la espalda recta.",
                "Intenta bajar un poco más en el movimiento.",
                "Mantén los codos cerca del cuerpo.",
                "No olvides respirar durante el ejercicio.",
                "Controla el movimiento, no uses impulso.",
            ],
            "rest_reminder": [
                "Es momento de descansar. Hidrátate bien.",
                "Tómate {} segundos de descanso. Lo has ganado.",
                "Descansa {} segundos. Prepárate para la siguiente serie.",
                "Aprovecha para recuperar el aliento.",
                "Buen trabajo. Ahora descansa un momento.",
            ],
            "set_completion": [
                "¡Serie completada! Excelente ejecución.",
                "¡Terminaste la serie! Cada vez más fuerte.",
                "¡Serie lista! Tu progreso es notable.",
                "¡Completado! Sigue mejorando así.",
                "¡Perfecto! Una serie menos, una victoria más.",
            ],
            "workout_start": [
                "¡Bienvenido a tu entrenamiento! Vamos a darlo todo.",
                "¡Es hora de entrenar! Prepárate para superar tus límites.",
                "¡Comencemos! Hoy será un gran día de entrenamiento.",
                "¡Listo para empezar! Recuerda calentar primero.",
                "¡A entrenar! Tu cuerpo te lo agradecerá.",
            ],
            "workout_end": [
                "¡Entrenamiento completado! Has hecho un trabajo increíble.",
                "¡Felicidades! Has terminado tu sesión de hoy.",
                "¡Excelente trabajo! No olvides estirar.",
                "¡Lo lograste! Cada día eres más fuerte.",
                "¡Sesión finalizada! Descansa, te lo has ganado.",
            ],
        }

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera y sintetiza feedback de audio.

        Args:
            context: Debe contener:
                - feedback_type: Tipo de feedback (encouragement, form_correction, etc.)
                - parameters: Parámetros adicionales (ej: rest_seconds)
                - voice_settings: Configuración de voz (opcional)
                - user_profile: Perfil del usuario para personalización (opcional)

        Returns:
            Dict con:
                - audio_base64: Audio sintetizado en base64
                - text: Texto del feedback
                - duration_estimate: Duración estimada del audio
                - voice_used: Voz utilizada
        """
        try:
            feedback_type = context.get("feedback_type", "encouragement")
            parameters = context.get("parameters", {})
            voice_settings = context.get("voice_settings", {})
            user_profile = context.get("user_profile", {})

            # Seleccionar o generar el texto del feedback
            feedback_text = self._generate_feedback_text(
                feedback_type, parameters, user_profile
            )

            # Configurar voz basada en preferencias del usuario
            voice_name = voice_settings.get(
                "voice_name", "es-ES-Standard-B"
            )  # Voz masculina por defecto
            language_code = voice_settings.get("language_code", "es-ES")

            # Ajustar el texto para mejor pronunciación
            adjusted_text = self._adjust_text_for_speech(feedback_text)

            # Sintetizar el audio
            logger.info(f"Sintetizando feedback: {feedback_type}")
            synthesis_result = await speech_adapter.synthesize_speech(
                text=adjusted_text,
                voice_name=voice_name,
                language_code=language_code,
                agent_id="audio_feedback_skill",
            )

            if synthesis_result.get("status") != "success":
                return {
                    "error": f"Error en síntesis: {synthesis_result.get('error')}",
                    "status": "error",
                }

            # Estimar duración basada en la longitud del texto
            # Aproximadamente 150 palabras por minuto
            word_count = len(feedback_text.split())
            duration_estimate = (word_count / 150) * 60  # en segundos

            return {
                "audio_base64": synthesis_result.get("audio_base64"),
                "text": feedback_text,
                "duration_estimate": round(duration_estimate, 1),
                "voice_used": voice_name,
                "language": language_code,
                "feedback_type": feedback_type,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error generando feedback de audio: {e}")
            return {"error": str(e), "status": "error"}

    def _generate_feedback_text(
        self,
        feedback_type: str,
        parameters: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> str:
        """Genera el texto del feedback basado en el tipo y contexto."""

        # Obtener templates para el tipo de feedback
        templates = self.feedback_templates.get(feedback_type, ["Buen trabajo."])

        # Seleccionar template (podría ser más sofisticado con ML)
        import random

        template = random.choice(templates)

        # Aplicar parámetros al template
        if "{}" in template and parameters:
            # Para rest_reminder, insertar segundos de descanso
            if feedback_type == "rest_reminder" and "rest_seconds" in parameters:
                template = template.format(parameters["rest_seconds"])

        # Personalizar basado en el perfil del usuario
        if user_profile:
            name = user_profile.get("name")
            if name and random.random() < 0.3:  # 30% de probabilidad de usar el nombre
                template = f"{name}, {template.lower()}"

        return template

    def _adjust_text_for_speech(self, text: str) -> str:
        """Ajusta el texto para mejor pronunciación en síntesis de voz."""

        # Reemplazar números por palabras cuando sea apropiado
        replacements = {
            r"\b1\b": "uno",
            r"\b2\b": "dos",
            r"\b3\b": "tres",
            r"\b4\b": "cuatro",
            r"\b5\b": "cinco",
            r"\b10\b": "diez",
            r"\b15\b": "quince",
            r"\b20\b": "veinte",
            r"\b30\b": "treinta",
            r"\b45\b": "cuarenta y cinco",
            r"\b60\b": "sesenta",
            r"\b90\b": "noventa",
        }

        adjusted = text
        for pattern, replacement in replacements.items():
            adjusted = re.sub(pattern, replacement, adjusted)

        # Agregar pausas para mejor ritmo
        adjusted = adjusted.replace(". ", '. <break time="0.5s"/> ')
        adjusted = adjusted.replace("! ", '! <break time="0.5s"/> ')
        adjusted = adjusted.replace(", ", ', <break time="0.3s"/> ')

        return adjusted


class VoiceEmotionAnalysisSkill(Skill):
    """
    Skill para analizar el tono emocional y el estado del usuario a través de su voz.

    Detecta fatiga, frustración, motivación y otros estados emocionales
    para ajustar el entrenamiento y el feedback.
    """

    def __init__(self):
        super().__init__(
            name="Voice Emotion Analysis",
            description="Analiza el estado emocional del usuario a través de su voz",
        )

        # Umbrales para diferentes estados
        self.emotion_thresholds = {
            "fatigue": {
                "energy_level": 0.3,
                "speech_rate": 0.7,
                "indicators": ["cansado", "agotado", "no puedo", "difícil"],
            },
            "frustration": {
                "stress_level": 0.7,
                "negative_sentiment": 0.6,
                "indicators": ["no sale", "imposible", "mal", "error"],
            },
            "motivation": {
                "energy_level": 0.7,
                "positive_sentiment": 0.7,
                "indicators": ["vamos", "puedo", "bien", "genial", "sí"],
            },
            "pain": {
                "stress_level": 0.8,
                "pitch_variation": 0.8,
                "indicators": ["duele", "dolor", "ay", "auch"],
            },
        }

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza el estado emocional del usuario a través de su voz.

        Args:
            context: Debe contener:
                - audio_data: Datos del audio a analizar
                - analysis_depth: Nivel de profundidad del análisis (basic/detailed)
                - previous_state: Estado emocional previo (opcional)

        Returns:
            Dict con:
                - emotional_state: Estado emocional principal detectado
                - confidence: Nivel de confianza en la detección
                - emotions: Diccionario con puntuaciones para cada emoción
                - recommendations: Recomendaciones basadas en el estado
                - indicators: Indicadores específicos detectados
        """
        try:
            audio_data = context.get("audio_data")
            if not audio_data:
                return {
                    "error": "No se proporcionaron datos de audio",
                    "status": "error",
                }

            analysis_depth = context.get("analysis_depth", "detailed")
            previous_state = context.get("previous_state", {})

            # Realizar análisis de audio con el speech adapter
            logger.info("Analizando emociones en el audio...")
            analysis_result = await speech_adapter.analyze_audio(
                audio_data=audio_data,
                analysis_type="emotion",
                language_code="es-ES",
                agent_id="voice_emotion_skill",
            )

            if analysis_result.get("status") != "success":
                return {
                    "error": f"Error en análisis: {analysis_result.get('error')}",
                    "status": "error",
                }

            # Extraer información del análisis
            transcription = analysis_result.get("transcription", "")
            raw_emotions = analysis_result.get("analysis", {})

            # Analizar indicadores en el texto
            detected_indicators = self._detect_indicators(transcription)

            # Combinar análisis de voz con indicadores textuales
            emotional_assessment = self._assess_emotional_state(
                raw_emotions, detected_indicators, transcription
            )

            # Generar recomendaciones basadas en el estado
            recommendations = self._generate_recommendations(
                emotional_assessment, previous_state
            )

            # Determinar si se necesita intervención
            needs_intervention = self._check_intervention_needed(
                emotional_assessment, previous_state
            )

            return {
                "emotional_state": emotional_assessment["primary_state"],
                "confidence": emotional_assessment["confidence"],
                "emotions": emotional_assessment["emotion_scores"],
                "physical_indicators": {
                    "fatigue_level": emotional_assessment.get("fatigue_level", 0.0),
                    "stress_level": emotional_assessment.get("stress_level", 0.0),
                    "energy_level": emotional_assessment.get("energy_level", 0.5),
                    "pain_indicators": emotional_assessment.get("pain_level", 0.0),
                },
                "recommendations": recommendations,
                "indicators": detected_indicators,
                "transcription": transcription,
                "needs_intervention": needs_intervention,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error en análisis de emociones: {e}")
            return {"error": str(e), "status": "error"}

    def _detect_indicators(self, text: str) -> Dict[str, List[str]]:
        """Detecta indicadores emocionales en el texto transcrito."""
        detected = {"fatigue": [], "frustration": [], "motivation": [], "pain": []}

        text_lower = text.lower()

        for state, config in self.emotion_thresholds.items():
            indicators = config.get("indicators", [])
            for indicator in indicators:
                if indicator in text_lower:
                    detected[state].append(indicator)

        return detected

    def _assess_emotional_state(
        self, raw_emotions: Dict[str, Any], indicators: Dict[str, List[str]], text: str
    ) -> Dict[str, Any]:
        """Evalúa el estado emocional combinando análisis de voz e indicadores."""

        # Extraer puntuaciones de emociones básicas
        emotion_scores = (
            raw_emotions.get("scores", {}) if isinstance(raw_emotions, dict) else {}
        )

        # Calcular niveles derivados
        fatigue_level = self._calculate_fatigue_level(
            emotion_scores, indicators["fatigue"]
        )
        stress_level = self._calculate_stress_level(
            emotion_scores, indicators["frustration"], indicators["pain"]
        )
        energy_level = 1.0 - fatigue_level  # Inversamente proporcional a la fatiga
        motivation_level = self._calculate_motivation_level(
            emotion_scores, indicators["motivation"]
        )
        pain_level = self._calculate_pain_level(indicators["pain"], text)

        # Determinar estado principal
        states = {
            "fatigued": fatigue_level,
            "frustrated": stress_level * 0.8,  # Ajustar peso
            "motivated": motivation_level,
            "in_pain": pain_level,
            "neutral": 0.5,  # Estado base
        }

        primary_state = max(states.items(), key=lambda x: x[1])[0]
        confidence = states[primary_state]

        return {
            "primary_state": primary_state,
            "confidence": confidence,
            "emotion_scores": emotion_scores,
            "fatigue_level": fatigue_level,
            "stress_level": stress_level,
            "energy_level": energy_level,
            "motivation_level": motivation_level,
            "pain_level": pain_level,
        }

    def _calculate_fatigue_level(
        self, emotions: Dict[str, float], fatigue_indicators: List[str]
    ) -> float:
        """Calcula el nivel de fatiga basado en emociones e indicadores."""
        # Base score from emotions
        base_score = (
            emotions.get("tristeza", 0.0) * 0.3 + emotions.get("neutral", 0.0) * 0.2
        )

        # Boost based on indicators
        indicator_boost = min(len(fatigue_indicators) * 0.2, 0.6)

        return min(base_score + indicator_boost, 1.0)

    def _calculate_stress_level(
        self,
        emotions: Dict[str, float],
        frustration_indicators: List[str],
        pain_indicators: List[str],
    ) -> float:
        """Calcula el nivel de estrés/frustración."""
        # Base score from emotions
        base_score = emotions.get("enojo", 0.0) * 0.4 + emotions.get("miedo", 0.0) * 0.3

        # Boost based on indicators
        frustration_boost = min(len(frustration_indicators) * 0.15, 0.4)
        pain_boost = min(len(pain_indicators) * 0.1, 0.2)

        return min(base_score + frustration_boost + pain_boost, 1.0)

    def _calculate_motivation_level(
        self, emotions: Dict[str, float], motivation_indicators: List[str]
    ) -> float:
        """Calcula el nivel de motivación."""
        # Base score from emotions
        base_score = (
            emotions.get("alegría", 0.0) * 0.5 + emotions.get("sorpresa", 0.0) * 0.2
        )

        # Boost based on indicators
        indicator_boost = min(len(motivation_indicators) * 0.2, 0.5)

        return min(base_score + indicator_boost, 1.0)

    def _calculate_pain_level(self, pain_indicators: List[str], text: str) -> float:
        """Calcula el nivel de dolor detectado."""
        # Base score from indicators
        base_score = min(len(pain_indicators) * 0.3, 0.7)

        # Check for intensity words
        intensity_words = ["mucho", "bastante", "demasiado", "horrible", "terrible"]
        intensity_boost = 0.0

        text_lower = text.lower()
        for word in intensity_words:
            if word in text_lower:
                intensity_boost = 0.3
                break

        return min(base_score + intensity_boost, 1.0)

    def _generate_recommendations(
        self, emotional_state: Dict[str, Any], previous_state: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Genera recomendaciones basadas en el estado emocional."""
        recommendations = []
        primary_state = emotional_state["primary_state"]

        if primary_state == "fatigued":
            if emotional_state["fatigue_level"] > 0.7:
                recommendations.append(
                    {
                        "type": "rest",
                        "priority": "high",
                        "message": "Nivel alto de fatiga detectado. Considera tomar un descanso más largo.",
                        "action": "extend_rest_time",
                    }
                )
            else:
                recommendations.append(
                    {
                        "type": "adjustment",
                        "priority": "medium",
                        "message": "Se detecta algo de fatiga. Reduce la intensidad del próximo ejercicio.",
                        "action": "reduce_intensity",
                    }
                )

        elif primary_state == "frustrated":
            recommendations.append(
                {
                    "type": "support",
                    "priority": "high",
                    "message": "Detectamos frustración. Vamos a ajustar el ejercicio o revisar la técnica.",
                    "action": "simplify_exercise",
                }
            )
            recommendations.append(
                {
                    "type": "motivation",
                    "priority": "medium",
                    "message": "Recuerda que cada repetición cuenta. ¡Lo estás haciendo genial!",
                    "action": "provide_encouragement",
                }
            )

        elif primary_state == "in_pain":
            recommendations.append(
                {
                    "type": "safety",
                    "priority": "critical",
                    "message": "Se detectó posible dolor. Detén el ejercicio y evalúa la situación.",
                    "action": "stop_exercise",
                }
            )
            recommendations.append(
                {
                    "type": "assessment",
                    "priority": "high",
                    "message": "Verifica tu forma y considera ejercicios alternativos.",
                    "action": "suggest_alternatives",
                }
            )

        elif primary_state == "motivated":
            if emotional_state["motivation_level"] > 0.8:
                recommendations.append(
                    {
                        "type": "challenge",
                        "priority": "medium",
                        "message": "¡Excelente energía! Podemos aumentar un poco la intensidad.",
                        "action": "increase_intensity",
                    }
                )

        return recommendations

    def _check_intervention_needed(
        self, current_state: Dict[str, Any], previous_state: Dict[str, Any]
    ) -> bool:
        """Determina si se necesita intervención inmediata."""

        # Intervención crítica por dolor
        if current_state.get("pain_level", 0) > 0.7:
            return True

        # Intervención por fatiga extrema
        if current_state.get("fatigue_level", 0) > 0.8:
            return True

        # Intervención por frustración alta persistente
        if (
            current_state.get("stress_level", 0) > 0.7
            and previous_state.get("stress_level", 0) > 0.6
        ):
            return True

        return False


class WorkoutVoiceGuideSkill(Skill):
    """
    Skill para proporcionar guía verbal completa durante los entrenamientos.

    Combina narración de ejercicios, conteo de repeticiones, recordatorios
    de forma y motivación continua.
    """

    def __init__(self):
        super().__init__(
            name="Workout Voice Guide",
            description="Proporciona guía verbal completa durante entrenamientos",
        )

        # Templates para diferentes momentos del ejercicio
        self.exercise_phases = {
            "introduction": "Vamos con {exercise_name}. {sets} series de {reps} repeticiones.",
            "setup": "Posición inicial: {setup_instructions}",
            "execution": "Recuerda: {key_points}",
            "breathing": "Inhala en {inhale_phase}, exhala en {exhale_phase}",
            "counting": {
                "start": "Comenzamos. ",
                "rep": "{count}... ",
                "halfway": "Vas a la mitad, sigue así. ",
                "almost": "Últimas {remaining}, dale con todo. ",
                "complete": "¡Excelente! Serie completada.",
            },
        }

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera guía de voz para un ejercicio completo.

        Args:
            context: Debe contener:
                - exercise: Información del ejercicio
                - phase: Fase actual del ejercicio
                - rep_count: Número de repetición actual (si aplica)
                - voice_settings: Configuración de voz

        Returns:
            Dict con:
                - audio_base64: Audio de la guía
                - text: Texto de la guía
                - duration: Duración del audio
                - next_cue_timing: Cuándo reproducir el siguiente audio
        """
        try:
            exercise = context.get("exercise", {})
            phase = context.get("phase", "introduction")
            rep_count = context.get("rep_count", 0)
            voice_settings = context.get("voice_settings", {})

            # Generar el texto de guía según la fase
            guide_text = self._generate_phase_guide(exercise, phase, rep_count)

            # Configurar voz para guía de ejercicios (clara y enérgica)
            voice_name = voice_settings.get("voice_name", "es-ES-Standard-C")
            language_code = voice_settings.get("language_code", "es-ES")

            # Sintetizar el audio
            logger.info(f"Generando guía de voz para fase: {phase}")
            synthesis_result = await speech_adapter.synthesize_speech(
                text=guide_text,
                voice_name=voice_name,
                language_code=language_code,
                agent_id="workout_voice_guide",
            )

            if synthesis_result.get("status") != "success":
                return {
                    "error": f"Error en síntesis: {synthesis_result.get('error')}",
                    "status": "error",
                }

            # Calcular timing para el siguiente cue
            next_cue_timing = self._calculate_next_cue_timing(phase, exercise)

            return {
                "audio_base64": synthesis_result.get("audio_base64"),
                "text": guide_text,
                "duration": synthesis_result.get("duration_estimate", 3.0),
                "phase": phase,
                "next_cue_timing": next_cue_timing,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error generando guía de voz: {e}")
            return {"error": str(e), "status": "error"}

    def _generate_phase_guide(
        self, exercise: Dict[str, Any], phase: str, rep_count: int
    ) -> str:
        """Genera el texto de guía para cada fase del ejercicio."""

        if phase == "introduction":
            return self.exercise_phases["introduction"].format(
                exercise_name=exercise.get("name", "el ejercicio"),
                sets=exercise.get("sets", 3),
                reps=exercise.get("reps", 10),
            )

        elif phase == "setup":
            setup_instructions = exercise.get(
                "setup_instructions", "Adopta la posición inicial correcta"
            )
            return self.exercise_phases["setup"].format(
                setup_instructions=setup_instructions
            )

        elif phase == "execution":
            key_points = exercise.get(
                "key_points", "Mantén la forma correcta durante todo el movimiento"
            )
            return self.exercise_phases["execution"].format(key_points=key_points)

        elif phase == "breathing":
            return self.exercise_phases["breathing"].format(
                inhale_phase=exercise.get("inhale_phase", "la fase negativa"),
                exhale_phase=exercise.get("exhale_phase", "la fase positiva"),
            )

        elif phase == "counting":
            total_reps = exercise.get("reps", 10)
            counting = self.exercise_phases["counting"]

            if rep_count == 0:
                return counting["start"]
            elif rep_count == total_reps:
                return counting["complete"]
            elif rep_count == total_reps // 2:
                return counting["halfway"] + f"{rep_count}... "
            elif rep_count >= total_reps - 3:
                return (
                    counting["almost"].format(remaining=total_reps - rep_count + 1)
                    + f"{rep_count}... "
                )
            else:
                return f"{rep_count}... "

        else:
            return "Continúa con el ejercicio."

    def _calculate_next_cue_timing(self, phase: str, exercise: Dict[str, Any]) -> float:
        """Calcula cuándo debe reproducirse el siguiente audio cue."""

        # Timings base por fase (en segundos)
        base_timings = {
            "introduction": 5.0,
            "setup": 4.0,
            "execution": 3.0,
            "breathing": 3.0,
            "counting": exercise.get("rep_duration", 2.0),  # Tiempo por repetición
        }

        return base_timings.get(phase, 3.0)


# Registro de todas las skills de audio/voz
AUDIO_VOICE_SKILLS = {
    "voice_command": VoiceCommandSkill(),
    "audio_feedback": AudioFeedbackSkill(),
    "voice_emotion_analysis": VoiceEmotionAnalysisSkill(),
    "workout_voice_guide": WorkoutVoiceGuideSkill(),
}
