import logging
import uuid
import time
import json
from typing import Dict, Any, Optional, List, Union
import os
from google.cloud import aiplatform

try:
    from google.adk.toolkit import Toolkit
except ImportError:
    from adk.toolkit import Toolkit

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from agents.base.a2a_agent import A2AAgent
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)


class RecoveryCorrective(A2AAgent):
    """
    Agente Recovery & Corrective Specialist compatible con A2A
    
    Prevención / rehab, movilidad, sueño, protocolos de HRV & dolor crónico.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "injury_prevention",
            "rehabilitation",
            "mobility_assessment",
            "sleep_optimization",
            "hrv_protocols",
            "chronic_pain_management"
        ]
        
        # Definir skills siguiendo el formato A2A con mejores prácticas
        skills = [
            {
                "id": "injury-prevention-protocols",
                "name": "Protocolos de Prevención de Lesiones",
                "description": "Genera protocolos personalizados para prevenir lesiones comunes.",
                "tags": ["injury", "prevention", "protocol", "safety", "exercise"],
                "examples": [
                    "Rutina de calentamiento para corredores para evitar lesiones de rodilla",
                    "Ejercicios para fortalecer el manguito rotador"
                ],
                "inputModes": ["text"],
                "outputModes": ["text", "markdown"]
            },
            {
                "id": "rehabilitation-guidance",
                "name": "Guía de Rehabilitación",
                "description": "Ofrece orientación y planes de rehabilitación basados en el tipo de lesión y la fase de recuperación.",
                "tags": ["rehabilitation", "recovery", "injury", "physical therapy", "plan"],
                "examples": [
                    "Ejercicios para rehabilitar un esguince de tobillo (fase inicial)",
                    "Plan de recuperación post-cirugía de LCA"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "markdown", "json"]
            },
             {
                "id": "mobility-flexibility-improvement",
                "name": "Mejora de Movilidad y Flexibilidad",
                "description": "Diseña rutinas para mejorar la movilidad articular y la flexibilidad muscular.",
                "tags": ["mobility", "flexibility", "stretching", "range of motion", "yoga"],
                "examples": [
                    "Rutina de movilidad de cadera para oficinistas",
                    "Estiramientos para mejorar la flexibilidad de isquiotibiales"
                ],
                "inputModes": ["text"],
                "outputModes": ["text", "markdown", "video_suggestion"]
            },
            {
                "id": "sleep-optimization-strategies",
                "name": "Estrategias de Optimización del Sueño",
                "description": "Proporciona consejos y técnicas para mejorar la calidad y cantidad del sueño.",
                "tags": ["sleep", "recovery", "insomnia", "sleep hygiene", "performance"],
                "examples": [
                    "Consejos para dormir mejor por la noche",
                    "Cómo crear una rutina relajante antes de acostarse"
                ],
                "inputModes": ["text"],
                "outputModes": ["text", "markdown"]
            },
             {
                "id": "hrv-analysis-interpretation",
                "name": "Análisis e Interpretación de VFC (HRV)",
                "description": "Interpreta los datos de Variabilidad de la Frecuencia Cardíaca (VFC) para evaluar la recuperación y el estrés.",
                "tags": ["hrv", "vfc", "recovery", "stress", "autonomic nervous system", "biometrics"],
                "examples": [
                    "Mi VFC de hoy es 45ms, ¿qué significa?",
                    "Cómo interpretar las tendencias de mi VFC semanal"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "markdown", "json"]
            },
            {
                "id": "chronic-pain-management-techniques",
                "name": "Técnicas de Manejo del Dolor Crónico",
                "description": "Ofrece estrategias no farmacológicas para manejar el dolor crónico.",
                "tags": ["pain management", "chronic pain", "non-pharmacological", "mindfulness", "therapy"],
                "examples": [
                    "Técnicas de mindfulness para el dolor lumbar crónico",
                    "Ejercicios suaves para aliviar la fibromialgia"
                ],
                "inputModes": ["text"],
                "outputModes": ["text", "markdown"]
            }
            # Añadir más skills detallados si es necesario
        ]
        
        # Llamada al constructor de A2AAgent
        super().__init__(
            agent_id="recovery_corrective",
            name="NGX Recovery & Corrective Specialist",
            description="Especialista en prevención, rehabilitación, movilidad, sueño, HRV y manejo del dolor crónico.",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            skills=skills, # Pasar skills aquí
            a2a_server_url=a2a_server_url,
            state_manager=state_manager # Pasar state_manager si A2AAgent lo acepta
        )
        
        # Inicialización de AI Platform (después de super)
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)
        
        # Inicializar clientes y herramientas (después de super)
        self.gemini_client = GeminiClient(model_name="gemini-1.5-flash") # Asegúrate que el modelo es correcto
        # self.supabase_client = SupabaseClient() # Descomentar si se usa
        # self.mcp_toolkit = MCPToolkit() # Descomentar si se usa
        
        # Las skills ya están definidas y pasadas a super(), no es necesario registrarlas de nuevo aquí si A2AAgent lo maneja.

        # AgentCard se crea implícitamente en A2AAgent a partir de los parámetros
        # o se puede sobreescribir get_agent_card() si se necesita personalización

        # Configuración adicional específica del agente
        self.system_instructions = "Eres un especialista experto en recuperación física, prevención de lesiones y manejo del dolor." 

        logger.info(f"Agente {self.agent_id} inicializado.")

    async def _get_context(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        # Registrar métrica de solicitud si telemetría está disponible
        if hasattr(self, "has_telemetry") and self.has_telemetry and hasattr(self, "request_counter"):
            self.request_counter.add(1, {"agent_id": self.agent_id, "user_id": user_id or "anonymous"})
        
        # Crear span para trazar la ejecución si telemetría está disponible
        if hasattr(self, "has_telemetry") and self.has_telemetry and hasattr(self, "tracer"):
            with self.tracer.start_as_current_span("recovery_corrective_process_request") as span:
                span.set_attribute("user_id", user_id or "anonymous")
                span.set_attribute("session_id", session_id or "none")
                span.set_attribute("input_length", len(input_text))
                
                # Medir tiempo de respuesta
                start_time = time.time()
                result = await self._process_request(input_text, user_id, session_id, **kwargs)
                end_time = time.time()
                
                # Registrar métrica de tiempo de respuesta
                if hasattr(self, "response_time") and self.response_time:
                    self.response_time.record(end_time - start_time, {"agent_id": self.agent_id})
                    
                return result
        else:
            # Ejecución sin telemetría
            return await self._process_request(input_text, user_id, session_id, **kwargs)
    
    async def _process_request(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la solicitud del usuario y genera una respuesta utilizando las skills adecuadas.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        start_time = time.time()
        result = {}
        protocol_id = None
        response_text = ""
        response_type = "text"
        
        try:
            # Generar ID de usuario y sesión si no se proporcionan
            user_id = user_id or str(uuid.uuid4())
            session_id = session_id or str(uuid.uuid4())
            
            # Obtener contexto de la conversación
            context = await self._get_context(user_id, session_id)
            
            # Obtener perfil del usuario si está disponible
            user_profile = kwargs.get("user_profile", {})
            
            # Analizar la entrada del usuario para determinar la skill a utilizar
            if any(keyword in input_text.lower() for keyword in ["prevenir", "prevención", "evitar lesiones", "proteger"]):
                # Usar skill de prevención de lesiones
                try:
                    result = await self.execute_skill("injury_prevention", 
                                                   input_text=input_text, 
                                                   user_profile=user_profile, 
                                                   context=context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Plan de prevención de lesiones:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    prevention_plans = self._state.get("prevention_plans", {})
                    protocol_id = str(uuid.uuid4())
                    prevention_plans[protocol_id] = result
                    self.update_state("prevention_plans", prevention_plans)
                    response_type = "prevention_plan"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill injury_prevention: {e}")
                    response_text = "Lo siento, ha ocurrido un error al generar el plan de prevención de lesiones."
                    result = {"error": str(e)}
                    protocol_id = None
                
            elif any(keyword in input_text.lower() for keyword in ["rehabilitación", "recuperación", "rehab", "recuperar"]):
                # Usar skill de rehabilitación
                try:
                    result = await self.execute_skill("rehabilitation", 
                                                   input_text=input_text, 
                                                   user_profile=user_profile, 
                                                   context=context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Protocolo de rehabilitación:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    rehab_protocols = self._state.get("recovery_protocols", {})
                    protocol_id = str(uuid.uuid4())
                    rehab_protocols[protocol_id] = result
                    self.update_state("recovery_protocols", rehab_protocols)
                    response_type = "rehabilitation_protocol"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill rehabilitation: {e}")
                    response_text = "Lo siento, ha ocurrido un error al generar el protocolo de rehabilitación."
                    result = {"error": str(e)}
                    protocol_id = None
                
            elif any(keyword in input_text.lower() for keyword in ["dolor", "molestia", "lesión", "lastimado"]):
                # Generar evaluación de dolor
                try:
                    pain_assessment = await self._generate_pain_assessment(input_text, user_profile)
                    
                    # Almacenar evaluación en el estado
                    pain_assessments = self._state.get("pain_assessments", {})
                    protocol_id = str(uuid.uuid4())
                    pain_assessments[protocol_id] = pain_assessment
                    self.update_state("pain_assessments", pain_assessments)
                    
                    # Generar respuesta
                    response_text = await self._summarize_pain_assessment(pain_assessment)
                    result = pain_assessment
                    response_type = "pain_assessment"
                except Exception as e:
                    logger.error(f"Error al generar evaluación de dolor: {e}")
                    response_text = "Lo siento, ha ocurrido un error al generar la evaluación de dolor."
                    result = {"error": str(e)}
                    protocol_id = None
            else:
                # Generar protocolo de recuperación por defecto
                try:
                    recovery_protocol = await self._generate_recovery_protocol(input_text, user_profile)
                    
                    # Almacenar protocolo en el estado
                    recovery_protocols = self._state.get("recovery_protocols", {})
                    protocol_id = str(uuid.uuid4())
                    recovery_protocols[protocol_id] = recovery_protocol
                    self.update_state("recovery_protocols", recovery_protocols)
                    
                    # Generar respuesta
                    response_text = await self._summarize_recovery_protocol(recovery_protocol)
                    result = recovery_protocol
                    response_type = "recovery_protocol"
                except Exception as e:
                    logger.error(f"Error al generar protocolo de recuperación: {e}")
                    response_text = "Lo siento, ha ocurrido un error al generar el protocolo de recuperación."
                    result = {"error": str(e)}
                    protocol_id = None
            
            # Crear respuesta base
            response = {
                "text": response_text,
                "data": result
            }
            
            # Añadir la interacción al historial de conversación en el contexto
            if user_id and "conversation_history" in context:
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "response_type": response_type
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Crear artefactos para la respuesta según el protocolo A2A
            artifacts = [
                {
                    "type": response_type,
                    "content": result,
                    "metadata": {
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            ]
            
            # Devolver respuesta final siguiendo el formato A2A
            return {
                "status": "success",
                "response": response_text,
                "result": result,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "id": protocol_id,
                    "created_at": time.time(),
                    "processing_time": time.time() - start_time,
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
    
    async def _register_skills(self):
        """
        Registra las habilidades del agente según el protocolo A2A con metadatos mejorados.
        """
        # Registrar skills en el toolkit si está disponible
        if self.toolkit:
            try:
                # Registrar skill de prevención de lesiones
                await self.register_skill(
                    "injury_prevention",
                    "Genera planes personalizados para prevenir lesiones específicas en diferentes actividades físicas y deportes",
                    self._generate_injury_prevention_plan,
                    tags=["prevention", "exercise", "safety", "injury", "training"],
                    examples=[
                        "Cómo prevenir lesiones en la espalda baja durante el entrenamiento de fuerza",
                        "Plan de prevención para corredores con historial de lesiones en rodilla",
                        "Ejercicios preventivos para tenistas con problemas de hombro"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de rehabilitación
                await self.register_skill(
                    "rehabilitation",
                    "Desarrolla protocolos de rehabilitación personalizados para diferentes tipos de lesiones y condiciones físicas",
                    self._generate_rehabilitation_protocol,
                    tags=["rehab", "recovery", "injury", "therapy", "healing"],
                    examples=[
                        "Protocolo de rehabilitación para esguince de tobillo grado 2",
                        "Plan de recuperación post-quirúrgico para reconstrucción de LCA",
                        "Programa de rehabilitación para tendinitis rotuliana crónica"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de evaluación de movilidad
                await self.register_skill(
                    "mobility_assessment",
                    "Evalúa limitaciones de movilidad y proporciona estrategias específicas para mejorar el rango de movimiento y la función articular",
                    self._generate_mobility_assessment,
                    tags=["mobility", "flexibility", "assessment", "range-of-motion", "joints"],
                    examples=[
                        "Evaluación de movilidad de cadera para mejorar sentadillas profundas",
                        "Ejercicios para aumentar la movilidad de hombros en nadadores",
                        "Protocolo para mejorar la dorsiflexión de tobillo limitada"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de optimización del sueño
                await self.register_skill(
                    "sleep_optimization",
                    "Analiza patrones de sueño y proporciona estrategias personalizadas para mejorar la calidad y cantidad del descanso para optimizar la recuperación",
                    self._generate_sleep_optimization_plan,
                    tags=["sleep", "recovery", "rest", "circadian-rhythm", "performance"],
                    examples=[
                        "Estrategias para mejorar el sueño durante periodos de alto estrés",
                        "Rutina nocturna para atletas con problemas para conciliar el sueño",
                        "Plan de optimización del sueño para viajes con cambios de zona horaria"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de protocolos HRV
                await self.register_skill(
                    "hrv_protocols",
                    "Interpreta datos de variabilidad de frecuencia cardíaca y desarrolla estrategias de entrenamiento y recuperación basadas en el estado del sistema nervioso autónomo",
                    self._generate_hrv_protocol,
                    tags=["hrv", "heart-rate-variability", "recovery", "training", "autonomic-nervous-system"],
                    examples=[
                        "Interpretación de tendencias de HRV para periodización del entrenamiento",
                        "Estrategias de recuperación basadas en valores bajos persistentes de HRV",
                        "Protocolo de entrenamiento adaptativo basado en lecturas diarias de HRV"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de manejo del dolor crónico
                await self.register_skill(
                    "chronic_pain_management",
                    "Desarrolla estrategias integrales para el manejo del dolor agudo y crónico utilizando enfoques multidisciplinarios y basados en evidencia",
                    self._generate_pain_management_protocol,
                    tags=["pain", "chronic", "management", "therapy", "relief"],
                    examples=[
                        "Estrategias no farmacológicas para manejar el dolor crónico de rodilla",
                        "Plan integral para reducir el dolor lumbar en trabajadores de oficina",
                        "Técnicas de autogestión para migrañas recurrentes relacionadas con el estrés"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                logger.info(f"Skills registradas correctamente: {len(self.skills)}")
            except Exception as e:
                logger.error(f"Error al registrar skills: {e}")
        else:
            logger.warning("No se ha proporcionado un toolkit para registrar skills")

            
            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute({
                    "prompt": prompt,
                    "temperature": 0.7,
                    "model": "gemini-2.0-flash"
                })
                response_text = result.get("text", "")
                
                # Intentar extraer JSON de la respuesta
                try:
                    # Buscar patrón JSON en la respuesta
                    import re
                    json_match = re.search(r'({.*})', response_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        # Si no se encuentra JSON, devolver respuesta como texto
                        return {"response": response_text}
                except Exception as e:
                    logger.warning(f"Error al extraer JSON de la respuesta: {e}")
                    return {"response": response_text}
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                response = await self.gemini_client.generate_structured_output(prompt)
                return response if isinstance(response, dict) else {"response": str(response)}
        
        # Registrar skills
        await self.register_skill("injury_prevention", injury_prevention)
        await self.register_skill("rehabilitation", rehabilitation)
        
        logger.info(f"Skills registradas para el agente {self.agent_id}")
    
    async def get_agent_card(self) -> Dict[str, Any]:
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
        # TODO: Integrar RAG para buscar protocolos estándar de rehabilitación NGX o de la literatura.
        # TODO: Usar mcp7_query para obtener datos específicos del usuario (ej. tipo de lesión, historial) desde Supabase.
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
        # TODO: Integrar RAG para buscar información sobre posibles causas del dolor según literatura/NGX.
        # TODO: Usar mcp7_query para obtener datos del usuario (ej. actividades recientes, otros síntomas) desde Supabase.
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

# Bloque de ejecución para pruebas locales (si existe)
if __name__ == '__main__':
    import asyncio
    import json
    logging.basicConfig(level=logging.INFO)

    async def main():
        agent = RecoveryCorrective()

        print("--- Prueba ADK (_run_async_impl) --- ")
        adk_input = "Necesito ejercicios para prevenir el dolor de espalda baja"
        adk_response = await agent._run_async_impl(adk_input, user_id="test_user_adk")
        print(f"Entrada ADK: {adk_input}")
        print(f"Respuesta ADK: {json.dumps(adk_response, indent=2)}\n")

        print("--- Prueba A2A execute_task (usando base A2AAgent) --- ")
        a2a_task = create_task(
            skill_id="injury-prevention-protocols", 
            input_data={"text": "Ejercicios de calentamiento para corredores", "user_id": "test_user_a2a_task"}
        )
        # La clase base A2AAgent llama a _run_async_impl por defecto si no se sobreescribe execute_task
        a2a_result = await agent.execute_task(a2a_task) 
        print(f"Tarea A2A: {json.dumps(a2a_task, indent=2)}")
        print(f"Resultado A2A: {json.dumps(a2a_result, indent=2)}\n")

        print("--- Prueba A2A process_message (usando base A2AAgent) --- ")
        # Crear mensaje A2A correctamente
        a2a_message_content = {
            "message_id": str(uuid.uuid4()),
            "role": "user", 
            "parts": [{"type": "text", "text": "¿Cómo puedo mejorar mi movilidad de hombros?"}],
            "metadata": {"user_id": "test_user_a2a_msg", "session_id": "session_recov1"}
        }
        a2a_response_msg = await agent.process_message(from_agent="other_agent_2", content=a2a_message_content)
        print(f"Mensaje A2A entrante: {json.dumps(a2a_message_content, indent=2)}")
        print(f"Respuesta A2A (mensaje): {json.dumps(a2a_response_msg, indent=2) if a2a_response_msg else 'None'}\n")

        print("--- Prueba A2A get_agent_card --- ")
        agent_card_dict = agent.get_agent_card()
        print(f"Agent Card: {json.dumps(agent_card_dict, indent=2)}")

    asyncio.run(main())
