import logging
import uuid
import time
from typing import Dict, Any, Optional, List

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager

# Configurar logging
logger = logging.getLogger(__name__)


class RecoveryCorrective(A2AAgent):
    """
    Agente Recovery & Corrective Specialist compatible con A2A
    
    Prevención / rehab, movilidad, sueño, protocolos de HRV & dolor crónico.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "injury_prevention",
            "rehabilitation",
            "mobility_assessment",
            "sleep_optimization",
            "hrv_protocols",
            "chronic_pain_management"
        ]
        
        skills = [
            {
                "name": "injury_prevention",
                "description": "Prevención de lesiones mediante ejercicios y prácticas específicas"
            },
            {
                "name": "rehabilitation",
                "description": "Rehabilitación de lesiones y recuperación funcional"
            },
            {
                "name": "mobility_assessment",
                "description": "Evaluación y mejora de la movilidad articular y muscular"
            },
            {
                "name": "sleep_optimization",
                "description": "Optimización de patrones de sueño para mejorar la recuperación"
            },
            {
                "name": "hrv_protocols",
                "description": "Protocolos basados en la variabilidad de la frecuencia cardíaca"
            },
            {
                "name": "chronic_pain_management",
                "description": "Manejo del dolor crónico mediante estrategias integradas"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Tengo dolor en la espalda baja después de entrenar"},
                "output": {"response": "He analizado tu dolor lumbar y te recomiendo un protocolo de recuperación específico..."}
            },
            {
                "input": {"message": "¿Cómo puedo mejorar mi movilidad de cadera?"},
                "output": {"response": "Para mejorar la movilidad de cadera, te recomiendo los siguientes ejercicios..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="recovery_corrective_specialist",
            name="Recovery & Corrective Specialist",
            description="Prevención / rehab, movilidad, sueño, protocolos de HRV & dolor crónico.",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.state_manager = StateManager(self.supabase_client)
        
        # Inicializar estado del agente
        self.update_state("recovery_protocols", {})  # Almacenar protocolos de recuperación generados
        self.update_state("pain_assessments", {})  # Almacenar evaluaciones de dolor
        
        logger.info(f"RecoveryCorrective inicializado con {len(capabilities)} capacidades")
    
    async def _get_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        try:
            # Intentar cargar el contexto desde el StateManager
            context = await self.state_manager.load_state(user_id, session_id)
            
            if not context or not context.get("state_data"):
                logger.info(f"No se encontró contexto en StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto.")
                # Si no hay contexto, crear uno nuevo
                context = {
                    "conversation_history": [],
                    "user_profile": {},
                    "pain_assessments": [],
                    "recovery_protocols": [],
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                # Si hay contexto, usar el state_data
                context = context.get("state_data", {})
                logger.info(f"Contexto cargado desde StateManager para user_id={user_id}, session_id={session_id}")
            
            return context
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "pain_assessments": [],
                "recovery_protocols": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el StateManager.
        
        Args:
            context: Contexto actualizado
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el StateManager
            await self.state_manager.save_state(context, user_id, session_id)
            logger.info(f"Contexto actualizado en StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)

    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                       session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente RecoveryCorrective.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en recuperación y corrección.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        try:
            start_time = time.time()
            logger.info(f"Ejecutando RecoveryCorrective con input: {input_text[:50]}...")
            
            # Generar ID de sesión si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generando nuevo session_id: {session_id}")
            
            # Obtener el contexto de la conversación
            context = await self._get_context(user_id, session_id) if user_id else {}
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                # Intentar obtener el perfil del usuario del contexto primero
                user_profile = context.get("user_profile", {})
                if not user_profile:
                    user_profile = self.supabase_client.get_user_profile(user_id)
                    if user_profile:
                        context["user_profile"] = user_profile
            
            # Determinar el tipo de solicitud basado en palabras clave
            if any(keyword in input_text.lower() for keyword in ["dolor", "molestia", "lesion", "lesión", "duele"]):
                # Generar evaluación de dolor
                pain_assessment = await self._generate_pain_assessment(input_text, user_profile)
                response = self._summarize_pain_assessment(pain_assessment)
                response_type = "pain_assessment"
                
                # Guardar la evaluación en el estado del agente
                if user_id:
                    # Guardar en el estado interno del agente
                    assessments = self.get_state("pain_assessments", {})
                    assessments[user_id] = assessments.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "assessment": pain_assessment
                    }]
                    self.update_state("pain_assessments", assessments)
                    
                    # Guardar en el contexto de StateManager
                    context["pain_assessments"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "assessment": pain_assessment
                    })
                    
                    # También guardar en Supabase si es necesario
                    self.supabase_client.save_pain_assessment(user_id, pain_assessment)
                
            elif any(keyword in input_text.lower() for keyword in ["recuperación", "rehabilitación", "protocolo", "movilidad", "ejercicio"]):
                # Generar protocolo de recuperación
                recovery_protocol = await self._generate_recovery_protocol(input_text, user_profile)
                response = self._summarize_recovery_protocol(recovery_protocol)
                response_type = "recovery_protocol"
                
                # Guardar el protocolo en el estado del agente
                if user_id:
                    # Guardar en el estado interno del agente
                    protocols = self.get_state("recovery_protocols", {})
                    protocols[user_id] = protocols.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "protocol": recovery_protocol
                    }]
                    self.update_state("recovery_protocols", protocols)
                    
                    # Guardar en el contexto de StateManager
                    context["recovery_protocols"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "protocol": recovery_protocol
                    })
                    
                    # También guardar en Supabase si es necesario
                    self.supabase_client.save_recovery_protocol(user_id, recovery_protocol)
                
            else:
                # Preparar contexto para respuesta general
                prompt_context = self._prepare_context(input_text, user_profile, context)
                
                # Generar respuesta con Gemini
                response = await self.gemini_client.generate_content(prompt_context)
                response_type = "general_response"
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, response)
            
            # Añadir la interacción al historial de conversación en el contexto
            if user_id:
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "response_type": response_type
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Crear artefactos para la respuesta
            artifacts = [
                {
                    "type": response_type,
                    "content": response,
                    "metadata": {
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            ]
            
            # Devolver respuesta final
            return {
                "status": "success",
                "response": response,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "response_type": response_type,
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en RecoveryCorrective: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de recuperación.",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    def _summarize_pain_assessment(self, pain_assessment: Dict[str, Any]) -> str:
        """Genera un resumen textual de la evaluación de dolor para la respuesta al usuario."""
        summary_parts = []
        
        if "location" in pain_assessment:
            summary_parts.append(f"El dolor se localiza en {pain_assessment['location']}.")
        
        if "intensity" in pain_assessment:
            summary_parts.append(f"La intensidad es de {pain_assessment['intensity']} en una escala de 1-10.")
        
        if "recommendations" in pain_assessment and pain_assessment["recommendations"]:
            recommendations = pain_assessment["recommendations"]
            if isinstance(recommendations, list) and len(recommendations) > 0:
                summary_parts.append(f"Te recomiendo: {recommendations[0]}.")
            elif isinstance(recommendations, str):
                summary_parts.append(f"Te recomiendo: {recommendations}.")
        
        if "seek_medical_attention" in pain_assessment:
            summary_parts.append(f"Nota importante: {pain_assessment['seek_medical_attention']}.")
        
        if not summary_parts:
            return "Revisa la evaluación detallada para más información."
            
        return " ".join(summary_parts)
    
    def _summarize_recovery_protocol(self, recovery_protocol: Dict[str, Any]) -> str:
        """Genera un resumen textual del protocolo de recuperación para la respuesta al usuario."""
        summary_parts = []
        
        if "objective" in recovery_protocol:
            summary_parts.append(f"El objetivo principal es: {recovery_protocol['objective']}.")
        
        if "phases" in recovery_protocol and recovery_protocol["phases"]:
            phases = recovery_protocol["phases"]
            if isinstance(phases, list) and len(phases) > 0:
                phase = phases[0]
                summary_parts.append(f"Comenzaremos con la fase '{phase.get('name', 'inicial')}' que dura {phase.get('duration', 'un periodo')} y se enfoca en {phase.get('focus', 'recuperación')}.")
        
        if "complementary_strategies" in recovery_protocol:
            strategies = recovery_protocol["complementary_strategies"]
            if isinstance(strategies, dict) and "sleep" in strategies:
                summary_parts.append(f"Para el sueño: {strategies['sleep']}.")
        
        if not summary_parts:
            return "Revisa el protocolo detallado para más información."
            
        return " ".join(summary_parts)
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
    
    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.
        
        Args:
            task: Tarea a ejecutar
            
        Returns:
            Any: Resultado de la tarea
        """
        try:
            user_input = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id")
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)
            
            # Preparar contexto para la generación de respuesta
            prompt_context = self._prepare_context(user_input, user_profile, context)
            
            # Generar respuesta
            response = await self.gemini_client.generate_response(
                user_input, 
                context=prompt_context,
                temperature=0.7
            )
            
            # Crear artefactos si es necesario (por ejemplo, un protocolo de recuperación)
            artifacts = []
            if any(keyword in user_input.lower() for keyword in ["protocolo", "recuperación", "rehabilitación", "ejercicio", "movilidad"]):
                # Crear un artefacto de protocolo de recuperación
                recovery_protocol = await self._generate_recovery_protocol(user_input, user_profile)
                
                artifact_id = f"recovery_protocol_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="recovery_protocol",
                    parts=[
                        self.create_data_part(recovery_protocol)
                    ]
                )
                artifacts.append(artifact)
            
            # Si se menciona dolor o lesiones, crear un artefacto de evaluación
            if any(keyword in user_input.lower() for keyword in ["dolor", "lesión", "molestia", "inflamación"]):
                pain_assessment = await self._generate_pain_assessment(user_input, user_profile)
                
                artifact_id = f"pain_assessment_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="pain_assessment",
                    parts=[
                        self.create_data_part(pain_assessment)
                    ]
                )
                artifacts.append(artifact)
            
            # Registrar la interacción
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id="recovery_corrective_specialist",
                    message=user_input,
                    response=response
                )
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            # Devolver respuesta estructurada según el protocolo A2A
            return {
                "response": response,
                "message": response_message,
                "artifacts": artifacts
            }
            
        except Exception as e:
            logger.error(f"Error en Recovery & Corrective Specialist: {e}")
            return {
                "error": str(e), 
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de recuperación."
            }
    
    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente.
        
        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje
            
        Returns:
            Any: Respuesta al mensaje
        """
        try:
            # Extraer información del mensaje
            message_text = content.get("text", "")
            context = content.get("context", {})
            
            # Generar respuesta basada en el contenido del mensaje
            prompt = f"""
            Has recibido un mensaje del agente {from_agent}:
            
            "{message_text}"
            
            Responde con información relevante sobre recuperación y corrección relacionada con este mensaje.
            """
            
            response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            return {
                "status": "success",
                "response": response,
                "message": response_message
            }
        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente: {e}")
            return {"error": str(e)}
    
    def _prepare_context(self, user_input: str, user_profile: Optional[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        Prepara el contexto para la generación de respuesta.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            context: Contexto adicional
            
        Returns:
            str: Contexto preparado para la generación de respuesta
        """
        prompt_context = """
        Eres el Recovery & Corrective Specialist de NGX, un experto en prevención, rehabilitación, 
        movilidad, sueño y protocolos para HRV y dolor crónico.
        
        Debes proporcionar recomendaciones basadas en evidencia científica para optimizar la recuperación
        y prevenir lesiones, personalizadas para el usuario.
        Tus respuestas deben ser claras, concisas y accionables.
        """
        
        # Añadir información del perfil del usuario si está disponible
        if user_profile:
            prompt_context += f"""
            
            Información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Historial de lesiones: {user_profile.get('injury_history', 'N/A')}
            - Calidad de sueño: {user_profile.get('sleep_quality', 'N/A')}
            - Nivel de estrés: {user_profile.get('stress_level', 'N/A')}
            - Áreas de dolor: {user_profile.get('pain_areas', 'N/A')}
            """
        
        # Añadir contexto adicional si está disponible
        if context:
            additional_context = "\n".join([f"- {key}: {value}" for key, value in context.items() 
                                           if key not in ["user_id", "session_id"]])
            if additional_context:
                prompt_context += f"""
                
                Contexto adicional:
                {additional_context}
                """
        
        return prompt_context
    
    async def _generate_recovery_protocol(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un protocolo de recuperación estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Protocolo de recuperación estructurado
        """
        prompt = f"""
        Genera un protocolo de recuperación estructurado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El protocolo debe incluir:
        1. Objetivo principal de recuperación
        2. Duración estimada del protocolo
        3. Fases de recuperación
        4. Ejercicios específicos con series, repeticiones y progresión
        5. Estrategias complementarias (sueño, nutrición, manejo del estrés)
        6. Métricas de seguimiento
        7. Señales de alerta para buscar ayuda profesional
        
        Devuelve el protocolo en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Historial de lesiones: {user_profile.get('injury_history', 'N/A')}
            - Calidad de sueño: {user_profile.get('sleep_quality', 'N/A')}
            - Nivel de estrés: {user_profile.get('stress_level', 'N/A')}
            - Áreas de dolor: {user_profile.get('pain_areas', 'N/A')}
            """
        
        # Generar el protocolo de recuperación
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "objective": "Protocolo de recuperación personalizado",
                    "duration": "4-6 semanas",
                    "phases": [
                        {
                            "name": "Fase inicial",
                            "duration": "1-2 semanas",
                            "focus": "Reducir dolor e inflamación"
                        },
                        {
                            "name": "Fase intermedia",
                            "duration": "2-3 semanas",
                            "focus": "Recuperar movilidad y estabilidad"
                        },
                        {
                            "name": "Fase final",
                            "duration": "1-2 semanas",
                            "focus": "Fortalecimiento y retorno a la actividad"
                        }
                    ],
                    "exercises": [
                        {
                            "name": "Ejemplo de ejercicio",
                            "sets": 3,
                            "reps": "8-12",
                            "frequency": "Diario"
                        }
                    ],
                    "complementary_strategies": {
                        "sleep": "Priorizar 7-9 horas de sueño reparador",
                        "nutrition": "Enfocarse en alimentos antiinflamatorios",
                        "stress": "Practicar técnicas de relajación diariamente"
                    }
                }
        
        return response
    
    async def _generate_pain_assessment(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera una evaluación de dolor estructurada.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Evaluación de dolor estructurada
        """
        prompt = f"""
        Genera una evaluación de dolor estructurada basada en la siguiente solicitud:
        
        "{user_input}"
        
        La evaluación debe incluir:
        1. Localización del dolor
        2. Intensidad (escala 1-10)
        3. Características del dolor (agudo, sordo, pulsante, etc.)
        4. Factores que aumentan o disminuyen el dolor
        5. Impacto en actividades diarias
        6. Posibles causas
        7. Recomendaciones iniciales
        8. Cuándo buscar atención médica
        
        Devuelve la evaluación en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Historial de lesiones: {user_profile.get('injury_history', 'N/A')}
            - Calidad de sueño: {user_profile.get('sleep_quality', 'N/A')}
            - Nivel de estrés: {user_profile.get('stress_level', 'N/A')}
            - Áreas de dolor: {user_profile.get('pain_areas', 'N/A')}
            """
        
        # Generar la evaluación de dolor
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "location": "Ubicación del dolor no especificada",
                    "intensity": "Intensidad no especificada",
                    "characteristics": "Características no especificadas",
                    "aggravating_factors": ["Factores que aumentan el dolor no especificados"],
                    "relieving_factors": ["Factores que disminuyen el dolor no especificados"],
                    "impact": "Impacto en actividades diarias no especificado",
                    "possible_causes": ["Causas posibles no especificadas"],
                    "recommendations": ["Recomendaciones generales"],
                    "seek_medical_attention": "Buscar atención médica si el dolor persiste más de 7 días o empeora"
                }
        
        return response
