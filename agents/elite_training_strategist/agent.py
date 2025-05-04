"""
Agente especializado en diseñar y periodizar programas de entrenamiento
para atletas de alto rendimiento.

Este agente implementa los protocolos oficiales A2A y ADK para comunicación
entre agentes y utiliza el modelo Gemini para generar planes personalizados.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
import time

from adk.toolkit import Toolkit
from agents.base.adk_agent import ADKAgent
from clients.gemini_client import GeminiClient
from core.agent_card import AgentCard, Example
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar OpenTelemetry para observabilidad
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    
    # Configurar TracerProvider para trazas
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer("elite_training_strategist")
    
    # Configurar MeterProvider para métricas
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("elite_training_strategist")
    
    # Crear contadores y medidores
    request_counter = meter.create_counter(
        name="agent_requests",
        description="Número de solicitudes recibidas por el agente",
        unit="1"
    )
    
    response_time = meter.create_histogram(
        name="agent_response_time",
        description="Tiempo de respuesta del agente en segundos",
        unit="s"
    )
    
    has_telemetry = True
except ImportError:
    # Fallback si OpenTelemetry no está disponible
    has_telemetry = False
    tracer = None
    request_counter = None
    response_time = None

# Configurar logger
logger = get_logger(__name__)

class EliteTrainingStrategist(ADKAgent):
    """
    Agente especializado en diseñar y periodizar programas de entrenamiento 
    para atletas de alto rendimiento.
    
    Este agente utiliza el modelo Gemini para generar planes de entrenamiento
    personalizados basados en los objetivos, nivel y restricciones del atleta.
    Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        """
        Inicializa el agente EliteTrainingStrategist.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
            state_manager: Gestor de estados para persistencia (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "elite_training",
            "performance_analysis",
            "periodization",
            "exercise_prescription"
        ]
        
        skills = [
            {
                "name": "generate_training_plan",
                "description": "Genera un plan de entrenamiento personalizado"
            },
            {
                "name": "analyze_performance",
                "description": "Analiza el rendimiento de un atleta"
            },
            {
                "name": "periodization",
                "description": "Diseña periodización de entrenamiento a corto y largo plazo"
            },
            {
                "name": "exercise_prescription",
                "description": "Prescribe ejercicios específicos basados en objetivos y capacidades"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito un plan de entrenamiento para un maratón en 12 semanas"},
                "output": {"response": "Aquí tienes un plan de entrenamiento de 12 semanas para preparar un maratón..."}
            },
            {
                "input": {"message": "Analiza mi rendimiento en la última carrera: 10km en 45 minutos"},
                "output": {"response": "Basado en tu tiempo de 10km en 45 minutos, tu ritmo promedio es de 4:30 min/km..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="elite_training_strategist",
            name="Elite Training Strategist",
            description="Agente especializado en diseñar y periodizar programas de entrenamiento para atletas de alto rendimiento",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            state_manager=state_manager,
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.mcp_client = MCPClient()
        
        # Inicializar el StateManager para persistencia
        self.state_manager = state_manager or StateManager()
        
        # Inicializar estado del agente
        self.update_state("training_plans", {})  # Almacenar planes de entrenamiento generados
        self.update_state("performance_analyses", {})  # Almacenar análisis de rendimiento
        self.update_state("conversation_contexts", {})  # Almacenar contextos de conversación
        
        logger.info(f"EliteTrainingStrategist inicializado con {len(capabilities)} capacidades")
    
    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # Registrar métrica de solicitud si telemetría está disponible
        if has_telemetry and request_counter:
            request_counter.add(1, {"agent_id": self.agent_id, "user_id": user_id or "anonymous"})
            
        # Crear span para trazar la ejecución si telemetría está disponible
        if has_telemetry and tracer:
            with tracer.start_as_current_span("elite_training_strategist_process_request") as span:
                span.set_attribute("user_id", user_id or "anonymous")
                span.set_attribute("session_id", session_id or "none")
                span.set_attribute("input_length", len(input_text))
                
                # Medir tiempo de respuesta
                start_time = time.time()
                result = await self._process_request(input_text, user_id, session_id, **kwargs)
                end_time = time.time()
                
                # Registrar métrica de tiempo de respuesta
                if response_time:
                    response_time.record(end_time - start_time, {"agent_id": self.agent_id})
                    
                return result
        else:
            # Ejecución sin telemetría
            return await self._process_request(input_text, user_id, session_id, **kwargs)
    
    async def _process_request(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente EliteTrainingStrategist.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en entrenamiento de alto rendimiento.
        
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
            logger.info(f"Ejecutando EliteTrainingStrategist con input: {input_text[:50]}...")
            
            # Generar ID de sesión si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generando nuevo session_id: {session_id}")
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)
            
            # Cargar el contexto de la conversación utilizando el método _get_context
            # Este método ya maneja la carga desde StateManager o memoria según corresponda
            context = await self._get_context(user_id, session_id)
            
            # Añadir información del perfil de usuario al contexto
            if user_profile:
                context["user_name"] = user_profile.get("name", "Atleta")
                context["experience_level"] = user_profile.get("experience_level", "intermedio")
                context["age"] = user_profile.get("age", "adulto")
                context["goals"] = user_profile.get("goals", [])
                context["sport"] = user_profile.get("sport", "deporte")
            
            # Determinar el tipo de solicitud basado en palabras clave
            if any(keyword in input_text.lower() for keyword in ["plan", "programa", "entrenamiento", "rutina"]):
                # Generar plan de entrenamiento
                response = await self._generate_training_plan(input_text, context)
                response_type = "training_plan"
                
                # Guardar el plan en el estado del agente
                if user_id:
                    plans = self.get_state("training_plans", {})
                    plans[user_id] = plans.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "plan": response
                    }]
                    self.update_state("training_plans", plans)
                    
            elif any(keyword in input_text.lower() for keyword in ["analiza", "rendimiento", "resultado", "tiempo", "carrera"]):
                # Analizar rendimiento
                response = await self._analyze_performance(input_text, context)
                response_type = "performance_analysis"
                
                # Guardar el análisis en el estado del agente
                if user_id:
                    analyses = self.get_state("performance_analyses", {})
                    analyses[user_id] = analyses.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "analysis": response
                    }]
                    self.update_state("performance_analyses", analyses)
                    
            else:
                # Respuesta general sobre entrenamiento
                response = await self._generate_training_plan(input_text, context)
                response_type = "general_response"
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, response)
            
            # Actualizar contexto y persistir en StateManager
            await self._update_context(user_id, session_id, input_text, response)
            
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
            logger.error(f"Error en EliteTrainingStrategist: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de entrenamiento.",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _generate_training_plan(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Genera un plan de entrenamiento personalizado utilizando el modelo Gemini.
        
        Args:
            input_text: Texto de entrada del usuario con la solicitud del plan
            context: Contexto adicional como historial, preferencias, etc.
            
        Returns:
            str: Plan de entrenamiento generado y formateado
        """
        try:
            # Intentar usar la skill registrada
            result = await self.execute_skill("generate_training_plan", 
                                             input_text=input_text, 
                                             context=context)
            return result
        except (ValueError, AttributeError) as e:
            # Fallback a implementación directa si la skill no está disponible
            self.logger.warning(f"Skill 'generate_training_plan' no disponible, usando fallback: {e}")
            
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un entrenador de élite especializado en diseñar programas de entrenamiento personalizados.
            Genera un plan de entrenamiento detallado basado en la siguiente solicitud:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación inicial de la solicitud
            2. Objetivos claros y medibles
            3. Periodización del entrenamiento
            4. Desglose semanal de sesiones
            5. Ejercicios específicos con series, repeticiones y descansos
            6. Recomendaciones de nutrición y recuperación
            7. Métricas para evaluar el progreso
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de conversaciones previas:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Registrar la generación
            self.logger.info(f"Generando plan de entrenamiento para: {input_text[:50]}...")
            
            # Generar plan con Gemini
            plan = await self.gemini_client.generate_content(prompt)
            
            # Registrar éxito
            self.logger.info(f"Plan de entrenamiento generado exitosamente: {len(plan)} caracteres")
            
            return plan
    
    async def _analyze_performance(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Analiza el rendimiento de un atleta utilizando el modelo Gemini.
        
        Args:
            input_text: Texto de entrada del usuario con los datos de rendimiento
            context: Contexto adicional como historial, métricas previas, etc.
            
        Returns:
            str: Análisis de rendimiento detallado y formateado
        """
        try:
            # Intentar usar la skill registrada
            result = await self.execute_skill("analyze_performance", 
                                             input_text=input_text, 
                                             context=context)
            return result
        except (ValueError, AttributeError) as e:
            # Fallback a implementación directa si la skill no está disponible
            self.logger.warning(f"Skill 'analyze_performance' no disponible, usando fallback: {e}")
            
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un analista de rendimiento deportivo especializado en evaluar datos de entrenamiento.
            Analiza los siguientes datos de rendimiento y proporciona insights detallados:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación de los datos proporcionados
            2. Comparación con estándares para el nivel del atleta
            3. Identificación de fortalezas y áreas de mejora
            4. Recomendaciones específicas para mejorar
            5. Objetivos realistas a corto y medio plazo
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            Incluye datos cuantitativos cuando sea posible.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de análisis previos:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Registrar el análisis
            self.logger.info(f"Analizando rendimiento para: {input_text[:50]}...")
            
            # Generar análisis con Gemini
            analysis = await self.gemini_client.generate_content(prompt)
            
            # Registrar éxito
            self.logger.info(f"Análisis de rendimiento generado exitosamente: {len(analysis)} caracteres")
            
            return analysis
    
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación para un usuario y sesión específicos.
        
        Este método intenta primero obtener el contexto del StateManager para persistencia.
        Si no está disponible, usa el almacenamiento en memoria como fallback.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        # Intentar cargar desde StateManager si hay user_id y session_id
        if user_id and session_id:
            try:
                state_data = await self.state_manager.load_state(user_id, session_id)
                if state_data and "context" in state_data:
                    logger.debug(f"Contexto cargado desde StateManager para session_id={session_id}")
                    return state_data["context"]
            except Exception as e:
                logger.warning(f"Error al cargar contexto desde StateManager: {e}")
        
        # Fallback: Obtener contextos almacenados en memoria
        contexts = self.get_state("conversation_contexts") or {}
        
        # Generar clave de contexto
        context_key = f"{user_id}_{session_id}" if user_id and session_id else "default"
        
        # Obtener o inicializar contexto
        if context_key not in contexts:
            contexts[context_key] = {"history": []}
            self.update_state("conversation_contexts", contexts)
        
        return contexts[context_key]
        
    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], msg: str, resp: str) -> None:
        """
        Actualiza el contexto de la conversación con un nuevo mensaje y respuesta.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            msg: Mensaje del usuario
            resp: Respuesta del bot
        """
        # Obtener contexto actual
        context = await self._get_context(user_id, session_id)
        
        # Añadir nueva interacción al historial
        if "history" not in context:
            context["history"] = []
            
        context["history"].append({"user": msg, "bot": resp, "timestamp": time.time()})
        
        # Limitar el tamaño del historial (mantener últimas 10 interacciones)
        if len(context["history"]) > 10:
            context["history"] = context["history"][-10:]
            
        # Actualizar contexto en memoria
        contexts = self.get_state("conversation_contexts") or {}
        key = f"{user_id}_{session_id}" if user_id and session_id else "default"
        contexts[key] = context
        self.update_state("conversation_contexts", contexts)
        
        # Persistir en StateManager si hay user_id y session_id
        if user_id and session_id:
            try:
                # Guardar contexto en StateManager
                state_data = {"context": context}
                await self.state_manager.save_state(state_data, user_id, session_id)
                logger.debug(f"Contexto actualizado en StateManager para session_id={session_id}")
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager: {e}")
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
        
    async def start(self):
        """
        Inicia el agente, conectándolo al servidor ADK y registrando sus skills.
        """
        # Registrar skills en el toolkit
        await self._register_skills()
        
        # Iniciar agente ADK (conectar al servidor ADK y registrar skills)
        await super().start()
        
    async def _register_skills(self):
        """
        Registra las skills del agente en el toolkit.
        """
        # Skill para generar planes de entrenamiento
        async def generate_training_plan(input_text: str, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un entrenador de élite especializado en diseñar programas de entrenamiento personalizados.
            Genera un plan de entrenamiento detallado basado en la siguiente solicitud:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación inicial de la solicitud
            2. Objetivos claros y medibles
            3. Periodización del entrenamiento
            4. Desglose semanal de sesiones
            5. Ejercicios específicos con series, repeticiones y descansos
            6. Recomendaciones de nutrición y recuperación
            7. Métricas para evaluar el progreso
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de conversaciones previas:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute({
                    "prompt": prompt,
                    "temperature": 0.7,
                    "model": "gemini-2.0-flash"
                })
                return result.get("text", "")
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                return await self.gemini_client.generate_content(prompt)
        
        # Skill para analizar rendimiento
        async def analyze_performance(input_text: str, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un analista de rendimiento deportivo especializado en evaluar datos de entrenamiento.
            Analiza los siguientes datos de rendimiento y proporciona insights detallados:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación de los datos proporcionados
            2. Comparación con estándares para el nivel del atleta
            3. Identificación de fortalezas y áreas de mejora
            4. Recomendaciones específicas para mejorar
            5. Objetivos realistas a corto y medio plazo
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            Incluye datos cuantitativos cuando sea posible.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de análisis previos:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute({
                    "prompt": prompt,
                    "temperature": 0.7,
                    "model": "gemini-2.0-flash"
                })
                return result.get("text", "")
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                return await self.gemini_client.generate_content(prompt)
        
        # Skill para diseñar periodización
        async def design_periodization(input_text: str, weeks: int = 12, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en periodización del entrenamiento deportivo.
            Diseña un plan de periodización de {weeks} semanas basado en la siguiente solicitud:
            
            {input_text}
            
            Incluye:
            1. División en macrociclos, mesociclos y microciclos
            2. Distribución de volumen e intensidad a lo largo del tiempo
            3. Fases de acumulación, transformación y realización
            4. Picos de rendimiento planificados
            5. Estrategias de tapering y supercompensación
            
            Presenta el plan de periodización en formato de tabla con semanas, fases y objetivos principales.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute({
                    "prompt": prompt,
                    "temperature": 0.7,
                    "model": "gemini-2.0-flash"
                })
                return result.get("text", "")
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                return await self.gemini_client.generate_content(prompt)
        
        # Skill para prescribir ejercicios
        async def prescribe_exercises(input_text: str, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en prescripción de ejercicios y biomecánica.
            Prescribe ejercicios específicos basados en la siguiente solicitud:
            
            {input_text}
            
            Para cada ejercicio incluye:
            1. Nombre y variante específica
            2. Músculos principales y secundarios trabajados
            3. Técnica correcta de ejecución
            4. Progresiones y regresiones
            5. Consideraciones de seguridad
            
            Presenta los ejercicios en formato de lista con instrucciones claras y precisas.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute({
                    "prompt": prompt,
                    "temperature": 0.7,
                    "model": "gemini-2.0-flash"
                })
                return result.get("text", "")
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                return await self.gemini_client.generate_content(prompt)
        
        # Registrar skills
        await self.register_skill("generate_training_plan", generate_training_plan)
        await self.register_skill("analyze_performance", analyze_performance)
        await self.register_skill("design_periodization", design_periodization)
        await self.register_skill("prescribe_exercises", prescribe_exercises)
