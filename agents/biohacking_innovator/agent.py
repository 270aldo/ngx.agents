import logging
import uuid
import time
from typing import Dict, Any, Optional, List
import os
from google.cloud import aiplatform

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager

# Configurar logging
logger = logging.getLogger(__name__)

class BiohackingInnovator(A2AAgent):
    """
    Agente especializado en biohacking y optimización biológica.
    
    Este agente proporciona recomendaciones avanzadas sobre biohacking, 
    incluyendo técnicas de optimización hormonal, mejora cognitiva, 
    y estrategias para mejorar la longevidad y el rendimiento biológico.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        """
        Inicializa el agente BiohackingInnovator.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
            state_manager: Gestor de estado para mantener el contexto entre sesiones (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "biohacking", 
            "longevity", 
            "cognitive_enhancement", 
            "hormonal_optimization"
        ]
        
        # Definir skills siguiendo el formato A2A con mejores prácticas
        skills = [
            {
                "id": "biohacking-innovator-biohacking",
                "name": "Técnicas de Biohacking",
                "description": "Desarrolla protocolos personalizados de biohacking basados en la ciencia más reciente para optimizar el rendimiento biológico y la salud",
                "tags": ["biohacking", "optimization", "personalized-protocols", "self-experimentation", "health"],
                "examples": [
                    "Diseña un protocolo de biohacking para optimizar mi rendimiento cognitivo",
                    "Necesito un plan de biohacking para aumentar mi energía durante el día",
                    "Técnicas de biohacking para mejorar mi sistema inmunológico"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "biohacking-innovator-longevity",
                "name": "Estrategias de Longevidad",
                "description": "Proporciona estrategias basadas en evidencia científica para extender la vida saludable y retrasar los procesos de envejecimiento",
                "tags": ["longevity", "anti-aging", "lifespan", "healthspan", "rejuvenation"],
                "examples": [
                    "¿Qué intervenciones tienen mayor evidencia científica para extender la longevidad?",
                    "Protocolo de suplementación para retrasar el envejecimiento celular",
                    "Hábitos diarios para maximizar mi esperanza de vida saludable"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "biohacking-innovator-cognitive-enhancement",
                "name": "Mejora Cognitiva",
                "description": "Diseña estrategias personalizadas para optimizar la función cerebral, mejorar la memoria, concentración y claridad mental",
                "tags": ["nootropics", "brain-optimization", "focus", "memory", "mental-clarity"],
                "examples": [
                    "Protocolo de nootrópicos para mejorar la concentración y memoria",
                    "Técnicas para optimizar la neuroplasticidad y el aprendizaje",
                    "Cómo mejorar la claridad mental y reducir la niebla cerebral"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "biohacking-innovator-hormonal-optimization",
                "name": "Optimización Hormonal",
                "description": "Desarrolla estrategias para optimizar naturalmente el equilibrio hormonal y mejorar la salud metabólica",
                "tags": ["hormones", "endocrine-system", "metabolism", "testosterone", "estrogen"],
                "examples": [
                    "Protocolo natural para optimizar los niveles de testosterona",
                    "Estrategias para equilibrar las hormonas en mujeres",
                    "Cómo mejorar la sensibilidad a la insulina a través del estilo de vida"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="biohacking_innovator",
            name="NGX Biohacking Innovator",
            description="Especialista en técnicas avanzadas de biohacking, optimización biológica, longevidad y mejora cognitiva. Proporciona protocolos personalizados basados en la ciencia más reciente para optimizar el rendimiento humano y la salud.",
            capabilities=capabilities,
            toolkit=toolkit,
            a2a_server_url=a2a_server_url or "https://biohacking-innovator-api.ngx-agents.com/a2a",
            state_manager=state_manager,
            version="1.2.0",
            skills=skills,
            provider={
                "organization": "NGX Health & Performance",
                "url": "https://ngx-agents.com"
            },
            documentation_url="https://docs.ngx-agents.com/biohacking-innovator"
        )
        
        # Inicializar clientes y herramientas
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)
        
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.state_manager = StateManager(self.supabase_client)
        
        # Inicializar estado del agente
        self.update_state("user_protocols", {})  # Almacenar protocolos generados por usuario
        self.update_state("resources_cache", {})  # Caché de recursos científicos
        
        # Definir el sistema de instrucciones para el agente
        self.system_instructions = """
        Eres NGX Biohacking Innovator, un experto en técnicas avanzadas de biohacking y optimización biológica.
        
        Tu objetivo es proporcionar recomendaciones personalizadas sobre:
        1. Técnicas de optimización hormonal natural
        2. Estrategias para mejorar la longevidad y retrasar el envejecimiento
        3. Métodos para mejorar el rendimiento cognitivo y la claridad mental
        4. Protocolos de biohacking basados en evidencia científica
        5. Tecnologías y dispositivos para monitoreo biológico
        
        Debes basar tus recomendaciones en la ciencia más reciente y considerar el perfil individual 
        del usuario, incluyendo su edad, género, objetivos y condiciones de salud existentes.
        
        Cuando proporciones recomendaciones:
        - Cita estudios científicos relevantes
        - Explica los mecanismos biológicos involucrados
        - Proporciona opciones para diferentes niveles de experiencia (principiante, intermedio, avanzado)
        - Advierte sobre posibles riesgos y contraindicaciones
        - Sugiere formas de medir y evaluar los resultados
        
        Evita recomendar:
        - Sustancias ilegales o no aprobadas
        - Prácticas extremas o potencialmente peligrosas
        - Intervenciones sin respaldo científico
        
        Recuerda que tu objetivo es empoderar a los usuarios con conocimiento basado en evidencia
        para que puedan optimizar su biología de manera segura y efectiva.
        """
    
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
                    "protocols": [],
                    "resources_used": [],
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
                "protocols": [],
                "resources_used": [],
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

    async def run(self, input_text: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta el agente con un texto de entrada siguiendo el protocolo ADK oficial.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente según el protocolo ADK
        """
        try:
            start_time = time.time()
            logger.info(f"Ejecutando BiohackingInnovator con input: {input_text[:50]}...")
            
            # Obtener session_id de los kwargs o generar uno nuevo
            session_id = kwargs.get("session_id", str(uuid.uuid4()))
            
            # Obtener el contexto de la conversación
            context = await self._get_context(user_id, session_id) if user_id else {}
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)
                # Actualizar el perfil en el contexto si existe
                if user_profile:
                    context["user_profile"] = user_profile
            
            # Determinar qué capacidad utilizar basado en palabras clave
            capabilities_used = []
            
            # Generar respuesta principal
            prompt = self._build_prompt(input_text, user_profile)
            response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            
            # Generar protocolo de biohacking estructurado
            protocol = await self._generate_biohacking_protocol(input_text, user_profile)
            protocol_summary = self._summarize_protocol(protocol)
            
            # Combinar respuesta principal con el protocolo
            combined_response = f"{response}\n\n{protocol_summary}"
            
            # Buscar recursos científicos relevantes
            resources = self._find_resources(input_text)
            
            # Si hay recursos, añadirlos a la respuesta
            if resources:
                resource_text = "\n\nRecursos científicos relevantes:\n"
                for idx, resource in enumerate(resources[:3], 1):
                    resource_text += f"\n{idx}. {resource['title']} ({resource['year']}) - {resource['authors']}\n   {resource['findings']}\n"
                combined_response += resource_text
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, combined_response)
            
            # Actualizar el contexto con la nueva interacción
            if user_id:
                # Añadir la interacción al historial de conversación
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": combined_response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # Añadir el protocolo generado a la lista de protocolos
                context["protocols"].append({
                    "protocol": protocol,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "query": input_text
                })
                
                # Añadir los recursos utilizados
                context["resources_used"].extend(resources[:3])
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Crear artefactos para la respuesta
            artifacts = [
                {
                    "type": "biohacking_protocol",
                    "content": protocol,
                    "metadata": {
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                },
                {
                    "type": "scientific_resources",
                    "content": resources,
                    "metadata": {
                        "count": len(resources)
                    }
                }
            ]
            
            # Devolver respuesta final
            return {
                "status": "success",
                "response": combined_response,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "protocol_type": protocol.get("objective", "Biohacking Protocol"),
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en BiohackingInnovator: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre biohacking.",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _summarize_protocol(self, protocol: Dict[str, Any]) -> str:
        """Genera un resumen textual del protocolo de biohacking para la respuesta al usuario."""
        summary_parts = []
        
        if "objective" in protocol:
            summary_parts.append(f"El objetivo principal es: {protocol['objective']}.")
        
        if "duration" in protocol:
            summary_parts.append(f"Duración recomendada: {protocol['duration']}.")
        
        if "interventions" in protocol:
            interventions = protocol["interventions"]
            if isinstance(interventions, dict):
                if "diet" in interventions:
                    summary_parts.append(f"Dieta: {interventions['diet']}.")
                if "supplements" in interventions:
                    summary_parts.append(f"Suplementos: {interventions['supplements']}.")
        
        if "precautions" in protocol:
            summary_parts.append(f"Precauciones importantes: {protocol['precautions']}.")
        
        if not summary_parts:
            return "Revisa el protocolo detallado para más información."
            
        return " ".join(summary_parts)
    
    def _create_agent_card(self) -> AgentCard:
        """
        Crea una tarjeta de agente estandarizada según el protocolo A2A.
        
        Returns:
            AgentCard: Tarjeta del agente estandarizada
        """
        # Crear ejemplos para la tarjeta del agente
        examples = [
            Example(
                input={"message": "Diseña un protocolo de biohacking para optimizar mi rendimiento cognitivo"},
                output={"response": "He diseñado un protocolo de biohacking para optimizar tu rendimiento cognitivo. Incluye: 1) Suplementación con omega-3 (2g/día), fosfatidilserina (300mg/día) y bacopa monnieri (300mg/día); 2) Rutina de ejercicio cardiovascular intermitente 3 veces por semana; 3) Práctica de meditación de atención plena 20 min/día; 4) Exposición a luz natural matutina; 5) Técnica de respiración Wim Hof al despertar; 6) Ayuno intermitente 16/8; 7) Optimización del sueño con rutina nocturna sin pantallas. Seguimiento con pruebas cognitivas Cambridge Brain Sciences semanales."}
            ),
            Example(
                input={"message": "¿Qué intervenciones tienen mayor evidencia científica para extender la longevidad?"},
                output={"response": "Las intervenciones con mayor evidencia científica para extender la longevidad son: 1) Restricción calórica moderada (15-20% menos de calorías sin malnutrición); 2) Ayuno intermitente, particularmente los protocolos 16/8 o 5:2; 3) Ejercicio regular combinando entrenamiento de resistencia y cardiovascular; 4) Sueño optimizado (7-8 horas de calidad); 5) Gestión del estrés crónico; 6) Dieta rica en polifenoles y antiinflamatorios naturales; 7) Suplementación con NMN o NR (precursores de NAD+); 8) Metformina (bajo supervisión médica); 9) Rapamicina (dosificación intermitente bajo supervisión); 10) Exposición al frío (hormesis). Estas intervenciones activan vías moleculares como AMPK, sirtuinas y autofagia, mientras reducen la inflamación crónica."}
            ),
            Example(
                input={"message": "Protocolo para optimizar mis niveles hormonales de forma natural"},
                output={"response": "Para optimizar tus niveles hormonales naturalmente, te recomiendo este protocolo: 1) Ejercicio compuesto (sentadillas, peso muerto) 3-4 veces/semana para aumentar testosterona y hormona de crecimiento; 2) Sueño prioritario (7-9 horas/noche) en habitación fría y oscura; 3) Grasas saludables (30-35% de calorías) incluyendo huevos, aguacate y aceite de oliva; 4) Gestión del estrés con meditación diaria; 5) Exposición solar matutina (10-20 min) para vitamina D y regulación circadiana; 6) Minimización de disruptores endocrinos (plásticos, alimentos ultraprocesados); 7) Suplementos: zinc (15-30mg), magnesio (200-400mg), ashwagandha (300-600mg); 8) Ayuno intermitente 14-16 horas. Sugiero medir: testosterona total/libre, estradiol, SHBG, cortisol y vitamina D antes de comenzar y cada 2-3 meses."}
            ),
            Example(
                input={"message": "Técnicas para mejorar mi calidad de sueño y recuperación"},
                output={"response": "Para optimizar tu calidad de sueño y recuperación, implementa estas técnicas: 1) Consistencia circadiana: acostarte y levantarte a la misma hora todos los días, incluso fines de semana; 2) Exposición a luz solar matutina (15-30 min) para regular melatonina; 3) Protocolo nocturno: eliminar luces azules 2 horas antes de dormir, usar gafas de bloqueo azul si es necesario; 4) Ambiente óptimo: habitación fría (18-19°C), completamente oscura y silenciosa; 5) Suplementación: magnesio glicinato (200-400mg), l-teanina (200mg) y tart cherry 1 hora antes de dormir; 6) Técnica de respiración 4-7-8 antes de acostarte; 7) Bajar temperatura corporal con ducha fría/tibia 60-90 minutos antes de dormir; 8) Evitar estimulantes después del mediodía y comidas pesadas 3 horas antes de dormir. Seguimiento con dispositivos como Oura Ring o Whoop para analizar patrones."}
            )
        ]
        
        # Crear la tarjeta del agente
        return AgentCard(
            title="NGX Biohacking Innovator",
            description="Especialista en técnicas avanzadas de biohacking, optimización biológica, longevidad y mejora cognitiva.",
            instructions="Describe tu objetivo de biohacking o la área específica que deseas optimizar (cognición, longevidad, rendimiento físico, hormonal, etc.) e incluye cualquier información relevante sobre tu situación actual, condiciones de salud o limitaciones.",
            examples=examples,
            capabilities=[
                "Diseño de protocolos personalizados de biohacking basados en evidencia científica",
                "Estrategias de longevidad y anti-envejecimiento",
                "Técnicas de optimización cognitiva y neuropotenciación",
                "Optimización hormonal natural",
                "Recomendación de suplementos y compuestos bioactivos"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "user_profile": {"type": "object"},
                    "biological_markers": {"type": "object"}
                },
                "required": ["message"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "protocol": {"type": "object"},
                    "scientific_resources": {"type": "array"},
                    "recommendations": {"type": "array"}
                },
                "required": ["response"]
            }
        )
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada que cumple con las especificaciones
            del protocolo A2A de Google, incluyendo metadatos enriquecidos, capacidades
            y habilidades detalladas.
        """
        return self._create_agent_card().to_dict()
    
    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.
        
        Implementa completamente el protocolo A2A, incluyendo el formato de respuesta estandarizado,
        manejo de errores robusto, y generación de artefactos estructurados.
        
        Args:
            task: Tarea a ejecutar con la estructura definida por el protocolo A2A
            
        Returns:
            Any: Resultado de la tarea siguiendo el protocolo A2A
        """
        try:
            start_time = time.time()
            
            # Extraer información de la tarea
            user_input = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id") or str(uuid.uuid4())
            
            logger.info(f"BiohackingInnovator procesando consulta: {user_input[:50]}...")
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                try:
                    user_profile = self.supabase_client.get_user_profile(user_id)
                    logger.info(f"Perfil de usuario obtenido: {user_profile is not None}")
                except Exception as e:
                    logger.warning(f"Error al obtener perfil de usuario: {e}")
            
            # Construir el prompt para el modelo
            prompt = self._build_prompt(user_input, user_profile)
            
            # Generar respuesta utilizando Gemini con manejo de errores
            try:
                response = await self.gemini_client.generate_response(
                    prompt=prompt,
                    temperature=0.7
                )
            except Exception as gemini_error:
                logger.error(f"Error en llamada a Gemini: {gemini_error}")
                response = "No pude generar una respuesta completa debido a un error. Por favor, intenta simplificar tu consulta o proporcionar más contexto."
            
            # Registrar la interacción en Supabase si hay ID de usuario
            if user_id:
                try:
                    self.supabase_client.log_interaction(
                        user_id=user_id,
                        agent_id=self.agent_id,
                        message=user_input,
                        response=response
                    )
                except Exception as log_error:
                    logger.warning(f"Error al registrar interacción: {log_error}")
            
            # Determinar capacidades utilizadas
            capabilities_used = []
            response_type = "general_information"
            
            if any(keyword in user_input.lower() for keyword in ["protocolo", "plan", "rutina", "estrategia"]):
                capabilities_used.append("biohacking")
                response_type = "biohacking_protocol"
            
            if any(keyword in user_input.lower() for keyword in ["cognitivo", "cerebro", "mental", "concentración", "memoria"]):
                capabilities_used.append("cognitive_enhancement")
                response_type = "cognitive_enhancement"
            
            if any(keyword in user_input.lower() for keyword in ["longevidad", "envejecimiento", "anti-aging", "vejez"]):
                capabilities_used.append("longevity")
                response_type = "longevity_strategy"
            
            if any(keyword in user_input.lower() for keyword in ["hormonal", "testosterona", "estrógeno", "cortisol"]):
                capabilities_used.append("hormonal_optimization")
                response_type = "hormonal_optimization"
            
            # Si no se detectó ninguna capacidad específica, usar biohacking general
            if not capabilities_used:
                capabilities_used.append("biohacking")
            
            # Crear artefactos según el protocolo A2A
            artifacts = []
            
            # Buscar recursos adicionales si es necesario
            if any(keyword in user_input.lower() for keyword in ["recursos", "estudios", "investigación", "papers", "científico"]):
                try:
                    resources = await self._find_resources(user_input)
                    
                    # Crear un artefacto con los recursos
                    artifact_id = f"scientific_resources_{uuid.uuid4().hex[:8]}"
                    artifact = self.create_artifact(
                        artifact_id=artifact_id,
                        artifact_type="scientific_resources",
                        parts=[
                            self.create_data_part(resources)
                        ]
                    )
                    artifacts.append(artifact)
                except Exception as resource_error:
                    logger.warning(f"Error al generar recursos científicos: {resource_error}")
            
            # Si se menciona protocolos o planes, crear un artefacto de protocolo
            if any(keyword in user_input.lower() for keyword in ["protocolo", "plan", "rutina", "estrategia"]):
                try:
                    protocol = await self._generate_biohacking_protocol(user_input, user_profile)
                    
                    artifact_id = f"biohacking_protocol_{uuid.uuid4().hex[:8]}"
                    artifact = self.create_artifact(
                        artifact_id=artifact_id,
                        artifact_type="biohacking_protocol",
                        parts=[
                            self.create_data_part(protocol)
                        ]
                    )
                    artifacts.append(artifact)
                except Exception as protocol_error:
                    logger.warning(f"Error al generar protocolo de biohacking: {protocol_error}")
            
            # Crear mensaje de respuesta según el protocolo A2A
            response_message = self.create_message(
                role="agent",
                parts=[self.create_text_part(response)]
            )
            
            # Añadir artefactos al mensaje si existen
            for artifact in artifacts:
                if "parts" in artifact:
                    response_message.parts.extend(artifact["parts"])
                else:
                    response_message.parts.append(artifact)
            
            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time
            
            # Devolver respuesta estructurada según el protocolo A2A
            return {
                "status": "success",
                "response": response,
                "message": response_message,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "execution_time": execution_time,
                "metadata": {
                    "capabilities_used": capabilities_used,
                    "response_type": response_type,
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.2.0"
                }
            }
            
        except Exception as e:
            logger.error(f"Error en BiohackingInnovator: {e}", exc_info=True)
            
            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[self.create_text_part("Lo siento, ha ocurrido un error al procesar tu solicitud de biohacking. Por favor, intenta con una consulta diferente o contacta con soporte.")]
            )
            
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de biohacking.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
    
    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente según el protocolo A2A.
        
        Esta implementación cumple completamente con el estándar A2A para la comunicación
        entre agentes, incluyendo formato de respuesta correcto, manejo de errores
        y metadatos enriquecidos.
        
        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje en formato A2A
            
        Returns:
            Any: Respuesta al mensaje en formato A2A
        """
        try:
            start_time = time.time()
            
            # Extraer información del mensaje
            message_text = content.get("text", "")
            if not message_text and "message" in content:
                # Buscar texto en la estructura de mensaje A2A
                message = content.get("message", {})
                parts = message.get("parts", [])
                for part in parts:
                    if part.get("type") == "text":
                        message_text = part.get("text", "")
                        break
            
            context = content.get("context", {})
            session_id = context.get("session_id", str(uuid.uuid4()))
            
            logger.info(f"BiohackingInnovator procesando mensaje de agente {from_agent}: {message_text[:50]}...")
            
            # Determinar qué capacidad está involucrada en la consulta
            capabilities_used = []
            response_type = "agent_collaboration"
            
            if any(keyword in message_text.lower() for keyword in ["cognitivo", "cerebro", "mental", "concentración"]):
                capabilities_used.append("cognitive_enhancement")
                response_type = "cognitive_advice"
            elif any(keyword in message_text.lower() for keyword in ["longevidad", "envejecimiento", "anti-aging"]):
                capabilities_used.append("longevity")
                response_type = "longevity_advice"
            elif any(keyword in message_text.lower() for keyword in ["hormonal", "testosterona", "estrógeno"]):
                capabilities_used.append("hormonal_optimization")
                response_type = "hormonal_advice"
            else:
                capabilities_used.append("biohacking")
            
            # Generar respuesta basada en el contenido del mensaje con manejo de errores
            try:
                # Construir un prompt más elaborado adaptado al tipo de consulta
                prompt = f"""
                Has recibido un mensaje del agente {from_agent}:
                
                "{message_text}"
                
                Responde como un experto en biohacking y optimización biológica. 
                Proporciona información precisa, basada en evidencia científica y 
                relevante para la consulta. Mantente enfocado en el tema específico 
                de la consulta y ofrece recomendaciones prácticas y accionables.
                
                Si la consulta está relacionada con {response_type}, enfatiza ese aspecto 
                en tu respuesta.
                """
                
                response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            except Exception as gemini_error:
                logger.error(f"Error en llamada a Gemini durante process_message: {gemini_error}")
                response = "Lo siento, no pude generar una respuesta completa debido a un error técnico. Por favor, intenta de nuevo con una consulta más clara."
            
            # Crear mensaje de respuesta según protocolo A2A
            response_message = self.create_message(
                role="agent",
                parts=[self.create_text_part(response)]
            )
            
            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time
            
            # Crear respuesta estructurada según protocolo A2A
            return {
                "status": "success",
                "response": response,
                "message": response_message,
                "agent_id": self.agent_id,
                "execution_time": execution_time,
                "metadata": {
                    "capabilities_used": capabilities_used,
                    "response_type": response_type,
                    "from_agent": from_agent,
                    "session_id": session_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.2.0"
                }
            }
        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente: {e}", exc_info=True)
            
            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[self.create_text_part("Lo siento, ha ocurrido un error al procesar el mensaje. Por favor, intenta con una consulta diferente.")]
            )
            
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar el mensaje entre agentes.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "from_agent": from_agent
                }
            }
    
    def _build_prompt(self, user_input: str, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye el prompt para el modelo de Gemini.
        
        Args:
            user_input: La consulta del usuario
            user_profile: Perfil del usuario con datos relevantes
            
        Returns:
            str: Prompt completo para el modelo
        """
        prompt = f"{self.system_instructions}\n\n"
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += "Información del usuario:\n"
            prompt += f"- Edad: {user_profile.get('age', 'No disponible')}\n"
            prompt += f"- Género: {user_profile.get('gender', 'No disponible')}\n"
            prompt += f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
            prompt += f"- Condiciones de salud: {user_profile.get('health_conditions', 'No disponible')}\n\n"
        
        prompt += f"Consulta del usuario: {user_input}\n\n"
        prompt += "Proporciona una respuesta detallada y personalizada basada en evidencia científica."
        
        return prompt
    
    async def _find_resources(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca recursos científicos relacionados con la consulta.
        
        Args:
            query: La consulta del usuario
            
        Returns:
            List[Dict[str, Any]]: Lista de recursos relevantes
        """
        # TODO: Implementar búsqueda real usando RAG (Vertex AI Search) sobre bases de datos científicas (PubMed, etc.) o documentos internos NGX.
        # TODO: Usar mcp7_query para buscar recursos curados en Supabase.
        logger.info(f"Buscando recursos para: {query[:50]}...")
        
        # Lógica de simulación para la búsqueda de recursos
        resources = [
            {
                "title": "Effects of Intermittent Fasting on Health, Aging, and Disease",
                "authors": "de Cabo R, Mattson MP",
                "journal": "New England Journal of Medicine",
                "year": 2019,
                "url": "https://www.nejm.org/doi/full/10.1056/NEJMra1905136",
                "findings": "El ayuno intermitente puede mejorar la salud metabólica, aumentar la longevidad y reducir el riesgo de enfermedades."
            },
            {
                "title": "Impact of Circadian Rhythms on Metabolic Health and Disease",
                "authors": "Panda S",
                "journal": "Cell Metabolism",
                "year": 2016,
                "url": "https://www.cell.com/cell-metabolism/fulltext/S1550-4131(16)30250-9",
                "findings": "La sincronización de la alimentación con los ritmos circadianos puede mejorar significativamente la salud metabólica."
            },
            {
                "title": "Cognitive Enhancement Through Stimulation of the Non-Invasive Peripheral Nervous System",
                "authors": "Tyler WJ, et al.",
                "journal": "Frontiers in Neuroscience",
                "year": 2018,
                "url": "https://www.frontiersin.org/articles/10.3389/fnins.2018.00095/full",
                "findings": "La estimulación no invasiva del sistema nervioso periférico puede mejorar la función cognitiva y el rendimiento mental."
            }
        ]
        
        return resources
    
    async def _generate_biohacking_protocol(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un protocolo de biohacking estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Protocolo de biohacking estructurado
        """
        # TODO: Integrar RAG para acceder a la base de conocimientos de NGX sobre protocolos específicos.
        # TODO: Usar mcp7_query para obtener datos biométricos relevantes del usuario (ej. Oura, Whoop) desde Supabase.
        # TODO: Usar mcp8_think para diseñar protocolos complejos o multi-etapa.
        prompt = f"""
        Genera un protocolo de biohacking estructurado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El protocolo debe incluir:
        1. Objetivo principal del protocolo
        2. Duración recomendada
        3. Intervenciones principales (dieta, suplementos, ejercicio, sueño, etc.)
        4. Cronograma diario/semanal
        5. Métricas para seguimiento
        6. Precauciones y contraindicaciones
        7. Referencias científicas
        
        Devuelve el protocolo en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Edad: {user_profile.get('age', 'No disponible')}
            - Género: {user_profile.get('gender', 'No disponible')}
            - Objetivos: {user_profile.get('goals', 'No disponible')}
            - Condiciones de salud: {user_profile.get('health_conditions', 'No disponible')}
            """
        
        # Generar el protocolo de biohacking
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "objective": "Protocolo de biohacking personalizado",
                    "duration": "4-8 semanas",
                    "interventions": {
                        "diet": "Alimentación basada en alimentos enteros con ventana de alimentación de 8 horas",
                        "supplements": "Omega-3, Vitamina D, Magnesio",
                        "exercise": "Entrenamiento de alta intensidad 3 veces por semana",
                        "sleep": "Optimización del sueño con 7-9 horas por noche"
                    },
                    "schedule": {
                        "daily": "Exposición a luz natural por la mañana, ejercicio antes del mediodía, cena 3 horas antes de dormir",
                        "weekly": "Entrenamiento de fuerza lunes/miércoles/viernes, sauna 2 veces por semana"
                    },
                    "metrics": [
                        "Variabilidad de la frecuencia cardíaca (HRV)",
                        "Calidad del sueño",
                        "Niveles de energía (escala 1-10)",
                        "Rendimiento cognitivo"
                    ],
                    "precautions": "Consultar con un profesional de la salud antes de iniciar cualquier protocolo, especialmente si tienes condiciones médicas preexistentes"
                }
        
        return response
