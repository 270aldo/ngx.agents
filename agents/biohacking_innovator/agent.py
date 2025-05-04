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

class BiohackingInnovator(A2AAgent):
    """
    Agente especializado en biohacking y optimización biológica.
    
    Este agente proporciona recomendaciones avanzadas sobre biohacking, 
    incluyendo técnicas de optimización hormonal, mejora cognitiva, 
    y estrategias para mejorar la longevidad y el rendimiento biológico.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None):
        """
        Inicializa el agente BiohackingInnovator.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "biohacking", 
            "longevity", 
            "cognitive_enhancement", 
            "hormonal_optimization"
        ]
        
        skills = [
            {
                "name": "biohacking",
                "description": "Técnicas avanzadas de biohacking y autoexperimentación"
            },
            {
                "name": "longevity",
                "description": "Estrategias para mejorar la longevidad y retrasar el envejecimiento"
            },
            {
                "name": "cognitive_enhancement",
                "description": "Métodos para mejorar el rendimiento cognitivo y la claridad mental"
            },
            {
                "name": "hormonal_optimization",
                "description": "Técnicas de optimización hormonal natural"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito un protocolo para mejorar mi rendimiento cognitivo"},
                "output": {"response": "He creado un protocolo de biohacking personalizado para optimizar tu rendimiento cognitivo..."}
            },
            {
                "input": {"message": "¿Qué suplementos puedo tomar para mejorar mi longevidad?"},
                "output": {"response": "Basado en la evidencia científica actual, estos son los suplementos más prometedores para la longevidad..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="biohacking_innovator",
            name="NGX Biohacking Innovator",
            description="Especialista en técnicas avanzadas de biohacking y optimización biológica",
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
            
            logger.info(f"Procesando consulta de biohacking: {user_input}")
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)
                logger.info(f"Perfil de usuario obtenido: {user_profile is not None}")
            
            # Construir el prompt para el modelo
            prompt = self._build_prompt(user_input, user_profile)
            
            # Generar respuesta utilizando Gemini
            response = await self.gemini_client.generate_response(
                prompt=prompt,
                temperature=0.7
            )
            
            # Registrar la interacción en Supabase si hay ID de usuario
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=response
                )
            
            # Crear artefactos si es necesario
            artifacts = []
            
            # Buscar recursos adicionales si es necesario
            if any(keyword in user_input.lower() for keyword in ["recursos", "estudios", "investigación", "papers"]):
                resources = await self._find_resources(user_input)
                
                # Crear un artefacto con los recursos
                artifact_id = f"biohacking_resources_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="scientific_resources",
                    parts=[
                        self.create_data_part(resources)
                    ]
                )
                artifacts.append(artifact)
            
            # Si se menciona protocolos o planes, crear un artefacto de protocolo
            if any(keyword in user_input.lower() for keyword in ["protocolo", "plan", "rutina", "estrategia"]):
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
            logger.error(f"Error en BiohackingInnovator: {e}")
            return {
                "error": str(e), 
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de biohacking."
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
            
            logger.info(f"Procesando mensaje de agente {from_agent}: {message_text}")
            
            # Generar respuesta basada en el contenido del mensaje
            prompt = f"""
            Has recibido un mensaje del agente {from_agent}:
            
            "{message_text}"
            
            Responde con información relevante sobre biohacking y optimización biológica relacionada con este mensaje.
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
        # En una implementación real, esto podría conectarse a una base de datos
        # de estudios científicos o a una API externa
        
        # Generar recursos dinámicamente basados en la consulta
        prompt = f"""
        Genera una lista de 3-5 estudios científicos relevantes relacionados con la siguiente consulta sobre biohacking:
        
        "{query}"
        
        Para cada estudio, proporciona:
        1. Título completo
        2. Autores principales
        3. Nombre de la revista o publicación
        4. Año de publicación
        5. URL (puede ser hipotética si no conoces la URL exacta)
        6. Breve descripción de los hallazgos clave (2-3 oraciones)
        
        Devuelve los resultados en formato JSON estructurado.
        """
        
        # Generar recursos usando Gemini
        resources_json = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(resources_json, list):
            try:
                import json
                if isinstance(resources_json, str):
                    resources_json = json.loads(resources_json)
                if isinstance(resources_json, dict) and "resources" in resources_json:
                    resources_json = resources_json["resources"]
            except:
                # Si no se puede convertir, crear una lista básica
                resources_json = [
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
        
        return resources_json
    
    async def _generate_biohacking_protocol(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un protocolo de biohacking estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Protocolo de biohacking estructurado
        """
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
