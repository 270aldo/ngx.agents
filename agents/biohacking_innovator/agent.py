import uuid
import time
from typing import Dict, Any, Optional, List, Union
import json
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

# Importar el servicio de clasificación de programas y definiciones
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition

# Configurar logger
logger = get_logger(__name__)


# Definir esquemas de entrada y salida para las skills
class BiohackingProtocolInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre biohacking")
    age: Optional[int] = Field(None, description="Edad del usuario")
    gender: Optional[str] = Field(None, description="Género del usuario")
    health_conditions: Optional[List[str]] = Field(
        None, description="Condiciones de salud del usuario"
    )
    goals: Optional[List[str]] = Field(None, description="Objetivos del usuario")


class BiohackingProtocolOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada sobre el protocolo de biohacking"
    )
    protocol: Dict[str, Any] = Field(
        ..., description="Protocolo de biohacking estructurado"
    )
    resources: Optional[List[Dict[str, Any]]] = Field(
        None, description="Recursos científicos relevantes"
    )


class LongevityStrategyInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre longevidad")
    age: Optional[int] = Field(None, description="Edad del usuario")
    health_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil de salud del usuario"
    )


class LongevityStrategyOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada sobre estrategias de longevidad"
    )
    strategies: List[Dict[str, Any]] = Field(
        ..., description="Estrategias de longevidad recomendadas"
    )
    scientific_basis: Optional[str] = Field(
        None, description="Base científica de las recomendaciones"
    )


class CognitiveEnhancementInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre mejora cognitiva")
    cognitive_goals: Optional[List[str]] = Field(
        None, description="Objetivos cognitivos específicos"
    )
    current_supplements: Optional[List[str]] = Field(
        None, description="Suplementos actuales del usuario"
    )


class CognitiveEnhancementOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre mejora cognitiva")
    protocol: Dict[str, Any] = Field(..., description="Protocolo de mejora cognitiva")
    supplements: Optional[List[Dict[str, Any]]] = Field(
        None, description="Suplementos recomendados"
    )


class HormonalOptimizationInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre optimización hormonal"
    )
    age: Optional[int] = Field(None, description="Edad del usuario")
    gender: Optional[str] = Field(None, description="Género del usuario")
    hormone_concerns: Optional[List[str]] = Field(
        None, description="Preocupaciones hormonales específicas"
    )


class HormonalOptimizationOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada sobre optimización hormonal"
    )
    protocol: Dict[str, Any] = Field(
        ..., description="Protocolo de optimización hormonal"
    )
    lifestyle_changes: List[str] = Field(
        ..., description="Cambios de estilo de vida recomendados"
    )
    supplements: Optional[List[Dict[str, Any]]] = Field(
        None, description="Suplementos recomendados"
    )


class AnalyzeWearableDataInput(BaseModel):
    """Entrada para analizar datos de dispositivos wearables."""

    image_data: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Imagen del dispositivo wearable o captura de pantalla de la app (base64, URL o ruta de archivo)",
    )
    device_type: Optional[str] = Field(
        None, description="Tipo de dispositivo (Oura, Whoop, Apple Watch, Garmin, etc.)"
    )
    metrics_of_interest: Optional[List[str]] = Field(
        None,
        description="Métricas específicas de interés (HRV, sueño, recuperación, etc.)",
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    time_period: Optional[str] = Field(
        None, description="Período de tiempo de los datos (día, semana, mes)"
    )


class WearableMetric(BaseModel):
    """Modelo para una métrica extraída de un dispositivo wearable."""

    name: str = Field(..., description="Nombre de la métrica")
    value: str = Field(..., description="Valor de la métrica")
    unit: Optional[str] = Field(None, description="Unidad de medida")
    interpretation: str = Field(..., description="Interpretación del valor")
    optimal_range: Optional[str] = Field(
        None, description="Rango óptimo para esta métrica"
    )
    confidence: float = Field(..., description="Confianza en la extracción (0.0-1.0)")


class AnalyzeWearableDataOutput(BaseModel):
    """Salida del análisis de datos de dispositivos wearables."""

    device_detected: str = Field(..., description="Dispositivo detectado en la imagen")
    metrics: List[WearableMetric] = Field(
        ..., description="Métricas extraídas e interpretadas"
    )
    analysis_summary: str = Field(..., description="Resumen del análisis de los datos")
    insights: List[str] = Field(..., description="Insights clave basados en los datos")
    recommendations: List[Dict[str, Any]] = Field(
        ..., description="Recomendaciones personalizadas"
    )
    biohacking_opportunities: List[Dict[str, Any]] = Field(
        ..., description="Oportunidades de biohacking basadas en los datos"
    )


class AnalyzeBiomarkerResultsInput(BaseModel):
    """Entrada para analizar resultados de pruebas biológicas."""

    image_data: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Imagen de los resultados de pruebas (base64, URL o ruta de archivo)",
    )
    test_type: Optional[str] = Field(
        None,
        description="Tipo de prueba (análisis de sangre, genética, microbioma, etc.)",
    )
    markers_of_interest: Optional[List[str]] = Field(
        None, description="Biomarcadores específicos de interés"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    health_goals: Optional[List[str]] = Field(
        None, description="Objetivos de salud del usuario"
    )


class BiomarkerResult(BaseModel):
    """Modelo para un resultado de biomarcador."""

    name: str = Field(..., description="Nombre del biomarcador")
    value: str = Field(..., description="Valor del biomarcador")
    unit: Optional[str] = Field(None, description="Unidad de medida")
    reference_range: Optional[str] = Field(None, description="Rango de referencia")
    status: str = Field(..., description="Estado (normal, bajo, alto, óptimo)")
    significance: str = Field(
        ..., description="Significado e importancia del biomarcador"
    )
    confidence: float = Field(..., description="Confianza en la extracción (0.0-1.0)")


class AnalyzeBiomarkerResultsOutput(BaseModel):
    """Salida del análisis de resultados de pruebas biológicas."""

    test_type_detected: str = Field(..., description="Tipo de prueba detectado")
    biomarkers: List[BiomarkerResult] = Field(
        ..., description="Biomarcadores extraídos y analizados"
    )
    analysis_summary: str = Field(
        ..., description="Resumen del análisis de los resultados"
    )
    health_insights: List[str] = Field(
        ..., description="Insights sobre la salud basados en los resultados"
    )
    optimization_strategies: List[Dict[str, Any]] = Field(
        ..., description="Estrategias de optimización recomendadas"
    )
    supplement_recommendations: Optional[List[Dict[str, Any]]] = Field(
        None, description="Suplementos recomendados basados en los resultados"
    )
    lifestyle_recommendations: List[str] = Field(
        ..., description="Recomendaciones de estilo de vida"
    )


# Definir las skills como clases que heredan de GoogleADKSkill
class BiohackingProtocolSkill(GoogleADKSkill):
    name = "biohacking_protocol"
    description = "Desarrolla protocolos personalizados de biohacking basados en la ciencia más reciente"
    input_schema = BiohackingProtocolInput
    output_schema = BiohackingProtocolOutput

    async def handler(
        self, input_data: BiohackingProtocolInput
    ) -> BiohackingProtocolOutput:
        """Implementación de la skill de protocolo de biohacking"""
        query = input_data.query
        age = input_data.age
        gender = input_data.gender
        health_conditions = input_data.health_conditions or []
        goals = input_data.goals or []

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Obtener el tipo de programa del usuario si está disponible
        try:
            # Intentar obtener el tipo de programa del contexto del agente
            program_type = getattr(self.agent, "program_type", "GENERAL")
            program_def = None

            if program_type != "GENERAL":
                program_def = get_program_definition(program_type)
                logger.info(
                    f"Generando protocolo de biohacking para programa {program_type}"
                )
        except Exception as e:
            logger.warning(
                f"Error al obtener tipo de programa: {e}. Usando enfoque general."
            )
            program_type = "GENERAL"
            program_def = None

        # Preparar contexto específico del programa
        program_context = ""
        if program_def:
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            program_context += f"- {program_def.get('description', '')}\n"
            program_context += f"- Objetivo: {program_def.get('objective', '')}\n"

            # Añadir consideraciones especiales para biohacking según el programa
            if program_type == "PRIME":
                program_context += (
                    "\nConsideraciones especiales para biohacking en PRIME:\n"
                )
                program_context += (
                    "- Enfoque en optimización del rendimiento físico y mental\n"
                )
                program_context += "- Protocolos para mejorar la recuperación y reducir la inflamación\n"
                program_context += "- Estrategias para optimizar hormonas relacionadas con el rendimiento\n"
                program_context += (
                    "- Técnicas para mejorar la calidad del sueño y la recuperación\n"
                )
            elif program_type == "LONGEVITY":
                program_context += (
                    "\nConsideraciones especiales para biohacking en LONGEVITY:\n"
                )
                program_context += "- Enfoque en intervenciones que promueven la longevidad y salud a largo plazo\n"
                program_context += (
                    "- Protocolos para optimizar biomarcadores de envejecimiento\n"
                )
                program_context += (
                    "- Estrategias para mejorar la salud mitocondrial y celular\n"
                )
                program_context += "- Técnicas para reducir la inflamación crónica y el estrés oxidativo\n"

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en biohacking y optimización biológica especializado en programas {program_type}.
        
        El usuario solicita un protocolo de biohacking con la siguiente consulta:
        "{query}"
        
        Información del usuario:
        - Edad: {age if age else "No especificada"}
        - Género: {gender if gender else "No especificado"}
        - Condiciones de salud: {', '.join(health_conditions) if health_conditions else "No especificadas"}
        - Objetivos: {', '.join(goals) if goals else "No especificados"}
        {program_context}
        
        Proporciona un protocolo de biohacking detallado y personalizado para el programa {program_type}, basado en evidencia científica.
        Incluye recomendaciones específicas sobre dieta, suplementos, ejercicio, sueño, y otras intervenciones relevantes.
        Estructura tu respuesta en secciones claras y proporciona una justificación científica para cada recomendación.
        """

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.7)

        # Generar protocolo estructurado
        protocol_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Para un usuario del programa {program_type}:
        {program_context}
        
        Genera un protocolo de biohacking estructurado en formato JSON con los siguientes campos:
        - objective: objetivo principal del protocolo adaptado al programa {program_type}
        - duration: duración recomendada
        - program_type: tipo de programa ("{program_type}")
        - interventions: objeto con intervenciones (diet, supplements, exercise, sleep, etc.) adaptadas al programa {program_type}
        - schedule: cronograma diario/semanal
        - metrics: métricas para seguimiento, priorizando las relevantes para {program_type}
        - precautions: precauciones y contraindicaciones
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """

        protocol_json = await gemini_client.generate_structured_output(protocol_prompt)

        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(protocol_json, dict):
            try:
                protocol_json = json.loads(protocol_json)
            except Exception:
                # Si no se puede convertir, crear un diccionario básico
                protocol_json = {
                    "objective": "Protocolo de biohacking personalizado",
                    "duration": "4-8 semanas",
                    "interventions": {
                        "diet": "Alimentación basada en alimentos enteros con ventana de alimentación de 8 horas",
                        "supplements": "Omega-3, Vitamina D, Magnesio",
                        "exercise": "Entrenamiento de alta intensidad 3 veces por semana",
                        "sleep": "Optimización del sueño con 7-9 horas por noche",
                    },
                    "schedule": {
                        "daily": "Exposición a luz natural por la mañana, ejercicio antes del mediodía, cena 3 horas antes de dormir",
                        "weekly": "Entrenamiento de fuerza lunes/miércoles/viernes, sauna 2 veces por semana",
                    },
                    "metrics": [
                        "Variabilidad de la frecuencia cardíaca (HRV)",
                        "Calidad del sueño",
                        "Niveles de energía (escala 1-10)",
                        "Rendimiento cognitivo",
                    ],
                    "precautions": "Consultar con un profesional de la salud antes de iniciar cualquier protocolo, especialmente si tienes condiciones médicas preexistentes",
                }

        # Buscar recursos científicos relevantes (simulado)
        resources = [
            {
                "title": "Effects of Intermittent Fasting on Health, Aging, and Disease",
                "authors": "de Cabo R, Mattson MP",
                "journal": "New England Journal of Medicine",
                "year": 2019,
                "url": "https://www.nejm.org/doi/full/10.1056/NEJMra1905136",
                "findings": "El ayuno intermitente puede mejorar la salud metabólica, aumentar la longevidad y reducir el riesgo de enfermedades.",
            },
            {
                "title": "Impact of Circadian Rhythms on Metabolic Health and Disease",
                "authors": "Panda S",
                "journal": "Cell Metabolism",
                "year": 2016,
                "url": "https://www.cell.com/cell-metabolism/fulltext/S1550-4131(16)30250-9",
                "findings": "La sincronización de la alimentación con los ritmos circadianos puede mejorar significativamente la salud metabólica.",
            },
        ]

        return BiohackingProtocolOutput(
            response=response_text, protocol=protocol_json, resources=resources
        )


class LongevityStrategySkill(GoogleADKSkill):
    name = "longevity_strategy"
    description = "Proporciona estrategias basadas en evidencia científica para extender la vida saludable"
    input_schema = LongevityStrategyInput
    output_schema = LongevityStrategyOutput

    async def handler(
        self, input_data: LongevityStrategyInput
    ) -> LongevityStrategyOutput:
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
                "mechanisms": [
                    "Activación de sirtuinas",
                    "Reducción de IGF-1",
                    "Autofagia",
                ],
            },
            {
                "name": "Ayuno intermitente",
                "description": "Ventana de alimentación de 8 horas con 16 horas de ayuno",
                "evidence_level": "Media-Alta",
                "mechanisms": [
                    "Autofagia",
                    "Reducción de inflamación",
                    "Mejora de sensibilidad a insulina",
                ],
            },
            {
                "name": "Ejercicio de resistencia",
                "description": "Entrenamiento con pesas 2-3 veces por semana",
                "evidence_level": "Alta",
                "mechanisms": [
                    "Preservación de masa muscular",
                    "Mejora de sensibilidad a insulina",
                    "Aumento de hormona de crecimiento",
                ],
            },
        ]

        scientific_basis = "Las estrategias recomendadas se basan en estudios que demuestran la activación de vías moleculares asociadas con la longevidad, como las sirtuinas, AMPK, y la reducción de mTOR. Estas vías están involucradas en procesos celulares que promueven la reparación del ADN, la autofagia, y la reducción del estrés oxidativo."

        return LongevityStrategyOutput(
            response=response_text,
            strategies=strategies,
            scientific_basis=scientific_basis,
        )


class CognitiveEnhancementSkill(GoogleADKSkill):
    name = "cognitive_enhancement"
    description = "Diseña estrategias personalizadas para optimizar la función cerebral"
    input_schema = CognitiveEnhancementInput
    output_schema = CognitiveEnhancementOutput

    async def handler(
        self, input_data: CognitiveEnhancementInput
    ) -> CognitiveEnhancementOutput:
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
                "mental_training": "Meditación de atención plena 20 minutos diarios, entrenamiento cognitivo con aplicaciones como Lumosity o Dual N-Back",
            },
            "metrics": [
                "Pruebas cognitivas estandarizadas (Cambridge Brain Sciences)",
                "Tiempo de reacción",
                "Capacidad de memoria de trabajo",
                "Niveles subjetivos de claridad mental y concentración",
            ],
        }

        # Crear lista de suplementos recomendados
        supplements = [
            {
                "name": "Bacopa Monnieri",
                "dosage": "300-600 mg diarios",
                "timing": "Con comidas",
                "benefits": "Mejora de memoria y reducción de ansiedad",
                "mechanism": "Aumento de circulación cerebral y modulación de neurotransmisores",
            },
            {
                "name": "Fosfatidilserina",
                "dosage": "100 mg, 3 veces al día",
                "timing": "Con comidas",
                "benefits": "Mejora de memoria y función cognitiva",
                "mechanism": "Componente estructural de membranas neuronales",
            },
            {
                "name": "Omega-3 DHA/EPA",
                "dosage": "1-2 g diarios",
                "timing": "Con comidas",
                "benefits": "Mejora de función cognitiva y salud cerebral",
                "mechanism": "Componente estructural de membranas neuronales y reducción de inflamación",
            },
        ]

        return CognitiveEnhancementOutput(
            response=response_text, protocol=protocol, supplements=supplements
        )


class HormonalOptimizationSkill(GoogleADKSkill):
    name = "hormonal_optimization"
    description = (
        "Desarrolla estrategias para optimizar naturalmente el equilibrio hormonal"
    )
    input_schema = HormonalOptimizationInput
    output_schema = HormonalOptimizationOutput

    async def handler(
        self, input_data: HormonalOptimizationInput
    ) -> HormonalOptimizationOutput:
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
            "target_hormones": [
                "Testosterona",
                "Cortisol",
                "Insulina",
                "Hormona de crecimiento",
            ],
            "interventions": {
                "nutrition": "Dieta rica en grasas saludables, proteínas de calidad y carbohidratos complejos",
                "supplements": "Zinc, magnesio, vitamina D, ashwagandha",
                "exercise": "Entrenamiento de fuerza con ejercicios compuestos 3-4 veces por semana",
                "sleep": "Priorización del sueño con 7-9 horas de calidad en habitación fría y oscura",
                "stress_management": "Meditación diaria, técnicas de respiración y tiempo en la naturaleza",
            },
            "metrics": [
                "Niveles hormonales en sangre (testosterona total/libre, estradiol, SHBG, cortisol)",
                "Composición corporal (% grasa corporal, masa muscular)",
                "Calidad del sueño",
                "Niveles de energía y estado de ánimo",
            ],
        }

        # Crear lista de cambios de estilo de vida recomendados
        lifestyle_changes = [
            "Exposición a luz solar matutina (10-20 min) para regular ritmos circadianos y vitamina D",
            "Minimización de disruptores endocrinos (plásticos, alimentos ultraprocesados)",
            "Ayuno intermitente 14-16 horas para optimizar sensibilidad a insulina y hormona de crecimiento",
            "Técnicas de gestión del estrés para reducir cortisol crónico",
            "Entrenamiento de fuerza con ejercicios compuestos para optimizar testosterona y hormona de crecimiento",
            "Optimización del sueño para maximizar la producción hormonal nocturna",
        ]

        # Crear lista de suplementos recomendados
        supplements = [
            {
                "name": "Zinc",
                "dosage": "15-30 mg diarios",
                "timing": "Con comidas",
                "benefits": "Soporte de producción de testosterona",
                "mechanism": "Cofactor en la síntesis de testosterona",
            },
            {
                "name": "Magnesio",
                "dosage": "200-400 mg diarios",
                "timing": "Antes de dormir",
                "benefits": "Mejora de calidad del sueño y reducción de cortisol",
                "mechanism": "Regulación de GABA y función muscular",
            },
            {
                "name": "Ashwagandha",
                "dosage": "300-600 mg diarios",
                "timing": "Mañana y noche",
                "benefits": "Reducción de cortisol y soporte de testosterona",
                "mechanism": "Modulación del eje HPA y reducción del estrés",
            },
        ]

        return HormonalOptimizationOutput(
            response=response_text,
            protocol=protocol,
            lifestyle_changes=lifestyle_changes,
            supplements=supplements,
        )


class AnalyzeWearableDataSkill(GoogleADKSkill):
    name = "analyze_wearable_data"
    description = "Analiza datos de dispositivos wearables para proporcionar insights y recomendaciones personalizadas"
    input_schema = AnalyzeWearableDataInput
    output_schema = AnalyzeWearableDataOutput

    async def handler(
        self, input_data: AnalyzeWearableDataInput
    ) -> AnalyzeWearableDataOutput:
        """Implementación de la skill de análisis de datos de dispositivos wearables"""
        logger.info(f"Ejecutando skill de análisis de datos de wearables")

        try:
            # Obtener datos de la imagen
            image_data = input_data.image_data
            device_type = input_data.device_type or "No especificado"
            metrics_of_interest = input_data.metrics_of_interest or [
                "HRV",
                "sueño",
                "recuperación",
                "actividad",
            ]
            user_profile = input_data.user_profile or {}
            time_period = input_data.time_period or "No especificado"

            # Obtener cliente Gemini del agente
            gemini_client = self.agent.gemini_client

            # Utilizar las capacidades de visión del agente base
            with self.agent.tracer.start_as_current_span("wearable_data_analysis"):
                # Analizar la imagen utilizando el procesador de visión
                vision_result = await self.agent.vision_processor.analyze_image(
                    image_data
                )

                # Extraer análisis de datos de wearables usando el modelo multimodal
                prompt = f"""
                Eres un experto en biohacking y análisis de datos de dispositivos wearables. Analiza esta imagen
                de un dispositivo o aplicación de {device_type} y extrae información detallada sobre las métricas
                mostradas.
                
                Enfócate específicamente en las siguientes métricas:
                {', '.join(metrics_of_interest)}
                
                Período de tiempo: {time_period}
                
                Proporciona:
                1. Identificación del dispositivo/aplicación mostrado
                2. Valores exactos de las métricas visibles
                3. Interpretación de cada métrica
                4. Insights basados en los patrones observados
                5. Recomendaciones personalizadas para optimización
                
                Sé preciso, detallado y proporciona análisis basados en la ciencia del biohacking.
                """

                multimodal_result = (
                    await self.agent.multimodal_adapter.process_multimodal(
                        prompt=prompt,
                        image_data=image_data,
                        temperature=0.2,
                        max_output_tokens=1024,
                    )
                )

                # Extraer métricas estructuradas
                metrics_prompt = f"""
                Basándote en el siguiente análisis de datos de wearables, extrae métricas específicas
                en formato estructurado. Para cada métrica, incluye:
                1. Nombre de la métrica
                2. Valor
                3. Unidad (si aplica)
                4. Interpretación del valor
                5. Rango óptimo (si es conocido)
                6. Confianza en la extracción (0.0-1.0)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """

                metrics_response = await gemini_client.generate_structured_output(
                    metrics_prompt
                )

                # Procesar métricas
                metrics = []
                if isinstance(metrics_response, list):
                    for metric in metrics_response:
                        if isinstance(metric, dict) and "name" in metric:
                            metrics.append(
                                WearableMetric(
                                    name=metric.get("name", "No especificado"),
                                    value=metric.get("value", "No disponible"),
                                    unit=metric.get("unit"),
                                    interpretation=metric.get(
                                        "interpretation", "No disponible"
                                    ),
                                    optimal_range=metric.get("optimal_range"),
                                    confidence=metric.get("confidence", 0.7),
                                )
                            )
                elif (
                    isinstance(metrics_response, dict) and "metrics" in metrics_response
                ):
                    for metric in metrics_response["metrics"]:
                        if isinstance(metric, dict) and "name" in metric:
                            metrics.append(
                                WearableMetric(
                                    name=metric.get("name", "No especificado"),
                                    value=metric.get("value", "No disponible"),
                                    unit=metric.get("unit"),
                                    interpretation=metric.get(
                                        "interpretation", "No disponible"
                                    ),
                                    optimal_range=metric.get("optimal_range"),
                                    confidence=metric.get("confidence", 0.7),
                                )
                            )

                # Si no hay métricas, crear algunas genéricas
                if not metrics:
                    metrics.append(
                        WearableMetric(
                            name="Métrica no identificada",
                            value="No disponible",
                            unit=None,
                            interpretation="No se pudo extraer información específica de la imagen",
                            optimal_range=None,
                            confidence=0.5,
                        )
                    )

                # Extraer insights
                insights_prompt = f"""
                Basándote en el siguiente análisis de datos de wearables, genera 3-5 insights clave
                sobre los patrones observados y su significado para la salud y el rendimiento.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve los insights como una lista de strings.
                """

                insights_response = await gemini_client.generate_structured_output(
                    insights_prompt
                )

                # Procesar insights
                insights = []
                if isinstance(insights_response, list):
                    insights = [
                        insight
                        for insight in insights_response
                        if isinstance(insight, str)
                    ]
                elif (
                    isinstance(insights_response, dict)
                    and "insights" in insights_response
                ):
                    insights = [
                        insight
                        for insight in insights_response["insights"]
                        if isinstance(insight, str)
                    ]

                # Si no hay insights, crear algunos genéricos
                if not insights:
                    insights = [
                        "Los datos sugieren patrones que requieren análisis adicional",
                        "Se recomienda monitoreo continuo para establecer líneas base personales",
                        "Considere correlacionar estos datos con otros factores de estilo de vida",
                    ]

                # Extraer recomendaciones
                recommendations_prompt = f"""
                Basándote en el siguiente análisis de datos de wearables, genera 3-5 recomendaciones
                personalizadas para optimizar las métricas observadas. Cada recomendación debe incluir:
                1. Título de la recomendación
                2. Descripción detallada
                3. Impacto esperado
                4. Dificultad de implementación (fácil, moderada, difícil)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """

                recommendations_response = (
                    await gemini_client.generate_structured_output(
                        recommendations_prompt
                    )
                )

                # Procesar recomendaciones
                recommendations = []
                if isinstance(recommendations_response, list):
                    recommendations = recommendations_response
                elif (
                    isinstance(recommendations_response, dict)
                    and "recommendations" in recommendations_response
                ):
                    recommendations = recommendations_response["recommendations"]

                # Si no hay recomendaciones, crear algunas genéricas
                if not recommendations:
                    recommendations = [
                        {
                            "title": "Establecer línea base personal",
                            "description": "Monitorear estas métricas durante 2-4 semanas para establecer su línea base personal",
                            "expected_impact": "Mejor comprensión de sus patrones individuales",
                            "implementation_difficulty": "fácil",
                        },
                        {
                            "title": "Optimizar rutina de sueño",
                            "description": "Mantener horarios consistentes de sueño y despertar",
                            "expected_impact": "Mejora en recuperación y HRV",
                            "implementation_difficulty": "moderada",
                        },
                    ]

                # Extraer oportunidades de biohacking
                biohacking_prompt = f"""
                Basándote en el siguiente análisis de datos de wearables, identifica 2-4 oportunidades
                específicas de biohacking para optimizar las métricas observadas. Cada oportunidad debe incluir:
                1. Nombre de la intervención
                2. Descripción detallada
                3. Mecanismo de acción
                4. Evidencia científica
                5. Protocolo recomendado
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """

                biohacking_response = await gemini_client.generate_structured_output(
                    biohacking_prompt
                )

                # Procesar oportunidades de biohacking
                biohacking_opportunities = []
                if isinstance(biohacking_response, list):
                    biohacking_opportunities = biohacking_response
                elif (
                    isinstance(biohacking_response, dict)
                    and "opportunities" in biohacking_response
                ):
                    biohacking_opportunities = biohacking_response["opportunities"]

                # Si no hay oportunidades, crear algunas genéricas
                if not biohacking_opportunities:
                    biohacking_opportunities = [
                        {
                            "name": "Exposición a luz roja",
                            "description": "Sesiones de exposición a luz roja para mejorar la recuperación y función mitocondrial",
                            "mechanism": "Estimulación de la producción de ATP y reducción de inflamación",
                            "evidence": "Estudios muestran mejoras en recuperación muscular y calidad del sueño",
                            "protocol": "10-20 minutos diarios, preferiblemente por la mañana",
                        },
                        {
                            "name": "Suplementación con magnesio",
                            "description": "Suplementación con magnesio bisglicinato para mejorar la calidad del sueño y HRV",
                            "mechanism": "El magnesio es un cofactor en más de 300 reacciones enzimáticas y ayuda a regular el sistema nervioso",
                            "evidence": "Múltiples estudios muestran mejoras en calidad del sueño y reducción del estrés",
                            "protocol": "200-400mg antes de dormir",
                        },
                    ]

                # Determinar el dispositivo detectado
                device_detected = device_type
                if device_type == "No especificado":
                    # Intentar detectar el dispositivo a partir del análisis
                    analysis_text = multimodal_result.get("text", "").lower()
                    if "oura" in analysis_text:
                        device_detected = "Oura Ring"
                    elif "whoop" in analysis_text:
                        device_detected = "Whoop"
                    elif (
                        "apple watch" in analysis_text
                        or "apple health" in analysis_text
                    ):
                        device_detected = "Apple Watch"
                    elif "garmin" in analysis_text:
                        device_detected = "Garmin"
                    elif "fitbit" in analysis_text:
                        device_detected = "Fitbit"
                    else:
                        device_detected = "Dispositivo wearable no identificado"

                # Extraer resumen del análisis
                analysis_summary = (
                    multimodal_result.get("text", "").split("\n\n")[0]
                    if multimodal_result.get("text")
                    else "No se pudo generar un resumen del análisis."
                )

                # Crear la salida de la skill
                return AnalyzeWearableDataOutput(
                    device_detected=device_detected,
                    metrics=metrics,
                    analysis_summary=analysis_summary,
                    insights=insights,
                    recommendations=recommendations,
                    biohacking_opportunities=biohacking_opportunities,
                )

        except Exception as e:
            logger.error(f"Error al analizar datos de wearables: {e}", exc_info=True)

            # En caso de error, devolver un análisis básico
            return AnalyzeWearableDataOutput(
                device_detected="No identificado",
                metrics=[
                    WearableMetric(
                        name="Error en análisis",
                        value="No disponible",
                        unit=None,
                        interpretation="No se pudo realizar el análisis debido a un error en el procesamiento.",
                        optimal_range=None,
                        confidence=0.0,
                    )
                ],
                analysis_summary="No se pudo realizar el análisis debido a un error en el procesamiento.",
                insights=[
                    "Se recomienda intentar nuevamente con una imagen de mejor calidad."
                ],
                recommendations=[
                    {
                        "title": "Intentar con otra imagen",
                        "description": "Proporcionar una imagen más clara del dispositivo o aplicación",
                        "expected_impact": "Análisis preciso de los datos",
                        "implementation_difficulty": "fácil",
                    }
                ],
                biohacking_opportunities=[
                    {
                        "name": "Monitoreo manual",
                        "description": "Llevar un registro manual de métricas clave",
                        "mechanism": "Seguimiento consciente de patrones",
                        "evidence": "El auto-monitoreo es una estrategia efectiva para cambios de comportamiento",
                        "protocol": "Registro diario de métricas clave",
                    }
                ],
            )


class AnalyzeBiomarkerResultsSkill(GoogleADKSkill):
    name = "analyze_biomarker_results"
    description = "Analiza resultados de pruebas biológicas para proporcionar insights y estrategias de optimización"
    input_schema = AnalyzeBiomarkerResultsInput
    output_schema = AnalyzeBiomarkerResultsOutput

    async def handler(
        self, input_data: AnalyzeBiomarkerResultsInput
    ) -> AnalyzeBiomarkerResultsOutput:
        """Implementación de la skill de análisis de resultados de pruebas biológicas"""
        logger.info(f"Ejecutando skill de análisis de resultados de pruebas biológicas")

        try:
            # Obtener datos de la imagen
            image_data = input_data.image_data
            test_type = input_data.test_type or "No especificado"
            markers_of_interest = input_data.markers_of_interest or []
            user_profile = input_data.user_profile or {}
            health_goals = input_data.health_goals or []

            # Obtener cliente Gemini del agente
            gemini_client = self.agent.gemini_client

            # Utilizar las capacidades de visión del agente base
            with self.agent.tracer.start_as_current_span("biomarker_results_analysis"):
                # Analizar la imagen utilizando el procesador de visión
                vision_result = await self.agent.vision_processor.analyze_image(
                    image_data
                )

                # Extraer texto de la imagen para facilitar la extracción de valores
                text_result = await self.agent.vision_processor.extract_text(image_data)

                # Extraer análisis de resultados de pruebas usando el modelo multimodal
                prompt = f"""
                Eres un experto en biohacking y análisis de biomarcadores. Analiza esta imagen
                de resultados de pruebas de {test_type} y extrae información detallada sobre los
                biomarcadores mostrados.
                
                {f"Enfócate específicamente en los siguientes biomarcadores: {', '.join(markers_of_interest)}" if markers_of_interest else ""}
                
                {f"Considera los siguientes objetivos de salud del usuario: {', '.join(health_goals)}" if health_goals else ""}
                
                Proporciona:
                1. Identificación del tipo de prueba
                2. Valores exactos de los biomarcadores visibles
                3. Interpretación de cada biomarcador
                4. Insights sobre la salud basados en los resultados
                5. Estrategias de optimización recomendadas
                6. Suplementos recomendados basados en los resultados
                7. Recomendaciones de estilo de vida
                
                Sé preciso, detallado y proporciona análisis basados en la ciencia del biohacking.
                """

                multimodal_result = (
                    await self.agent.multimodal_adapter.process_multimodal(
                        prompt=prompt,
                        image_data=image_data,
                        temperature=0.2,
                        max_output_tokens=1024,
                    )
                )

                # Extraer biomarcadores estructurados
                biomarkers_prompt = f"""
                Basándote en el siguiente análisis de resultados de pruebas biológicas, extrae biomarcadores específicos
                en formato estructurado. Para cada biomarcador, incluye:
                1. Nombre del biomarcador
                2. Valor
                3. Unidad (si aplica)
                4. Rango de referencia (si está disponible)
                5. Estado (normal, bajo, alto, óptimo)
                6. Significado e importancia del biomarcador
                7. Confianza en la extracción (0.0-1.0)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Texto extraído de la imagen:
                {text_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """

                biomarkers_response = await gemini_client.generate_structured_output(
                    biomarkers_prompt
                )

                # Procesar biomarcadores
                biomarkers = []
                if isinstance(biomarkers_response, list):
                    for marker in biomarkers_response:
                        if isinstance(marker, dict) and "name" in marker:
                            biomarkers.append(
                                BiomarkerResult(
                                    name=marker.get("name", "No especificado"),
                                    value=marker.get("value", "No disponible"),
                                    unit=marker.get("unit"),
                                    reference_range=marker.get("reference_range"),
                                    status=marker.get("status", "No disponible"),
                                    significance=marker.get(
                                        "significance", "No disponible"
                                    ),
                                    confidence=marker.get("confidence", 0.7),
                                )
                            )
                elif (
                    isinstance(biomarkers_response, dict)
                    and "biomarkers" in biomarkers_response
                ):
                    for marker in biomarkers_response["biomarkers"]:
                        if isinstance(marker, dict) and "name" in marker:
                            biomarkers.append(
                                BiomarkerResult(
                                    name=marker.get("name", "No especificado"),
                                    value=marker.get("value", "No disponible"),
                                    unit=marker.get("unit"),
                                    reference_range=marker.get("reference_range"),
                                    status=marker.get("status", "No disponible"),
                                    significance=marker.get(
                                        "significance", "No disponible"
                                    ),
                                    confidence=marker.get("confidence", 0.7),
                                )
                            )

                # Si no hay biomarcadores, crear algunos genéricos
                if not biomarkers:
                    biomarkers.append(
                        BiomarkerResult(
                            name="Biomarcador no identificado",
                            value="No disponible",
                            unit=None,
                            reference_range=None,
                            status="No disponible",
                            significance="No se pudo extraer información específica de la imagen",
                            confidence=0.5,
                        )
                    )

                # Extraer insights de salud
                health_insights_prompt = f"""
                Basándote en el siguiente análisis de resultados de pruebas biológicas, genera 3-5 insights clave
                sobre la salud del usuario basados en los resultados.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve los insights como una lista de strings.
                """

                health_insights_response = (
                    await gemini_client.generate_structured_output(
                        health_insights_prompt
                    )
                )

                # Procesar insights de salud
                health_insights = []
                if isinstance(health_insights_response, list):
                    health_insights = [
                        insight
                        for insight in health_insights_response
                        if isinstance(insight, str)
                    ]
                elif (
                    isinstance(health_insights_response, dict)
                    and "insights" in health_insights_response
                ):
                    health_insights = [
                        insight
                        for insight in health_insights_response["insights"]
                        if isinstance(insight, str)
                    ]

                # Si no hay insights, crear algunos genéricos
                if not health_insights:
                    health_insights = [
                        "Los resultados sugieren patrones que requieren análisis adicional",
                        "Se recomienda consultar con un profesional de la salud para una interpretación completa",
                        "Considere realizar pruebas de seguimiento para confirmar los hallazgos",
                    ]

                # Extraer estrategias de optimización
                optimization_strategies_prompt = f"""
                Basándote en el siguiente análisis de resultados de pruebas biológicas, genera 3-5 estrategias
                de optimización para mejorar los biomarcadores. Cada estrategia debe incluir:
                1. Nombre de la estrategia
                2. Descripción detallada
                3. Biomarcadores objetivo
                4. Mecanismo de acción
                5. Tiempo esperado para ver resultados
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """

                optimization_strategies_response = (
                    await gemini_client.generate_structured_output(
                        optimization_strategies_prompt
                    )
                )

                # Procesar estrategias de optimización
                optimization_strategies = []
                if isinstance(optimization_strategies_response, list):
                    optimization_strategies = optimization_strategies_response
                elif (
                    isinstance(optimization_strategies_response, dict)
                    and "strategies" in optimization_strategies_response
                ):
                    optimization_strategies = optimization_strategies_response[
                        "strategies"
                    ]

                # Si no hay estrategias, crear algunas genéricas
                if not optimization_strategies:
                    optimization_strategies = [
                        {
                            "name": "Optimización nutricional",
                            "description": "Ajustar la dieta para abordar deficiencias y desequilibrios",
                            "target_biomarkers": ["Múltiples"],
                            "mechanism": "Proporcionar nutrientes esenciales y reducir inflamación",
                            "expected_timeframe": "4-8 semanas",
                        },
                        {
                            "name": "Protocolo de gestión del estrés",
                            "description": "Implementar técnicas de reducción del estrés como meditación y respiración",
                            "target_biomarkers": ["Cortisol", "Inflamación"],
                            "mechanism": "Reducción de la activación del eje HPA y respuesta inflamatoria",
                            "expected_timeframe": "2-4 semanas",
                        },
                    ]

                # Extraer recomendaciones de suplementos
                supplement_recommendations_prompt = f"""
                Basándote en el siguiente análisis de resultados de pruebas biológicas, recomienda 3-5 suplementos
                específicos para optimizar los biomarcadores. Para cada suplemento, incluye:
                1. Nombre del suplemento
                2. Dosis recomendada
                3. Biomarcadores objetivo
                4. Mecanismo de acción
                5. Consideraciones de seguridad
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """

                supplement_recommendations_response = (
                    await gemini_client.generate_structured_output(
                        supplement_recommendations_prompt
                    )
                )

                # Procesar recomendaciones de suplementos
                supplement_recommendations = []
                if isinstance(supplement_recommendations_response, list):
                    supplement_recommendations = supplement_recommendations_response
                elif (
                    isinstance(supplement_recommendations_response, dict)
                    and "supplements" in supplement_recommendations_response
                ):
                    supplement_recommendations = supplement_recommendations_response[
                        "supplements"
                    ]

                # Extraer recomendaciones de estilo de vida
                lifestyle_recommendations_prompt = f"""
                Basándote en el siguiente análisis de resultados de pruebas biológicas, genera 3-5 recomendaciones
                específicas de estilo de vida para optimizar los biomarcadores.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve las recomendaciones como una lista de strings.
                """

                lifestyle_recommendations_response = (
                    await gemini_client.generate_structured_output(
                        lifestyle_recommendations_prompt
                    )
                )

                # Procesar recomendaciones de estilo de vida
                lifestyle_recommendations = []
                if isinstance(lifestyle_recommendations_response, list):
                    lifestyle_recommendations = [
                        rec
                        for rec in lifestyle_recommendations_response
                        if isinstance(rec, str)
                    ]
                elif (
                    isinstance(lifestyle_recommendations_response, dict)
                    and "recommendations" in lifestyle_recommendations_response
                ):
                    lifestyle_recommendations = [
                        rec
                        for rec in lifestyle_recommendations_response["recommendations"]
                        if isinstance(rec, str)
                    ]

                # Si no hay recomendaciones, crear algunas genéricas
                if not lifestyle_recommendations:
                    lifestyle_recommendations = [
                        "Mantener una dieta rica en alimentos enteros y antiinflamatorios",
                        "Priorizar el sueño de calidad (7-9 horas por noche)",
                        "Implementar técnicas de gestión del estrés como meditación o respiración profunda",
                        "Realizar ejercicio regular adaptado a sus objetivos y capacidades",
                        "Minimizar la exposición a toxinas ambientales y disruptores endocrinos",
                    ]

                # Determinar el tipo de prueba detectado
                test_type_detected = test_type
                if test_type == "No especificado":
                    # Intentar detectar el tipo de prueba a partir del análisis
                    analysis_text = multimodal_result.get("text", "").lower()
                    if (
                        "sangre" in analysis_text
                        or "hemograma" in analysis_text
                        or "bioquímica" in analysis_text
                    ):
                        test_type_detected = "Análisis de sangre"
                    elif (
                        "genética" in analysis_text
                        or "adn" in analysis_text
                        or "genoma" in analysis_text
                    ):
                        test_type_detected = "Prueba genética"
                    elif (
                        "microbioma" in analysis_text
                        or "intestinal" in analysis_text
                        or "bacterias" in analysis_text
                    ):
                        test_type_detected = "Análisis de microbioma"
                    elif "hormonal" in analysis_text or "hormonas" in analysis_text:
                        test_type_detected = "Panel hormonal"
                    else:
                        test_type_detected = "Prueba biológica no identificada"

                # Extraer resumen del análisis
                analysis_summary = (
                    multimodal_result.get("text", "").split("\n\n")[0]
                    if multimodal_result.get("text")
                    else "No se pudo generar un resumen del análisis."
                )

                # Crear la salida de la skill
                return AnalyzeBiomarkerResultsOutput(
                    test_type_detected=test_type_detected,
                    biomarkers=biomarkers,
                    analysis_summary=analysis_summary,
                    health_insights=health_insights,
                    optimization_strategies=optimization_strategies,
                    supplement_recommendations=supplement_recommendations,
                    lifestyle_recommendations=lifestyle_recommendations,
                )

        except Exception as e:
            logger.error(
                f"Error al analizar resultados de pruebas biológicas: {e}",
                exc_info=True,
            )

            # En caso de error, devolver un análisis básico
            return AnalyzeBiomarkerResultsOutput(
                test_type_detected="No identificado",
                biomarkers=[
                    BiomarkerResult(
                        name="Error en análisis",
                        value="No disponible",
                        unit=None,
                        reference_range=None,
                        status="No disponible",
                        significance="No se pudo realizar el análisis debido a un error en el procesamiento.",
                        confidence=0.0,
                    )
                ],
                analysis_summary="No se pudo realizar el análisis debido a un error en el procesamiento.",
                health_insights=[
                    "Se recomienda consultar con un profesional de la salud para una interpretación adecuada de los resultados."
                ],
                optimization_strategies=[
                    {
                        "name": "Consulta profesional",
                        "description": "Buscar la interpretación de un profesional de la salud calificado",
                        "target_biomarkers": ["Todos"],
                        "mechanism": "Expertise profesional",
                        "expected_timeframe": "Inmediato",
                    }
                ],
                supplement_recommendations=[],
                lifestyle_recommendations=[
                    "Mantener hábitos saludables generales mientras se obtiene una interpretación profesional de los resultados."
                ],
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
        state_manager=None,
        **kwargs,
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
                    output="Aquí tienes un protocolo de biohacking para principiantes basado en evidencia científica...",
                ),
                Example(
                    input="¿Qué estrategias puedo implementar para mejorar mi longevidad?",
                    output="Para mejorar tu longevidad, te recomiendo las siguientes estrategias basadas en evidencia...",
                ),
                Example(
                    input="¿Cómo puedo mejorar mi rendimiento cognitivo de forma natural?",
                    output="Para optimizar tu rendimiento cognitivo, te recomiendo este protocolo personalizado...",
                ),
                Example(
                    input="¿Qué puedo hacer para optimizar mis niveles hormonales naturalmente?",
                    output="Para optimizar tu equilibrio hormonal de forma natural, considera estas intervenciones...",
                ),
            ],
        )

        # Crear toolkit con las skills del agente
        toolkit = Toolkit(
            skills=[
                BiohackingProtocolSkill(),
                LongevityStrategySkill(),
                CognitiveEnhancementSkill(),
                HormonalOptimizationSkill(),
                AnalyzeWearableDataSkill(),
                AnalyzeBiomarkerResultsSkill(),
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
            **kwargs,
        )

        # Inicializar el servicio de clasificación de programas
        self.gemini_client = gemini_client or GeminiClient()
        self.program_classification_service = ProgramClassificationService(
            self.gemini_client
        )

        # Inicializar procesadores de visión y multimodales para las nuevas capacidades
        try:
            # Inicializar procesador de visión
            from core.vision_processor import VisionProcessor

            self.vision_processor = VisionProcessor(model=self.model)
            logger.info("Procesador de visión inicializado correctamente")

            # Inicializar adaptador multimodal
            from infrastructure.adapters.multimodal_adapter import MultimodalAdapter

            self.multimodal_adapter = MultimodalAdapter()
            logger.info("Adaptador multimodal inicializado correctamente")

            # Inicializar tracer para telemetría
            from opentelemetry import trace

            self.tracer = trace.get_tracer(__name__)
            logger.info("Tracer para telemetría inicializado correctamente")
        except ImportError as e:
            logger.warning(
                f"No se pudieron inicializar algunos componentes para capacidades avanzadas: {e}"
            )
            # Crear implementaciones simuladas para mantener la compatibilidad
            self.vision_processor = type(
                "DummyVisionProcessor",
                (),
                {
                    "analyze_image": lambda self, image_data: asyncio.Future().set_result(
                        {"text": "Análisis de imagen simulado"}
                    ),
                    "extract_text": lambda self, image_data: asyncio.Future().set_result(
                        {"text": "Texto extraído simulado"}
                    ),
                },
            )()
            self.multimodal_adapter = type(
                "DummyMultimodalAdapter",
                (),
                {
                    "process_multimodal": lambda self, prompt, image_data, temperature=0.2, max_output_tokens=1024: asyncio.Future().set_result(
                        {"text": "Análisis multimodal simulado"}
                    )
                },
            )()
            self.tracer = type(
                "DummyTracer",
                (),
                {
                    "start_as_current_span": lambda name: type(
                        "DummySpan",
                        (),
                        {
                            "__enter__": lambda self: None,
                            "__exit__": lambda self, *args: None,
                        },
                    )()
                },
            )

        logger.info(f"Agente BiohackingInnovator inicializado con ID: {agent_id}")

    async def _get_context(
        self, user_id: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
                logger.info(
                    f"No se encontró contexto en el adaptador del StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto."
                )
                # Si no hay contexto, crear uno nuevo
                context = {
                    "conversation_history": [],
                    "user_profile": {},
                    "protocols": [],
                    "resources_used": [],
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            else:
                # Si hay contexto, usar el state_data
                context = context.get("state_data", {})
                logger.info(
                    f"Contexto cargado desde el adaptador del StateManager para user_id={user_id}, session_id={session_id}"
                )

            return context
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "protocols": [],
                "resources_used": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

    async def _update_context(
        self, context: Dict[str, Any], user_id: str, session_id: str
    ) -> None:
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
            logger.info(
                f"Contexto actualizado en el adaptador del StateManager para user_id={user_id}, session_id={session_id}"
            )
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
                "biohacking": "biohacking",
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
            logger.error(
                f"Error al clasificar consulta con Intent Analyzer: {e}", exc_info=True
            )
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
            "biohacking",
            "protocolo",
            "optimización",
            "rendimiento",
            "mejora",
            "monitoreo",
            "dispositivos",
            "autoexperimentación",
        ]

        # Palabras clave para longevidad
        longevity_keywords = [
            "longevidad",
            "envejecimiento",
            "antienvejecimiento",
            "vida saludable",
            "esperanza de vida",
            "telómeros",
            "sirtuinas",
            "senolíticos",
        ]

        # Palabras clave para mejora cognitiva
        cognitive_keywords = [
            "cognitivo",
            "cerebro",
            "memoria",
            "concentración",
            "claridad mental",
            "nootropicos",
            "rendimiento mental",
            "niebla mental",
            "focus",
        ]

        # Palabras clave para optimización hormonal
        hormonal_keywords = [
            "hormonal",
            "testosterona",
            "estrógeno",
            "cortisol",
            "tiroides",
            "insulina",
            "hormona de crecimiento",
            "equilibrio hormonal",
        ]

        # Palabras clave para análisis de datos de wearables
        wearable_keywords = [
            "wearable",
            "dispositivo",
            "anillo",
            "reloj",
            "oura",
            "whoop",
            "apple watch",
            "garmin",
            "fitbit",
            "hrv",
            "sueño",
            "recuperación",
            "actividad",
            "pasos",
            "frecuencia cardíaca",
            "monitoreo",
            "métricas",
            "datos",
        ]

        # Palabras clave para análisis de biomarcadores
        biomarker_keywords = [
            "biomarcador",
            "análisis",
            "sangre",
            "prueba",
            "laboratorio",
            "resultados",
            "genética",
            "microbioma",
            "hormonal",
            "inflamación",
            "metabolismo",
            "colesterol",
            "glucosa",
            "insulina",
            "vitamina",
            "mineral",
            "enzima",
        ]

        # Verificar coincidencias con palabras clave
        for keyword in wearable_keywords:
            if keyword in query_lower:
                return "analyze_wearable_data"

        for keyword in biomarker_keywords:
            if keyword in query_lower:
                return "analyze_biomarker_results"

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

    async def _consult_other_agent(
        self,
        agent_id: str,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
                "additional_context": context or {},
            }

            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id, user_input=query, context=task_context
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
                "agent_name": agent_id,
            }

    async def _run_async_impl(
        self, input_text: str, user_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
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

        # Determinar el tipo de programa del usuario para personalizar las recomendaciones
        program_context = {
            "user_profile": user_profile or {},
            "goals": user_profile.get("goals", []) if user_profile else [],
        }

        try:
            # Clasificar el tipo de programa del usuario
            program_type = (
                await self.program_classification_service.classify_program_type(
                    program_context
                )
            )
            logger.info(f"Tipo de programa determinado para biohacking: {program_type}")

            # Obtener definición del programa para personalizar las recomendaciones
            program_def = get_program_definition(program_type)

            # Guardar el tipo de programa en el contexto
            context["program_type"] = program_type
            if program_def:
                context["program_objective"] = program_def.get("objective", "")
        except Exception as e:
            logger.warning(
                f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales."
            )
            program_type = "GENERAL"
            program_def = None

        # Clasificar el tipo de consulta utilizando el adaptador del Intent Analyzer
        query_type = await self._classify_query(input_text)
        capabilities_used = []

        # Procesar la consulta según su tipo utilizando las skills ADK
        if query_type == "biohacking":
            # Usar la skill de protocolo de biohacking
            biohacking_skill = next(
                (skill for skill in self.skills if skill.name == "biohacking_protocol"),
                None,
            )
            if biohacking_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                age = user_profile.get("age") if user_profile else None
                gender = user_profile.get("gender") if user_profile else None
                health_conditions = (
                    user_profile.get("health_conditions", []) if user_profile else []
                )
                goals = user_profile.get("goals", []) if user_profile else []

                input_data = BiohackingProtocolInput(
                    query=input_text,
                    age=age,
                    gender=gender,
                    health_conditions=health_conditions,
                    goals=goals,
                )
                result = await biohacking_skill.handler(input_data)
                response = result.response
                capabilities_used.append("biohacking")

                # Actualizar contexto con el protocolo
                context["protocols"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "biohacking",
                        "query": input_text,
                        "protocol": result.protocol,
                        "resources": result.resources,
                    }
                )

        elif query_type == "longevity":
            # Usar la skill de estrategias de longevidad
            longevity_skill = next(
                (skill for skill in self.skills if skill.name == "longevity_strategy"),
                None,
            )
            if longevity_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                age = user_profile.get("age") if user_profile else None
                health_profile = (
                    {
                        "conditions": user_profile.get("health_conditions", []),
                        "metrics": user_profile.get("metrics", {}),
                        "lifestyle": user_profile.get("lifestyle", {}),
                    }
                    if user_profile
                    else {}
                )

                input_data = LongevityStrategyInput(
                    query=input_text, age=age, health_profile=health_profile
                )
                result = await longevity_skill.handler(input_data)
                response = result.response
                capabilities_used.append("longevity")

                # Actualizar contexto con las estrategias de longevidad
                context["protocols"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "longevity",
                        "query": input_text,
                        "strategies": result.strategies,
                        "scientific_basis": result.scientific_basis,
                    }
                )

        elif query_type == "cognitive_enhancement":
            # Usar la skill de mejora cognitiva
            cognitive_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "cognitive_enhancement"
                ),
                None,
            )
            if cognitive_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                cognitive_goals = (
                    user_profile.get("cognitive_goals", []) if user_profile else []
                )
                current_supplements = (
                    user_profile.get("supplements", []) if user_profile else []
                )

                input_data = CognitiveEnhancementInput(
                    query=input_text,
                    cognitive_goals=cognitive_goals,
                    current_supplements=current_supplements,
                )
                result = await cognitive_skill.handler(input_data)
                response = result.response
                capabilities_used.append("cognitive_enhancement")

                # Actualizar contexto con el protocolo de mejora cognitiva
                context["protocols"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "cognitive_enhancement",
                        "query": input_text,
                        "protocol": result.protocol,
                        "supplements": result.supplements,
                    }
                )

        elif query_type == "hormonal_optimization":
            # Usar la skill de optimización hormonal
            hormonal_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "hormonal_optimization"
                ),
                None,
            )
            if hormonal_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                age = user_profile.get("age") if user_profile else None
                gender = user_profile.get("gender") if user_profile else None
                hormone_concerns = (
                    user_profile.get("hormone_concerns", []) if user_profile else []
                )

                input_data = HormonalOptimizationInput(
                    query=input_text,
                    age=age,
                    gender=gender,
                    hormone_concerns=hormone_concerns,
                )
                result = await hormonal_skill.handler(input_data)
                response = result.response
                capabilities_used.append("hormonal_optimization")

                # Actualizar contexto con el protocolo de optimización hormonal
                context["protocols"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "hormonal_optimization",
                        "query": input_text,
                        "protocol": result.protocol,
                        "lifestyle_changes": result.lifestyle_changes,
                        "supplements": result.supplements,
                    }
                )

        elif query_type == "analyze_wearable_data":
            # Usar la skill de análisis de datos de wearables
            wearable_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "analyze_wearable_data"
                ),
                None,
            )
            if wearable_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                # Nota: En un caso real, aquí se procesaría la imagen proporcionada por el usuario
                # Para esta implementación, asumimos que la imagen se proporciona como un string base64 o URL

                # Crear datos de entrada simulados para la demostración
                input_data = AnalyzeWearableDataInput(
                    image_data="<imagen_simulada>",  # En un caso real, esto sería la imagen proporcionada
                    device_type=None,  # Se detectará automáticamente
                    metrics_of_interest=["HRV", "sueño", "recuperación", "actividad"],
                    user_profile=user_profile,
                    time_period="última semana",
                )

                result = await wearable_skill.handler(input_data)
                response = f"Análisis de datos del dispositivo {result.device_detected}:\n\n{result.analysis_summary}\n\n"

                # Añadir insights clave
                response += "Insights clave:\n"
                for insight in result.insights[
                    :3
                ]:  # Limitar a 3 insights para mantener la respuesta concisa
                    response += f"- {insight}\n"

                # Añadir recomendaciones principales
                response += "\nRecomendaciones principales:\n"
                for rec in result.recommendations[:2]:  # Limitar a 2 recomendaciones
                    response += (
                        f"- {rec.get('title', '')}: {rec.get('description', '')}\n"
                    )

                capabilities_used.append("analyze_wearable_data")

                # Actualizar contexto con el análisis
                context["protocols"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "wearable_analysis",
                        "query": input_text,
                        "device_detected": result.device_detected,
                        "metrics": [
                            {
                                "name": m.name,
                                "value": m.value,
                                "interpretation": m.interpretation,
                            }
                            for m in result.metrics
                        ],
                        "insights": result.insights,
                        "recommendations": result.recommendations,
                    }
                )

        elif query_type == "analyze_biomarker_results":
            # Usar la skill de análisis de resultados de pruebas biológicas
            biomarker_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "analyze_biomarker_results"
                ),
                None,
            )
            if biomarker_skill:
                # Extraer información relevante del perfil del usuario si está disponible
                # Nota: En un caso real, aquí se procesaría la imagen proporcionada por el usuario

                # Crear datos de entrada simulados para la demostración
                input_data = AnalyzeBiomarkerResultsInput(
                    image_data="<imagen_simulada>",  # En un caso real, esto sería la imagen proporcionada
                    test_type=None,  # Se detectará automáticamente
                    markers_of_interest=[],
                    user_profile=user_profile,
                    health_goals=user_profile.get("goals", []) if user_profile else [],
                )

                result = await biomarker_skill.handler(input_data)
                response = f"Análisis de {result.test_type_detected}:\n\n{result.analysis_summary}\n\n"

                # Añadir insights de salud
                response += "Insights de salud:\n"
                for insight in result.health_insights[
                    :3
                ]:  # Limitar a 3 insights para mantener la respuesta concisa
                    response += f"- {insight}\n"

                # Añadir estrategias de optimización principales
                response += "\nEstrategias de optimización recomendadas:\n"
                for strategy in result.optimization_strategies[
                    :2
                ]:  # Limitar a 2 estrategias
                    response += f"- {strategy.get('name', '')}: {strategy.get('description', '')}\n"

                # Añadir recomendaciones de estilo de vida
                response += "\nRecomendaciones de estilo de vida:\n"
                for rec in result.lifestyle_recommendations[
                    :3
                ]:  # Limitar a 3 recomendaciones
                    response += f"- {rec}\n"

                capabilities_used.append("analyze_biomarker_results")

                # Actualizar contexto con el análisis
                context["protocols"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "type": "biomarker_analysis",
                        "query": input_text,
                        "test_type": result.test_type_detected,
                        "biomarkers": [
                            {"name": b.name, "value": b.value, "status": b.status}
                            for b in result.biomarkers
                        ],
                        "health_insights": result.health_insights,
                        "optimization_strategies": result.optimization_strategies,
                    }
                )

        # Actualizar el historial de conversación
        context["conversation_history"].append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "role": "user",
                "content": input_text,
            }
        )
        context["conversation_history"].append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "role": "assistant",
                "content": response,
            }
        )

        # Actualizar el contexto en el StateManager
        if user_id:
            await self._update_context(context, user_id, session_id)

        # Calcular tiempo de ejecución
        execution_time = time.time() - start_time
        logger.info(
            f"BiohackingInnovator completó la ejecución en {execution_time:.2f} segundos"
        )

        # Preparar respuesta según el protocolo ADK
        return {
            "response": response,
            "capabilities_used": capabilities_used,
            "metadata": {
                "query_type": query_type,
                "program_type": program_type,
                "execution_time": execution_time,
                "session_id": session_id,
            },
        }
