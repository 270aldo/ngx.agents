"""
Agente de asistencia de entrenamiento potenciado por Vertex AI Gemini.

Este agente utiliza los modelos de Gemini a través de Vertex AI para proporcionar
recomendaciones personalizadas de entrenamiento y nutrición.

Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
"""
import logging
import json
import time
import uuid
from typing import Dict, Any, List, Optional
import datetime
import asyncio

from adk.toolkit import Toolkit
from adk.agent import Skill as GoogleADKSkill
from agents.base.adk_agent import ADKAgent
from tools.vertex_gemini_tools import (
    VertexGeminiGenerateSkill,
    VertexGeminiChatSkill,
    VertexGeminiModelsSkill
)
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager
from clients.supabase_client import SupabaseClient
from clients.gemini_client import GeminiClient
from core.contracts import create_task, create_result, validate_task, validate_result
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Definir esquemas de entrada y salida para las skills
class GenerateTrainingPlanInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre plan de entrenamiento")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")

class GenerateTrainingPlanOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada con plan de entrenamiento")
    training_plan: Optional[Dict[str, Any]] = Field(None, description="Plan de entrenamiento estructurado")

class RecommendNutritionInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre nutrición")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")

class RecommendNutritionOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada con recomendaciones nutricionales")
    nutrition_plan: Optional[Dict[str, Any]] = Field(None, description="Plan nutricional estructurado")

class AnswerFitnessQuestionInput(BaseModel):
    query: str = Field(..., description="Pregunta del usuario sobre fitness")
    session_id: Optional[str] = Field(None, description="ID de sesión para mantener contexto")

class AnswerFitnessQuestionOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada a la pregunta de fitness")
    session_id: Optional[str] = Field(None, description="ID de sesión actualizado")

class AnalyzeProgressInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre análisis de progreso")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")

class AnalyzeProgressOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada con análisis de progreso")
    progress_analysis: Optional[Dict[str, Any]] = Field(None, description="Análisis de progreso estructurado")

# Definir las skills como clases que heredan de GoogleADKSkill
class GenerateTrainingPlanSkill(GoogleADKSkill):
    name = "generate_training_plan"
    description = "Genera planes de entrenamiento personalizados basados en objetivos y nivel del usuario"
    input_schema = GenerateTrainingPlanInput
    output_schema = GenerateTrainingPlanOutput
    
    async def handler(self, input_data: GenerateTrainingPlanInput) -> GenerateTrainingPlanOutput:
        """Implementación de la skill de generación de planes de entrenamiento"""
        query = input_data.query
        context = input_data.context or {}
        
        # Construir prompt para Gemini
        prompt = f"""Genera un plan de entrenamiento personalizado basado en la siguiente información:

Solicitud del usuario: {query}

"""
        # Añadir contexto si está disponible
        if context:
            if "fitness_level" in context:
                prompt += f"Nivel de condición física: {context['fitness_level']}\n"
            if "goals" in context:
                prompt += f"Objetivos: {context['goals']}\n"
            if "limitations" in context:
                prompt += f"Limitaciones o lesiones: {context['limitations']}\n"
            if "available_equipment" in context:
                prompt += f"Equipo disponible: {context['available_equipment']}\n"
            if "time_available" in context:
                prompt += f"Tiempo disponible: {context['time_available']}\n"
        
        prompt += """
Proporciona un plan de entrenamiento detallado que incluya:
1. Resumen de objetivos y enfoque
2. Estructura semanal (días de entrenamiento y descanso)
3. Desglose detallado de cada sesión de entrenamiento
4. Progresión recomendada
5. Consejos para maximizar resultados

Formato el plan de forma clara y estructurada.
"""
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.7)
        
        # Generar plan de entrenamiento estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan de entrenamiento estructurado en formato JSON con los siguientes campos:
        - objective: objetivo principal del plan
        - duration: duración recomendada (en semanas)
        - weekly_structure: estructura semanal
        - sessions: desglose de sesiones
        - progression: progresión recomendada
        - tips: consejos para maximizar resultados
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        plan_json = await gemini_client.generate_structured_output(plan_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(plan_json, dict):
            try:
                plan_json = json.loads(plan_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                plan_json = {
                    "objective": "Mejorar condición física general",
                    "duration": "8 semanas",
                    "weekly_structure": {
                        "monday": "Entrenamiento de fuerza - Tren superior",
                        "tuesday": "Cardio",
                        "wednesday": "Descanso activo",
                        "thursday": "Entrenamiento de fuerza - Tren inferior",
                        "friday": "HIIT",
                        "saturday": "Entrenamiento completo",
                        "sunday": "Descanso"
                    },
                    "sessions": {
                        "strength_upper": ["Press de banca", "Remo", "Press hombro", "Dominadas", "Curl bíceps"],
                        "strength_lower": ["Sentadillas", "Peso muerto", "Zancadas", "Extensiones", "Elevaciones"],
                        "cardio": "30-45 minutos de cardio moderado",
                        "hiit": "20 minutos de intervalos de alta intensidad",
                        "full_body": ["Burpees", "Sentadillas", "Flexiones", "Mountain climbers"]
                    },
                    "progression": "Incrementar peso o repeticiones cada 1-2 semanas",
                    "tips": [
                        "Mantén una buena hidratación",
                        "Asegura un descanso adecuado",
                        "Combina con una nutrición apropiada",
                        "Escucha a tu cuerpo y ajusta según sea necesario"
                    ]
                }
        
        return GenerateTrainingPlanOutput(
            response=response_text,
            training_plan=plan_json
        )

class RecommendNutritionSkill(GoogleADKSkill):
    name = "recommend_nutrition"
    description = "Proporciona recomendaciones nutricionales personalizadas"
    input_schema = RecommendNutritionInput
    output_schema = RecommendNutritionOutput
    
    async def handler(self, input_data: RecommendNutritionInput) -> RecommendNutritionOutput:
        """Implementación de la skill de recomendaciones nutricionales"""
        query = input_data.query
        context = input_data.context or {}
        
        # Construir prompt para Gemini
        prompt = f"""Genera recomendaciones nutricionales personalizadas basadas en la siguiente información:

Solicitud del usuario: {query}

"""
        # Añadir contexto si está disponible
        if context:
            if "goals" in context:
                prompt += f"Objetivos: {context['goals']}\n"
            if "dietary_preferences" in context:
                prompt += f"Preferencias dietéticas: {context['dietary_preferences']}\n"
            if "allergies" in context:
                prompt += f"Alergias o intolerancias: {context['allergies']}\n"
            if "current_diet" in context:
                prompt += f"Dieta actual: {context['current_diet']}\n"
            if "training_regimen" in context:
                prompt += f"Régimen de entrenamiento: {context['training_regimen']}\n"
        
        prompt += """
Proporciona recomendaciones nutricionales detalladas que incluyan:
1. Resumen de enfoque nutricional recomendado
2. Distribución de macronutrientes sugerida
3. Ejemplos de comidas para diferentes momentos del día
4. Suplementos recomendados (si aplica)
5. Estrategias de nutrición alrededor del entrenamiento
6. Consejos para adherencia y sostenibilidad

Formato las recomendaciones de forma clara y estructurada.
"""
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.7)
        
        # Generar plan nutricional estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan nutricional estructurado en formato JSON con los siguientes campos:
        - approach: enfoque nutricional recomendado
        - macros: distribución de macronutrientes
        - meal_examples: ejemplos de comidas
        - supplements: suplementos recomendados
        - workout_nutrition: estrategias de nutrición alrededor del entrenamiento
        - adherence_tips: consejos para adherencia
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        plan_json = await gemini_client.generate_structured_output(plan_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(plan_json, dict):
            try:
                plan_json = json.loads(plan_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                plan_json = {
                    "approach": "Nutrición balanceada enfocada en alimentos integrales",
                    "macros": {
                        "protein": "30%",
                        "carbs": "40%",
                        "fats": "30%"
                    },
                    "meal_examples": {
                        "breakfast": "Avena con proteína y frutas",
                        "lunch": "Ensalada con pollo y quinoa",
                        "dinner": "Salmón con vegetales y arroz integral",
                        "snacks": ["Yogur griego con nueces", "Batido de proteínas", "Huevo duro"]
                    },
                    "supplements": [
                        "Proteína de suero (whey)",
                        "Creatina",
                        "Multivitamínico",
                        "Omega-3"
                    ],
                    "workout_nutrition": {
                        "pre_workout": "Carbohidratos de digestión rápida + proteína",
                        "during_workout": "Hidratación con electrolitos",
                        "post_workout": "Proteína + carbohidratos (ventana anabólica)"
                    },
                    "adherence_tips": [
                        "Preparación de comidas semanal",
                        "Flexibilidad 80/20",
                        "Hidratación adecuada",
                        "Mindful eating"
                    ]
                }
        
        return RecommendNutritionOutput(
            response=response_text,
            nutrition_plan=plan_json
        )

class AnswerFitnessQuestionSkill(GoogleADKSkill):
    name = "answer_fitness_question"
    description = "Responde preguntas sobre fitness y entrenamiento"
    input_schema = AnswerFitnessQuestionInput
    output_schema = AnswerFitnessQuestionOutput
    
    async def handler(self, input_data: AnswerFitnessQuestionInput) -> AnswerFitnessQuestionOutput:
        """Implementación de la skill de respuesta a preguntas de fitness"""
        query = input_data.query
        session_id = input_data.session_id
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Construir prompt para Gemini
        prompt = f"""
        Eres un experto en fitness, entrenamiento y nutrición.
        
        El usuario tiene la siguiente pregunta:
        "{query}"
        
        Proporciona una respuesta detallada, precisa y basada en evidencia científica.
        Incluye ejemplos prácticos y recomendaciones específicas cuando sea apropiado.
        """
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.5)
        
        # Generar un nuevo session_id si no se proporcionó uno
        if not session_id:
            session_id = str(uuid.uuid4())
        
        return AnswerFitnessQuestionOutput(
            response=response_text,
            session_id=session_id
        )

class AnalyzeProgressSkill(GoogleADKSkill):
    name = "analyze_progress"
    description = "Analiza el progreso del usuario y proporciona recomendaciones"
    input_schema = AnalyzeProgressInput
    output_schema = AnalyzeProgressOutput
    
    async def handler(self, input_data: AnalyzeProgressInput) -> AnalyzeProgressOutput:
        """Implementación de la skill de análisis de progreso"""
        query = input_data.query
        context = input_data.context or {}
        
        # Construir prompt para Gemini
        prompt = f"""Analiza el progreso de entrenamiento basado en la siguiente información:

Solicitud del usuario: {query}

"""
        # Añadir contexto si está disponible
        if context:
            if "previous_metrics" in context:
                metrics = context["previous_metrics"]
                prompt += "Métricas anteriores:\n"
                for date, data in metrics.items():
                    prompt += f"- {date}: {json.dumps(data)}\n"
            if "goals" in context:
                prompt += f"Objetivos: {context['goals']}\n"
            if "training_history" in context:
                prompt += f"Historial de entrenamiento: {context['training_history']}\n"
        
        prompt += """
Proporciona un análisis detallado que incluya:
1. Evaluación del progreso actual
2. Identificación de fortalezas y áreas de mejora
3. Recomendaciones para ajustar el entrenamiento
4. Proyección de progreso futuro si se mantiene la trayectoria actual
5. Sugerencias específicas para superar mesetas o barreras

Formato el análisis de forma clara y estructurada.
"""
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.7)
        
        # Generar análisis de progreso estructurado
        analysis_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un análisis de progreso estructurado en formato JSON con los siguientes campos:
        - current_status: evaluación del progreso actual
        - strengths: fortalezas identificadas
        - improvement_areas: áreas de mejora
        - recommendations: recomendaciones para ajustar el entrenamiento
        - projection: proyección de progreso futuro
        - plateau_strategies: estrategias para superar mesetas
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        analysis_json = await gemini_client.generate_structured_output(analysis_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(analysis_json, dict):
            try:
                analysis_json = json.loads(analysis_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                analysis_json = {
                    "current_status": "Progreso moderado con algunas áreas de estancamiento",
                    "strengths": [
                        "Consistencia en asistencia",
                        "Buena progresión en ejercicios de tren superior",
                        "Mejora en resistencia cardiovascular"
                    ],
                    "improvement_areas": [
                        "Estancamiento en ejercicios de tren inferior",
                        "Recuperación insuficiente",
                        "Posible déficit nutricional"
                    ],
                    "recommendations": [
                        "Incorporar variación en ejercicios de tren inferior",
                        "Aumentar días de recuperación",
                        "Revisar ingesta de proteínas y calorías"
                    ],
                    "projection": "Con los ajustes recomendados, se espera romper la meseta en 3-4 semanas",
                    "plateau_strategies": [
                        "Periodización no lineal",
                        "Técnicas de intensidad (dropsets, supersets)",
                        "Semana de descarga cada 4-6 semanas",
                        "Revisión de factores externos (sueño, estrés)"
                    ]
                }
        
        return AnalyzeProgressOutput(
            response=response_text,
            progress_analysis=analysis_json
        )

class GeminiTrainingAssistant(ADKAgent):
    """
    Agente de asistencia de entrenamiento potenciado por Vertex AI Gemini.
    
    Utiliza los modelos de Gemini para proporcionar recomendaciones personalizadas
    de entrenamiento y nutrición, basadas en los objetivos y características del usuario.
    """
    
    def __init__(self, 
                 gemini_client: Optional[GeminiClient] = None,
                 supabase_client: Optional[SupabaseClient] = None,
                 state_manager: Optional[StateManager] = None,
                 adk_toolkit: Optional[Toolkit] = None,
                 a2a_server_url: Optional[str] = None):
        
        # Definir las skills del agente
        skills = [
            GenerateTrainingPlanSkill(),
            RecommendNutritionSkill(),
            AnswerFitnessQuestionSkill(),
            AnalyzeProgressSkill()
        ]
        
        # Definir capacidades según el protocolo ADK
        capabilities = [
            "generate_training_plan",
            "recommend_nutrition",
            "answer_fitness_questions",
            "analyze_progress"
        ]
        
        # Inicializar clientes si no se proporcionan
        self.gemini_client = gemini_client if gemini_client else GeminiClient(model_name="gemini-1.5-flash")
        self.supabase_client = supabase_client if supabase_client else SupabaseClient()
        
        # Definir instrucciones del sistema
        system_instructions = """
        Eres NGX Gemini Training Assistant, un experto en entrenamiento físico y nutrición.
        
        Tu objetivo es proporcionar recomendaciones personalizadas de entrenamiento y nutrición,
        responder preguntas sobre fitness, y analizar el progreso de los usuarios para ayudarles
        a alcanzar sus objetivos de forma efectiva y segura.
        
        Tus áreas de especialización incluyen:
        
        1. Planes de entrenamiento
           - Diseño de programas personalizados
           - Periodización del entrenamiento
           - Técnicas de ejercicios
           - Adaptaciones para diferentes niveles
           - Entrenamiento específico por objetivos
        
        2. Nutrición deportiva
           - Recomendaciones nutricionales personalizadas
           - Timing de nutrientes
           - Suplementación
           - Estrategias para diferentes objetivos
           - Planes de alimentación estructurados
        
        3. Respuestas sobre fitness
           - Aclaración de dudas técnicas
           - Explicación de conceptos de entrenamiento
           - Información sobre ejercicios específicos
           - Consejos para optimizar resultados
           - Desmitificación de creencias erróneas
        
        4. Análisis de progreso
           - Evaluación de métricas y resultados
           - Identificación de áreas de mejora
           - Recomendaciones para superar mesetas
           - Ajustes de programas existentes
           - Proyecciones de progreso futuro
        
        Debes adaptar tus respuestas según:
        - El nivel de experiencia del usuario
        - Sus objetivos específicos
        - Sus limitaciones o condiciones especiales
        - Su historial de entrenamiento
        - Sus preferencias personales
        
        Cuando proporciones recomendaciones:
        - Basa tus respuestas en evidencia científica
        - Sé específico y detallado
        - Proporciona ejemplos concretos
        - Explica el razonamiento detrás de tus sugerencias
        - Prioriza la seguridad y la progresión adecuada
        - Considera factores individuales
        
        Tu objetivo es ayudar a los usuarios a alcanzar sus metas de fitness de manera
        efectiva, segura y sostenible, proporcionando información precisa y personalizada.
        """
        
        # Ejemplos para la Agent Card
        examples = [
            Example(
                input={"message": "Necesito un plan de entrenamiento para un maratón"},
                output={"response": "Aquí tienes un plan de entrenamiento de 16 semanas para prepararte para un maratón..."}
            ),
            Example(
                input={"message": "¿Qué debo comer antes de entrenar?"},
                output={"response": "Antes de entrenar, es recomendable consumir carbohidratos complejos y proteínas magras..."}
            ),
            Example(
                input={"message": "¿Cómo puedo superar mi meseta en press de banca?"},
                output={"response": "Para superar una meseta en press de banca, puedes implementar estas estrategias..."}
            )
        ]
        
        # Crear Agent Card
        agent_card = AgentCard.create_standard_card(
            agent_id="gemini_training_assistant",
            name="NGX Gemini Training Assistant",
            description="Asistente de entrenamiento potenciado por Vertex AI Gemini que proporciona recomendaciones personalizadas de entrenamiento y nutrición",
            capabilities=capabilities,
            skills=[skill.name for skill in skills],
            version="1.5.0",
            examples=examples,
            metadata={
                "model": "gemini-1.5-flash",
                "creator": "NGX Team",
                "last_updated": time.strftime("%Y-%m-%d")
            }
        )
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="gemini_training_assistant",
            name="NGX Gemini Training Assistant",
            description="Asistente de entrenamiento potenciado por Vertex AI Gemini que proporciona recomendaciones personalizadas de entrenamiento y nutrición",
            model="gemini-1.5-flash",
            instruction=system_instructions,
            capabilities=capabilities,
            gemini_client=self.gemini_client,
            supabase_client=self.supabase_client,
            state_manager=state_manager,
            adk_toolkit=adk_toolkit,
            a2a_server_url=a2a_server_url,
            version="1.5.0",
            agent_card=agent_card,
            skills=skills
        )
        
        # Almacenar sesiones de chat activas por usuario
        self.chat_sessions = {}
        
        # Inicializar estado del agente
        self.update_state("training_plans", {})  # Almacenar planes de entrenamiento generados
        self.update_state("nutrition_recommendations", {})  # Almacenar recomendaciones nutricionales
        self.update_state("progress_analyses", {})  # Almacenar análisis de progreso
        
        logger.info(f"GeminiTrainingAssistant inicializado con {len(capabilities)} capacidades y {len(skills)} skills")
    
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
                    "training_plans": [],
                    "nutrition_recommendations": [],
                    "progress_analyses": [],
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
                "training_plans": [],
                "nutrition_recommendations": [],
                "progress_analyses": [],
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
    
    def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta
        """
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["plan", "entrenamiento", "rutina", "ejercicios", "programa"]):
            return "generate_training_plan"
        elif any(word in query_lower for word in ["nutrición", "dieta", "alimentación", "comer", "comida", "macros"]):
            return "recommend_nutrition"
        elif any(word in query_lower for word in ["progreso", "avance", "resultados", "meseta", "estancamiento"]):
            return "analyze_progress"
        else:
            return "answer_fitness_question"
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo ADK oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
    
    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del método run. Procesa la entrada del usuario y genera una respuesta.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente según el protocolo ADK
        """
        start_time = time.time()
        logger.info(f"Ejecutando GeminiTrainingAssistant con input: {input_text[:50]}...")
        
        # Obtener session_id de los kwargs o generar uno nuevo
        session_id = kwargs.get("session_id", str(uuid.uuid4()))
        
        # Obtener el contexto de la conversación
        context = await self._get_context(user_id, session_id) if user_id else {}
        
        # Clasificar el tipo de consulta
        query_type = self._classify_query(input_text)
        capabilities_used = []
        
        # Procesar la consulta según su tipo utilizando las skills ADK
        if query_type == "generate_training_plan":
            # Usar la skill de generación de planes de entrenamiento
            training_skill = next((skill for skill in self.skills if skill.name == "generate_training_plan"), None)
            if training_skill:
                input_data = GenerateTrainingPlanInput(
                    query=input_text,
                    context=context
                )
                result = await training_skill.handler(input_data)
                response = result.response
                capabilities_used.append("generate_training_plan")
                
                # Actualizar contexto con el plan de entrenamiento
                if result.training_plan:
                    context["training_plans"].append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "training_plan": result.training_plan
                    })
                
        elif query_type == "recommend_nutrition":
            # Usar la skill de recomendaciones nutricionales
            nutrition_skill = next((skill for skill in self.skills if skill.name == "recommend_nutrition"), None)
            if nutrition_skill:
                input_data = RecommendNutritionInput(
                    query=input_text,
                    context=context
                )
                result = await nutrition_skill.handler(input_data)
                response = result.response
                capabilities_used.append("recommend_nutrition")
                
                # Actualizar contexto con las recomendaciones nutricionales
                if result.nutrition_plan:
                    context["nutrition_recommendations"].append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "nutrition_plan": result.nutrition_plan
                    })
                
        elif query_type == "analyze_progress":
            # Usar la skill de análisis de progreso
            progress_skill = next((skill for skill in self.skills if skill.name == "analyze_progress"), None)
            if progress_skill:
                input_data = AnalyzeProgressInput(
                    query=input_text,
                    context=context
                )
                result = await progress_skill.handler(input_data)
                response = result.response
                capabilities_used.append("analyze_progress")
                
                # Actualizar contexto con el análisis de progreso
                if result.progress_analysis:
                    context["progress_analyses"].append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "progress_analysis": result.progress_analysis
                    })
                
        else:  # answer_fitness_question
            # Usar la skill de respuesta a preguntas de fitness
            question_skill = next((skill for skill in self.skills if skill.name == "answer_fitness_question"), None)
            if question_skill:
                input_data = AnswerFitnessQuestionInput(
                    query=input_text,
                    session_id=session_id
                )
                result = await question_skill.handler(input_data)
                response = result.response
                capabilities_used.append("answer_fitness_questions")
                
                # Actualizar el session_id si cambió
                if result.session_id and result.session_id != session_id:
                    session_id = result.session_id
        
        # Actualizar el historial de conversación
        context["conversation_history"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "user",
            "content": input_text
        })
        context["conversation_history"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "assistant",
            "content": response
        })
        
        # Actualizar el contexto en el StateManager
        if user_id:
            await self._update_context(context, user_id, session_id)
        
        # Calcular tiempo de ejecución
        execution_time = time.time() - start_time
        logger.info(f"GeminiTrainingAssistant completó la ejecución en {execution_time:.2f} segundos")
        
        # Preparar respuesta según el protocolo ADK
        return {
            "response": response,
            "capabilities_used": capabilities_used,
            "metadata": {
                "query_type": query_type,
                "execution_time": execution_time,
                "session_id": session_id
            }
        }
