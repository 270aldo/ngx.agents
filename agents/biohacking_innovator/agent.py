import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union
import json
import os
from google.cloud import aiplatform
import datetime
import asyncio
from pydantic import BaseModel, Field

# Importar componentes de Google ADK
from adk.toolkit import Toolkit
from adk.agent import Skill as GoogleADKSkill

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.adk_agent import ADKAgent
from core.agent_card import AgentCard, Example
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

# Definir esquemas de entrada y salida para las skills
class BiohackingProtocolInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre biohacking")
    age: Optional[int] = Field(None, description="Edad del usuario")
    gender: Optional[str] = Field(None, description="Género del usuario")
    health_conditions: Optional[List[str]] = Field(None, description="Condiciones de salud del usuario")
    goals: Optional[List[str]] = Field(None, description="Objetivos del usuario")

class BiohackingProtocolOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre el protocolo de biohacking")
    protocol: Dict[str, Any] = Field(..., description="Protocolo de biohacking estructurado")
    resources: Optional[List[Dict[str, Any]]] = Field(None, description="Recursos científicos relevantes")

class LongevityStrategyInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre longevidad")
    age: Optional[int] = Field(None, description="Edad del usuario")
    health_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil de salud del usuario")

class LongevityStrategyOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre estrategias de longevidad")
    strategies: List[Dict[str, Any]] = Field(..., description="Estrategias de longevidad recomendadas")
    scientific_basis: Optional[str] = Field(None, description="Base científica de las recomendaciones")

class CognitiveEnhancementInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre mejora cognitiva")
    cognitive_goals: Optional[List[str]] = Field(None, description="Objetivos cognitivos específicos")
    current_supplements: Optional[List[str]] = Field(None, description="Suplementos actuales del usuario")

class CognitiveEnhancementOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre mejora cognitiva")
    protocol: Dict[str, Any] = Field(..., description="Protocolo de mejora cognitiva")
    supplements: Optional[List[Dict[str, Any]]] = Field(None, description="Suplementos recomendados")

class HormonalOptimizationInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre optimización hormonal")
    age: Optional[int] = Field(None, description="Edad del usuario")
    gender: Optional[str] = Field(None, description="Género del usuario")
    hormone_concerns: Optional[List[str]] = Field(None, description="Preocupaciones hormonales específicas")

class HormonalOptimizationOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre optimización hormonal")
    protocol: Dict[str, Any] = Field(..., description="Protocolo de optimización hormonal")
    lifestyle_changes: List[str] = Field(..., description="Cambios de estilo de vida recomendados")
    supplements: Optional[List[Dict[str, Any]]] = Field(None, description="Suplementos recomendados")

# Definir las skills como clases que heredan de GoogleADKSkill
class BiohackingProtocolSkill(GoogleADKSkill):
    name = "biohacking_protocol"
    description = "Desarrolla protocolos personalizados de biohacking basados en la ciencia más reciente"
    input_schema = BiohackingProtocolInput
    output_schema = BiohackingProtocolOutput
    
    async def handler(self, input_data: BiohackingProtocolInput) -> BiohackingProtocolOutput:
        """Implementación de la skill de protocolo de biohacking"""
        query = input_data.query
        age = input_data.age
        gender = input_data.gender
        health_conditions = input_data.health_conditions or []
        goals = input_data.goals or []
        
        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en biohacking y optimización biológica.
        
        El usuario solicita un protocolo de biohacking con la siguiente consulta:
        "{query}"
        
        Información del usuario:
        - Edad: {age if age else "No especificada"}
        - Género: {gender if gender else "No especificado"}
        - Condiciones de salud: {', '.join(health_conditions) if health_conditions else "No especificadas"}
        - Objetivos: {', '.join(goals) if goals else "No especificados"}
        
        Proporciona un protocolo de biohacking detallado y personalizado, basado en evidencia científica.
        Incluye recomendaciones específicas sobre dieta, suplementos, ejercicio, sueño, y otras intervenciones relevantes.
        Estructura tu respuesta en secciones claras y proporciona una justificación científica para cada recomendación.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.7)
        
        # Generar protocolo estructurado
        protocol_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un protocolo de biohacking estructurado en formato JSON con los siguientes campos:
        - objective: objetivo principal del protocolo
        - duration: duración recomendada
        - interventions: objeto con intervenciones (diet, supplements, exercise, sleep, etc.)
        - schedule: cronograma diario/semanal
        - metrics: métricas para seguimiento
        - precautions: precauciones y contraindicaciones
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        protocol_json = await gemini_client.generate_structured_output(protocol_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(protocol_json, dict):
            try:
                protocol_json = json.loads(protocol_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                protocol_json = {
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
        
        # Buscar recursos científicos relevantes (simulado)
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
            }
        ]
        
        return BiohackingProtocolOutput(
            response=response_text,
            protocol=protocol_json,
            resources=resources
        )

class LongevityStrategySkill(GoogleADKSkill):
    name = "longevity_strategy"
    description = "Proporciona estrategias basadas en evidencia científica para extender la vida saludable"
    input_schema = LongevityStrategyInput
    output_schema = LongevityStrategyOutput
    
    async def handler(self, input_data: LongevityStrategyInput) -> LongevityStrategyOutput:
        """Implementación de la skill de estrategias de longevidad"""
        query = input_data.query
        age = input_data.age
        health_profile = input_data.health_profile or {}
        
        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en longevidad y medicina antienvejecimiento.
        
        El usuario solicita estrategias de longevidad con la siguiente consulta:
        "{query}"
        
        Información del usuario:
        - Edad: {age if age else "No especificada"}
        - Perfil de salud: {json.dumps(health_profile, indent=2) if health_profile else "No especificado"}
        
        Proporciona estrategias detalladas y basadas en evidencia científica para extender la vida saludable
        y retrasar los procesos de envejecimiento. Incluye intervenciones respaldadas por estudios científicos
        y explica los mecanismos biológicos involucrados.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear estrategias de longevidad (simplificadas)
        strategies = [
            {
                "name": "Restricción calórica moderada",
                "description": "Reducción del 15-20% de calorías sin malnutrición",
                "evidence_level": "Alta",
                "mechanisms": ["Activación de sirtuinas", "Reducción de IGF-1", "Autofagia"]
            },
            {
                "name": "Ayuno intermitente",
                "description": "Ventana de alimentación de 8 horas con 16 horas de ayuno",
                "evidence_level": "Media-Alta",
                "mechanisms": ["Autofagia", "Reducción de inflamación", "Mejora de sensibilidad a insulina"]
            },
            {
                "name": "Ejercicio de resistencia",
                "description": "Entrenamiento con pesas 2-3 veces por semana",
                "evidence_level": "Alta",
                "mechanisms": ["Preservación de masa muscular", "Mejora de sensibilidad a insulina", "Aumento de hormona de crecimiento"]
            }
        ]
        
        scientific_basis = "Las estrategias recomendadas se basan en estudios que demuestran la activación de vías moleculares asociadas con la longevidad, como las sirtuinas, AMPK, y la reducción de mTOR. Estas vías están involucradas en procesos celulares que promueven la reparación del ADN, la autofagia, y la reducción del estrés oxidativo."
        
        return LongevityStrategyOutput(
            response=response_text,
            strategies=strategies,
            scientific_basis=scientific_basis
        )

class CognitiveEnhancementSkill(GoogleADKSkill):
    name = "cognitive_enhancement"
    description = "Diseña estrategias personalizadas para optimizar la función cerebral"
    input_schema = CognitiveEnhancementInput
    output_schema = CognitiveEnhancementOutput
    
    async def handler(self, input_data: CognitiveEnhancementInput) -> CognitiveEnhancementOutput:
        """Implementación de la skill de mejora cognitiva"""
        query = input_data.query
        cognitive_goals = input_data.cognitive_goals or []
        current_supplements = input_data.current_supplements or []
        
        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en neurociencia y mejora cognitiva.
        
        El usuario solicita estrategias de mejora cognitiva con la siguiente consulta:
        "{query}"
        
        Información del usuario:
        - Objetivos cognitivos: {', '.join(cognitive_goals) if cognitive_goals else "No especificados"}
        - Suplementos actuales: {', '.join(current_supplements) if current_supplements else "No especificados"}
        
        Proporciona un protocolo detallado para optimizar la función cerebral, mejorar la memoria, concentración y claridad mental.
        Incluye recomendaciones sobre suplementos, ejercicios mentales, nutrición, sueño y otras intervenciones relevantes.
        Basa tus recomendaciones en evidencia científica y explica los mecanismos neurológicos involucrados.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear protocolo de mejora cognitiva (simplificado)
        protocol = {
            "objective": "Optimización de la función cognitiva",
            "duration": "12 semanas",
            "interventions": {
                "nutrition": "Dieta mediterránea con énfasis en ácidos grasos omega-3, antioxidantes y alimentos ricos en colina",
                "supplements": "Bacopa monnieri, fosfatidilserina, omega-3 DHA/EPA, magnesio L-treonato",
                "exercise": "Ejercicio cardiovascular de intensidad moderada 30 minutos diarios, 5 días por semana",
                "sleep": "Optimización del sueño con 7-8 horas de calidad, consistencia en horarios y rutina de relajación",
                "mental_training": "Meditación de atención plena 20 minutos diarios, entrenamiento cognitivo con aplicaciones como Lumosity o Dual N-Back"
            },
            "metrics": [
                "Pruebas cognitivas estandarizadas (Cambridge Brain Sciences)",
                "Tiempo de reacción",
                "Capacidad de memoria de trabajo",
                "Niveles subjetivos de claridad mental y concentración"
            ]
        }
        
        # Crear lista de suplementos recomendados
        supplements = [
            {
                "name": "Bacopa Monnieri",
                "dosage": "300-600 mg diarios",
                "timing": "Con comidas",
                "benefits": "Mejora de memoria y reducción de ansiedad",
                "mechanism": "Aumento de circulación cerebral y modulación de neurotransmisores"
            },
            {
                "name": "Fosfatidilserina",
                "dosage": "100 mg, 3 veces al día",
                "timing": "Con comidas",
                "benefits": "Mejora de memoria y función cognitiva",
                "mechanism": "Componente estructural de membranas neuronales"
            },
            {
                "name": "Omega-3 DHA/EPA",
                "dosage": "1-2 g diarios",
                "timing": "Con comidas",
                "benefits": "Mejora de función cognitiva y salud cerebral",
                "mechanism": "Componente estructural de membranas neuronales y reducción de inflamación"
            }
        ]
        
        return CognitiveEnhancementOutput(
            response=response_text,
            protocol=protocol,
            supplements=supplements
        )

class HormonalOptimizationSkill(GoogleADKSkill):
    name = "hormonal_optimization"
    description = "Desarrolla estrategias para optimizar naturalmente el equilibrio hormonal"
    input_schema = HormonalOptimizationInput
    output_schema = HormonalOptimizationOutput
    
    async def handler(self, input_data: HormonalOptimizationInput) -> HormonalOptimizationOutput:
        """Implementación de la skill de optimización hormonal"""
        query = input_data.query
        age = input_data.age
        gender = input_data.gender
        hormone_concerns = input_data.hormone_concerns or []
        
        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en endocrinología y optimización hormonal natural.
        
        El usuario solicita estrategias de optimización hormonal con la siguiente consulta:
        "{query}"
        
        Información del usuario:
        - Edad: {age if age else "No especificada"}
        - Género: {gender if gender else "No especificado"}
        - Preocupaciones hormonales: {', '.join(hormone_concerns) if hormone_concerns else "No especificadas"}
        
        Proporciona un protocolo detallado para optimizar naturalmente el equilibrio hormonal y mejorar la salud metabólica.
        Incluye recomendaciones sobre nutrición, ejercicio, gestión del estrés, sueño, suplementos y otras intervenciones relevantes.
        Basa tus recomendaciones en evidencia científica y explica los mecanismos endocrinos involucrados.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear protocolo de optimización hormonal (simplificado)
        protocol = {
            "objective": "Optimización del equilibrio hormonal natural",
            "duration": "12 semanas",
            "target_hormones": ["Testosterona", "Cortisol", "Insulina", "Hormona de crecimiento"],
            "interventions": {
                "nutrition": "Dieta rica en grasas saludables, proteínas de calidad y carbohidratos complejos",
                "supplements": "Zinc, magnesio, vitamina D, ashwagandha",
                "exercise": "Entrenamiento de fuerza con ejercicios compuestos 3-4 veces por semana",
                "sleep": "Priorización del sueño con 7-9 horas de calidad en habitación fría y oscura",
                "stress_management": "Meditación diaria, técnicas de respiración y tiempo en la naturaleza"
            },
            "metrics": [
                "Niveles hormonales en sangre (testosterona total/libre, estradiol, SHBG, cortisol)",
                "Composición corporal (% grasa corporal, masa muscular)",
                "Calidad del sueño",
                "Niveles de energía y estado de ánimo"
            ]
        }
        
        # Crear lista de cambios de estilo de vida recomendados
        lifestyle_changes = [
            "Exposición a luz solar matutina (10-20 min) para regular ritmos circadianos y vitamina D",
            "Minimización de disruptores endocrinos (plásticos, alimentos ultraprocesados)",
            "Ayuno intermitente 14-16 horas para optimizar sensibilidad a insulina y hormona de crecimiento",
            "Técnicas de gestión del estrés para reducir cortisol crónico",
            "Entrenamiento de fuerza con ejercicios compuestos para optimizar testosterona y hormona de crecimiento",
            "Optimización del sueño para maximizar la producción hormonal nocturna"
        ]
        
        # Crear lista de suplementos recomendados
        supplements = [
            {
                "name": "Zinc",
                "dosage": "15-30 mg diarios",
                "timing": "Con comidas",
                "benefits": "Soporte de producción de testosterona",
                "mechanism": "Cofactor en la síntesis de testosterona"
            },
            {
                "name": "Magnesio",
                "dosage": "200-400 mg diarios",
                "timing": "Antes de dormir",
                "benefits": "Mejora de calidad del sueño y reducción de cortisol",
                "mechanism": "Regulación de GABA y función muscular"
            },
            {
                "name": "Ashwagandha",
                "dosage": "300-600 mg diarios",
                "timing": "Mañana y noche",
                "benefits": "Reducción de cortisol y soporte de testosterona",
                "mechanism": "Modulación del eje HPA y reducción del estrés"
            }
        ]
        
        return HormonalOptimizationOutput(
            response=response_text,
            protocol=protocol,
            lifestyle_changes=lifestyle_changes,
            supplements=supplements
        )

class BiohackingInnovator(ADKAgent):
    """
    Agente especializado en biohacking y optimización biológica.
    
    Este agente proporciona recomendaciones avanzadas sobre biohacking, 
    incluyendo técnicas de optimización hormonal, mejora cognitiva, 
    y estrategias para mejorar la longevidad y el rendimiento biológico.
    """
    
    def __init__(
        self,
        agent_id: str = None,
        gemini_client: GeminiClient = None,
        supabase_client: SupabaseClient = None,
        mcp_toolkit: MCPToolkit = None,
        state_manager = None,
        **kwargs
    ):
        """Inicializa el agente BiohackingInnovator con sus dependencias"""
        
        # Generar ID único si no se proporciona
        if agent_id is None:
            agent_id = f"biohacking_innovator_{uuid.uuid4().hex[:8]}"
        
        # Crear tarjeta de agente
        agent_card = AgentCard(
            name="BiohackingInnovator",
            description="Especialista en técnicas avanzadas de biohacking, optimización biológica, longevidad y mejora cognitiva",
            instructions="""
            Soy un agente especializado en biohacking y optimización biológica.
            
            Puedo ayudarte con:
            - Protocolos personalizados de biohacking basados en evidencia científica
            - Estrategias para mejorar la longevidad y retrasar el envejecimiento
            - Técnicas para optimizar el rendimiento cognitivo y la claridad mental
            - Métodos para optimizar naturalmente el equilibrio hormonal
            - Tecnologías y dispositivos para monitoreo biológico
            
            Mis recomendaciones se basan en la ciencia más reciente y consideran tu perfil individual,
            incluyendo edad, género, objetivos y condiciones de salud existentes.
            """,
            examples=[
                Example(
                    input="¿Puedes recomendarme un protocolo de biohacking para principiantes?",
                    output="Aquí tienes un protocolo de biohacking para principiantes basado en evidencia científica..."
                ),
                Example(
                    input="¿Qué estrategias puedo implementar para mejorar mi longevidad?",
                    output="Para mejorar tu longevidad, te recomiendo las siguientes estrategias basadas en evidencia..."
                ),
                Example(
                    input="¿Cómo puedo mejorar mi rendimiento cognitivo de forma natural?",
                    output="Para optimizar tu rendimiento cognitivo, te recomiendo este protocolo personalizado..."
                ),
                Example(
                    input="¿Qué puedo hacer para optimizar mis niveles hormonales naturalmente?",
                    output="Para optimizar tu equilibrio hormonal de forma natural, considera estas intervenciones..."
                )
            ]
        )
        
        # Crear toolkit con las skills del agente
        toolkit = Toolkit(
            skills=[
                BiohackingProtocolSkill(),
                LongevityStrategySkill(),
                CognitiveEnhancementSkill(),
                HormonalOptimizationSkill()
            ]
        )
        
        # Inicializar la clase base
        super().__init__(
            agent_id=agent_id,
            agent_card=agent_card,
            toolkit=toolkit,
            gemini_client=gemini_client,
            supabase_client=supabase_client,
            mcp_toolkit=mcp_toolkit,
            state_manager=None,  # Ya no usamos el state_manager original
            **kwargs
        )
        
        logger.info(f"Agente BiohackingInnovator inicializado con ID: {agent_id}")
    
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
            # Intentar cargar el contexto desde el adaptador del StateManager
            context = await state_manager_adapter.load_state(user_id, session_id)
            
            if not context or not context.get("state_data"):
                logger.info(f"No se encontró contexto en el adaptador del StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto.")
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
                logger.info(f"Contexto cargado desde el adaptador del StateManager para user_id={user_id}, session_id={session_id}")
            
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
            
            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(user_id, session_id, context)
            logger.info(f"Contexto actualizado en el adaptador del StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    async def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando el adaptador del Intent Analyzer.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        try:
            # Utilizar el adaptador del Intent Analyzer para analizar la intención
            intent_analysis = await intent_analyzer_adapter.analyze_intent(query)
            
            # Mapear la intención primaria a los tipos de consulta del agente
            primary_intent = intent_analysis.get("primary_intent", "").lower()
            
            # Mapeo de intenciones a tipos de consulta
            intent_to_query_type = {
                "hormonal": "hormonal_optimization",
                "hormonal_optimization": "hormonal_optimization",
                "cognitive": "cognitive_enhancement",
                "cognitive_enhancement": "cognitive_enhancement",
                "longevity": "longevity",
                "biohacking": "biohacking"
            }
            
            # Buscar coincidencias exactas
            if primary_intent in intent_to_query_type:
                return intent_to_query_type[primary_intent]
            
            # Buscar coincidencias parciales
            for intent, query_type in intent_to_query_type.items():
                if intent in primary_intent:
                    return query_type
            
            # Si no hay coincidencias, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
        except Exception as e:
            logger.error(f"Error al clasificar consulta con Intent Analyzer: {e}", exc_info=True)
            # En caso de error, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
    
    def _classify_query_by_keywords(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando palabras clave.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()
        
        # Palabras clave para biohacking general
        biohacking_keywords = [
            "biohacking", "protocolo", "optimización", "rendimiento", "mejora", 
            "monitoreo", "dispositivos", "wearables", "autoexperimentación"
        ]
        
        # Palabras clave para longevidad
        longevity_keywords = [
            "longevidad", "envejecimiento", "antienvejecimiento", "vida saludable", 
            "esperanza de vida", "telómeros", "sirtuinas", "senolíticos"
        ]
        
        # Palabras clave para mejora cognitiva
        cognitive_keywords = [
            "cognitivo", "cerebro", "memoria", "concentración", "claridad mental", 
            "nootropicos", "rendimiento mental", "niebla mental", "focus"
        ]
        
        # Palabras clave para optimización hormonal
        hormonal_keywords = [
            "hormonal", "testosterona", "estrógeno", "cortisol", "tiroides", 
            "insulina", "hormona de crecimiento", "equilibrio hormonal"
        ]
        
        # Verificar coincidencias con palabras clave
        for keyword in hormonal_keywords:
            if keyword in query_lower:
                return "hormonal_optimization"
                
        for keyword in cognitive_keywords:
            if keyword in query_lower:
                return "cognitive_enhancement"
                
        for keyword in longevity_keywords:
            if keyword in query_lower:
                return "longevity"
                
        for keyword in biohacking_keywords:
            if keyword in query_lower:
                return "biohacking"
                
        # Si no hay coincidencias, devolver tipo general
        return "biohacking"
    
    async def _consult_other_agent(self, agent_id: str, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta a otro agente utilizando el adaptador de A2A.
        
        Args:
            agent_id: ID del agente a consultar
            query: Consulta a enviar al agente
            user_id: ID del usuario
            session_id: ID de la sesión
            context: Contexto adicional para la consulta
            
        Returns:
            Dict[str, Any]: Respuesta del agente consultado
        """
        try:
            # Crear contexto para la consulta
            task_context = {
                "user_id": user_id,
                "session_id": session_id,
                "additional_context": context or {}
            }
            
            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id,
                user_input=query,
                context=task_context
            )
            
            logger.info(f"Respuesta recibida del agente {agent_id}")
            return response
        except Exception as e:
            logger.error(f"Error al consultar al agente {agent_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al consultar al agente {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id
            }
    
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
        logger.info(f"Ejecutando BiohackingInnovator con input: {input_text[:50]}...")
        
        # Obtener session_id de los kwargs o generar uno nuevo
        session_id = kwargs.get("session_id", str(uuid.uuid4()))
        
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
        
        # Clasificar el tipo de consulta utilizando el adaptador del Intent Analyzer
        query_type = await self._classify_query(input_text)
        capabilities_used = []
        
        # Procesar la consulta según su tipo utilizando las skills ADK
        if query_type == "biohacking":
            # Usar la skill de protocolo de biohacking
            biohacking_skill = next((skill for skill in self.skills if skill.name == "biohacking_protocol"), None)
            if biohacking_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                age = user_profile.get("age") if user_profile else None
                gender = user_profile.get("gender") if user_profile else None
                health_conditions = user_profile.get("health_conditions", []) if user_profile else []
                goals = user_profile.get("goals", []) if user_profile else []
                
                input_data = BiohackingProtocolInput(
                    query=input_text,
                    age=age,
                    gender=gender,
                    health_conditions=health_conditions,
                    goals=goals
                )
                result = await biohacking_skill.handler(input_data)
                response = result.response
                capabilities_used.append("biohacking")
                
                # Actualizar contexto con el protocolo
                context["protocols"].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "type": "biohacking",
                    "query": input_text,
                    "protocol": result.protocol,
                    "resources": result.resources
                })
                
        elif query_type == "longevity":
            # Usar la skill de estrategias de longevidad
            longevity_skill = next((skill for skill in self.skills if skill.name == "longevity_strategy"), None)
            if longevity_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                age = user_profile.get("age") if user_profile else None
                health_profile = {
                    "conditions": user_profile.get("health_conditions", []),
                    "metrics": user_profile.get("metrics", {}),
                    "lifestyle": user_profile.get("lifestyle", {})
                } if user_profile else {}
                
                input_data = LongevityStrategyInput(
                    query=input_text,
                    age=age,
                    health_profile=health_profile
                )
                result = await longevity_skill.handler(input_data)
                response = result.response
                capabilities_used.append("longevity")
                
                # Actualizar contexto con las estrategias de longevidad
                context["protocols"].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "type": "longevity",
                    "query": input_text,
                    "strategies": result.strategies,
                    "scientific_basis": result.scientific_basis
                })
                
        elif query_type == "cognitive_enhancement":
            # Usar la skill de mejora cognitiva
            cognitive_skill = next((skill for skill in self.skills if skill.name == "cognitive_enhancement"), None)
            if cognitive_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                cognitive_goals = user_profile.get("cognitive_goals", []) if user_profile else []
                current_supplements = user_profile.get("supplements", []) if user_profile else []
                
                input_data = CognitiveEnhancementInput(
                    query=input_text,
                    cognitive_goals=cognitive_goals,
                    current_supplements=current_supplements
                )
                result = await cognitive_skill.handler(input_data)
                response = result.response
                capabilities_used.append("cognitive_enhancement")
                
                # Actualizar contexto con el protocolo de mejora cognitiva
                context["protocols"].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "type": "cognitive_enhancement",
                    "query": input_text,
                    "protocol": result.protocol,
                    "supplements": result.supplements
                })
                
        elif query_type == "hormonal_optimization":
            # Usar la skill de optimización hormonal
            hormonal_skill = next((skill for skill in self.skills if skill.name == "hormonal_optimization"), None)
            if hormonal_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                age = user_profile.get("age") if user_profile else None
                gender = user_profile.get("gender") if user_profile else None
                hormone_concerns = user_profile.get("hormone_concerns", []) if user_profile else []
                
                input_data = HormonalOptimizationInput(
                    query=input_text,
                    age=age,
                    gender=gender,
                    hormone_concerns=hormone_concerns
                )
                result = await hormonal_skill.handler(input_data)
                response = result.response
                capabilities_used.append("hormonal_optimization")
                
                # Actualizar contexto con el protocolo de optimización hormonal
                context["protocols"].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "type": "hormonal_optimization",
                    "query": input_text,
                    "protocol": result.protocol,
                    "lifestyle_changes": result.lifestyle_changes,
                    "supplements": result.supplements
                })
        
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
        logger.info(f"BiohackingInnovator completó la ejecución en {execution_time:.2f} segundos")
        
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
