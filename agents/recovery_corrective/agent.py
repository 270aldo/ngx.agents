import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union
import json
import os
from google.cloud import aiplatform
import datetime
import asyncio
import base64
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
from core.logging_config import get_logger
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition

# Configurar logger
logger = get_logger(__name__)

# Definir esquemas de entrada y salida para las skills
class InjuryPreventionInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre prevención de lesiones")
    activity_type: Optional[str] = Field(None, description="Tipo de actividad física")
    injury_history: Optional[List[str]] = Field(None, description="Historial de lesiones previas")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class InjuryPreventionOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre prevención de lesiones")
    prevention_plan: Dict[str, Any] = Field(..., description="Plan de prevención estructurado")
    exercises: Optional[List[Dict[str, Any]]] = Field(None, description="Ejercicios recomendados")

class RehabilitationInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre rehabilitación")
    injury_type: Optional[str] = Field(None, description="Tipo de lesión")
    injury_phase: Optional[str] = Field(None, description="Fase de la lesión (aguda, subaguda, crónica)")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class RehabilitationOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre rehabilitación")
    rehab_protocol: Dict[str, Any] = Field(..., description="Protocolo de rehabilitación estructurado")
    exercises: Optional[List[Dict[str, Any]]] = Field(None, description="Ejercicios recomendados")

class MobilityAssessmentInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre movilidad")
    target_areas: Optional[List[str]] = Field(None, description="Áreas objetivo para mejorar movilidad")
    movement_goals: Optional[List[str]] = Field(None, description="Objetivos de movimiento")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class MobilityAssessmentOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre movilidad")
    mobility_assessment: Dict[str, Any] = Field(..., description="Evaluación de movilidad estructurada")
    exercises: Optional[List[Dict[str, Any]]] = Field(None, description="Ejercicios recomendados")

class SleepOptimizationInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre optimización del sueño")
    sleep_issues: Optional[List[str]] = Field(None, description="Problemas de sueño reportados")
    sleep_data: Optional[Dict[str, Any]] = Field(None, description="Datos de sueño del usuario")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class SleepOptimizationOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre optimización del sueño")
    sleep_plan: Dict[str, Any] = Field(..., description="Plan de optimización del sueño estructurado")
    recommendations: Optional[List[str]] = Field(None, description="Recomendaciones específicas")

class HRVProtocolInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre protocolos HRV")
    hrv_data: Optional[Dict[str, Any]] = Field(None, description="Datos de HRV del usuario")
    training_context: Optional[Dict[str, Any]] = Field(None, description="Contexto de entrenamiento")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class HRVProtocolOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre protocolos HRV")
    hrv_protocol: Dict[str, Any] = Field(..., description="Protocolo HRV estructurado")
    recommendations: Optional[List[str]] = Field(None, description="Recomendaciones específicas")

class ChronicPainInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre dolor crónico")
    pain_location: Optional[str] = Field(None, description="Ubicación del dolor")
    pain_intensity: Optional[int] = Field(None, description="Intensidad del dolor (1-10)")
    pain_duration: Optional[str] = Field(None, description="Duración del dolor")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class ChronicPainOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre manejo del dolor crónico")
    pain_assessment: Dict[str, Any] = Field(..., description="Evaluación del dolor estructurada")
    management_plan: Dict[str, Any] = Field(..., description="Plan de manejo del dolor estructurado")
    recommendations: Optional[List[str]] = Field(None, description="Recomendaciones específicas")

class GeneralRecoveryInput(BaseModel):
    query: str = Field(..., description="Consulta general del usuario sobre recuperación")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class GeneralRecoveryOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada a la consulta general")
    recovery_protocol: Optional[Dict[str, Any]] = Field(None, description="Protocolo de recuperación si es aplicable")

class PostureAnalysisInput(BaseModel):
    image_data: str = Field(..., description="Imagen codificada en base64 para análisis de postura")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    analysis_type: Optional[str] = Field("general", description="Tipo de análisis de postura (general, específico)")
    focus_areas: Optional[List[str]] = Field(None, description="Áreas específicas para analizar")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class PostureAnalysisOutput(BaseModel):
    analysis_id: str = Field(..., description="ID único del análisis")
    posture_summary: str = Field(..., description="Resumen del análisis de postura")
    posture_assessment: Dict[str, Any] = Field(..., description="Evaluación detallada de la postura")
    imbalances: List[Dict[str, Any]] = Field(..., description="Desequilibrios posturales identificados")
    recommendations: List[str] = Field(..., description="Recomendaciones para mejorar la postura")
    corrective_exercises: Optional[List[Dict[str, Any]]] = Field(None, description="Ejercicios correctivos recomendados")

class MovementAnalysisInput(BaseModel):
    video_data: Optional[str] = Field(None, description="Video codificado en base64 para análisis de movimiento")
    image_sequence: Optional[List[str]] = Field(None, description="Secuencia de imágenes codificadas en base64")
    movement_type: str = Field(..., description="Tipo de movimiento a analizar (sentadilla, peso muerto, etc.)")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")

class MovementAnalysisOutput(BaseModel):
    analysis_id: str = Field(..., description="ID único del análisis")
    movement_summary: str = Field(..., description="Resumen del análisis de movimiento")
    movement_assessment: Dict[str, Any] = Field(..., description="Evaluación detallada del movimiento")
    technique_issues: List[Dict[str, Any]] = Field(..., description="Problemas de técnica identificados")
    recommendations: List[str] = Field(..., description="Recomendaciones para mejorar la técnica")
    corrective_exercises: Optional[List[Dict[str, Any]]] = Field(None, description="Ejercicios correctivos recomendados")

# Definir las skills como clases que heredan de GoogleADKSkill
class InjuryPreventionSkill(GoogleADKSkill):
    name = "injury_prevention"
    description = "Genera protocolos personalizados para prevenir lesiones comunes en diferentes actividades físicas"
    input_schema = InjuryPreventionInput
    output_schema = InjuryPreventionOutput
    
    async def handler(self, input_data: InjuryPreventionInput) -> InjuryPreventionOutput:
        """Implementación de la skill de prevención de lesiones"""
        query = input_data.query
        activity_type = input_data.activity_type
        injury_history = input_data.injury_history or []
        user_profile = input_data.user_profile or {}
        
        # Determinar el tipo de programa del usuario para personalizar las recomendaciones
        context = {
            "user_profile": user_profile,
            "goals": user_profile.get("goals", []) if user_profile else []
        }
        
        try:
            # Clasificar el tipo de programa del usuario
            program_type = await self.agent.program_classification_service.classify_program_type(context)
            logger.info(f"Tipo de programa determinado para prevención de lesiones: {program_type}")
            
            # Obtener definición del programa para personalizar las recomendaciones
            program_def = get_program_definition(program_type)
            
            # Preparar contexto específico del programa
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            
            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                
                # Añadir protocolos de recuperación específicos del programa si están disponibles
                if program_def.get("key_protocols") and "recovery" in program_def.get("key_protocols", {}):
                    program_context += "- Protocolos de recuperación recomendados:\n"
                    for protocol in program_def.get("key_protocols", {}).get("recovery", []):
                        program_context += f"  * {protocol}\n"
        except Exception as e:
            logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
            program_type = "GENERAL"
            program_context = ""
        
        # Construir el prompt para el modelo
        activity_info = f"Actividad: {activity_type}" if activity_type else "Actividad no especificada"
        history_info = f"Historial de lesiones: {', '.join(injury_history)}" if injury_history else "Sin historial de lesiones conocido"
        
        prompt = f"""
        Eres un especialista en prevención de lesiones y recuperación física.
        
        El usuario solicita información sobre prevención de lesiones:
        "{query}"
        
        Información adicional:
        - {activity_info}
        - {history_info}
        - Tipo de programa: {program_type}
        {program_context}
        
        Proporciona una respuesta detallada sobre cómo prevenir lesiones específicas,
        incluyendo ejercicios de calentamiento, fortalecimiento, técnica adecuada y señales de alerta.
        Adapta tus recomendaciones específicamente para el programa {program_type} del usuario.
        
        Estructura tu respuesta en secciones:
        1. Análisis de riesgos específicos para el programa {program_type}
        2. Estrategias de prevención alineadas con los objetivos del programa
        3. Ejercicios recomendados considerando las necesidades específicas del programa
        4. Señales de alerta
        5. Cuándo buscar ayuda profesional
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar plan de prevención estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan de prevención de lesiones estructurado en formato JSON con los siguientes campos:
        - target_area: área objetivo (ej. "rodilla", "espalda baja", "hombro")
        - risk_factors: factores de riesgo identificados
        - warm_up: rutina de calentamiento recomendada
        - strengthening: ejercicios de fortalecimiento
        - technique_tips: consejos de técnica
        - recovery_strategies: estrategias de recuperación
        - warning_signs: señales de alerta
        
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
                    "target_area": "área no especificada",
                    "risk_factors": ["Factores de riesgo no especificados"],
                    "warm_up": "Rutina de calentamiento general de 5-10 minutos",
                    "strengthening": "Ejercicios de fortalecimiento general",
                    "technique_tips": ["Mantener buena postura", "Evitar movimientos bruscos"],
                    "recovery_strategies": ["Descanso adecuado", "Hidratación"],
                    "warning_signs": ["Dolor persistente", "Inflamación"]
                }
        
        # Generar ejercicios recomendados
        exercises_prompt = f"""
        Basándote en la consulta del usuario sobre prevención de lesiones:
        "{query}"
        
        Genera una lista de 3-5 ejercicios específicos en formato JSON array, donde cada ejercicio es un objeto con:
        - name: nombre del ejercicio
        - description: descripción breve
        - sets: número de series
        - reps: número de repeticiones
        - frequency: frecuencia recomendada
        - notes: notas adicionales (opcional)
        
        Devuelve SOLO el JSON array, sin explicaciones adicionales.
        """
        
        exercises_json = await gemini_client.generate_structured_output(exercises_prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(exercises_json, list):
            try:
                exercises_json = json.loads(exercises_json)
                if not isinstance(exercises_json, list):
                    exercises_json = []
            except:
                # Si no se puede convertir, crear una lista básica
                exercises_json = [
                    {
                        "name": "Ejemplo de ejercicio 1",
                        "description": "Descripción del ejercicio",
                        "sets": 3,
                        "reps": "10-12",
                        "frequency": "3 veces por semana",
                        "notes": "Mantener buena forma"
                    }
                ]
        
        return InjuryPreventionOutput(
            response=response_text,
            prevention_plan=plan_json,
            exercises=exercises_json
        )

class RehabilitationSkill(GoogleADKSkill):
    name = "rehabilitation"
    description = "Desarrolla protocolos de rehabilitación personalizados para diferentes tipos de lesiones"
    input_schema = RehabilitationInput
    output_schema = RehabilitationOutput
    
    async def handler(self, input_data: RehabilitationInput) -> RehabilitationOutput:
        """Implementación de la skill de rehabilitación"""
        query = input_data.query
        injury_type = input_data.injury_type
        injury_phase = input_data.injury_phase
        user_profile = input_data.user_profile or {}
        
        # Determinar el tipo de programa del usuario para personalizar las recomendaciones
        context = {
            "user_profile": user_profile,
            "goals": user_profile.get("goals", []) if user_profile else []
        }
        
        try:
            # Clasificar el tipo de programa del usuario
            program_type = await self.agent.program_classification_service.classify_program_type(context)
            logger.info(f"Tipo de programa determinado para rehabilitación: {program_type}")
            
            # Obtener definición del programa para personalizar las recomendaciones
            program_def = get_program_definition(program_type)
            
            # Preparar contexto específico del programa
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            
            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                
                # Añadir protocolos de recuperación específicos del programa si están disponibles
                if program_def.get("key_protocols") and "recovery" in program_def.get("key_protocols", {}):
                    program_context += "- Protocolos de recuperación recomendados:\n"
                    for protocol in program_def.get("key_protocols", {}).get("recovery", []):
                        program_context += f"  * {protocol}\n"
                        
                # Añadir consideraciones especiales para la rehabilitación según el programa
                if program_type == "PRIME":
                    program_context += "\nConsideraciones especiales para PRIME:\n"
                    program_context += "- Enfoque en recuperación rápida y eficiente\n"
                    program_context += "- Priorización de la funcionalidad y el rendimiento\n"
                    program_context += "- Uso de técnicas avanzadas de rehabilitación\n"
                elif program_type == "LONGEVITY":
                    program_context += "\nConsideraciones especiales para LONGEVITY:\n"
                    program_context += "- Enfoque en rehabilitación sostenible y de largo plazo\n"
                    program_context += "- Priorización de la salud articular y la prevención de recurrencias\n"
                    program_context += "- Adaptación de ejercicios para minimizar el impacto en articulaciones\n"
        except Exception as e:
            logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
            program_type = "GENERAL"
            program_context = ""
        
        # Construir el prompt para el modelo
        injury_info = f"Tipo de lesión: {injury_type}" if injury_type else "Tipo de lesión no especificado"
        phase_info = f"Fase de la lesión: {injury_phase}" if injury_phase else "Fase de la lesión no especificada"
        
        prompt = f"""
        Eres un especialista en rehabilitación física y recuperación de lesiones.
        
        El usuario solicita información sobre rehabilitación:
        "{query}"
        
        Información adicional:
        - {injury_info}
        - {phase_info}
        - Tipo de programa: {program_type}
        {program_context}
        
        Proporciona una respuesta detallada sobre cómo rehabilitar esta lesión específica,
        incluyendo fases de recuperación, ejercicios recomendados, progresión y señales de alerta.
        Adapta tus recomendaciones específicamente para el programa {program_type} del usuario.
        
        Estructura tu respuesta en secciones:
        1. Análisis de la lesión en el contexto del programa {program_type}
        2. Fases de rehabilitación adaptadas al programa {program_type}
        3. Ejercicios recomendados por fase, considerando las necesidades específicas del programa
        4. Progresión y criterios para avanzar, alineados con los objetivos del programa
        5. Señales de alerta
        6. Cuándo buscar ayuda profesional
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar protocolo de rehabilitación estructurado
        protocol_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un protocolo de rehabilitación estructurado en formato JSON con los siguientes campos:
        - injury: lesión objetivo
        - phase: fase actual de rehabilitación
        - duration: duración estimada del protocolo
        - phases: array de fases con nombre, duración, objetivos y ejercicios
        - progression_criteria: criterios para avanzar entre fases
        - contraindications: contraindicaciones
        - warning_signs: señales de alerta
        
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
                    "injury": "Lesión no especificada",
                    "phase": "Fase no especificada",
                    "duration": "6-8 semanas (estimado)",
                    "phases": [
                        {
                            "name": "Fase aguda",
                            "duration": "1-2 semanas",
                            "objectives": ["Reducir dolor e inflamación", "Proteger la lesión"],
                            "exercises": ["Reposo relativo", "Movilizaciones suaves"]
                        },
                        {
                            "name": "Fase subaguda",
                            "duration": "2-4 semanas",
                            "objectives": ["Recuperar rango de movimiento", "Iniciar fortalecimiento"],
                            "exercises": ["Estiramientos suaves", "Ejercicios isométricos"]
                        },
                        {
                            "name": "Fase de recuperación",
                            "duration": "3-6 semanas",
                            "objectives": ["Fortalecer", "Mejorar función"],
                            "exercises": ["Fortalecimiento progresivo", "Ejercicios funcionales"]
                        }
                    ],
                    "progression_criteria": ["Sin dolor en reposo", "Rango de movimiento adecuado", "Fuerza suficiente"],
                    "contraindications": ["Dolor agudo", "Inflamación severa", "Inestabilidad articular"],
                    "warning_signs": ["Aumento de dolor", "Inflamación persistente", "Pérdida de función"]
                }
        
        # Generar ejercicios recomendados
        exercises_prompt = f"""
        Basándote en la consulta del usuario sobre rehabilitación:
        "{query}"
        
        Genera una lista de 3-5 ejercicios específicos en formato JSON array, donde cada ejercicio es un objeto con:
        - name: nombre del ejercicio
        - description: descripción breve
        - phase: fase de rehabilitación en que se recomienda
        - sets: número de series
        - reps: número de repeticiones
        - frequency: frecuencia recomendada
        - progression: cómo progresar el ejercicio
        
        Devuelve SOLO el JSON array, sin explicaciones adicionales.
        """
        
        exercises_json = await gemini_client.generate_structured_output(exercises_prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(exercises_json, list):
            try:
                exercises_json = json.loads(exercises_json)
                if not isinstance(exercises_json, list):
                    exercises_json = []
            except:
                # Si no se puede convertir, crear una lista básica
                exercises_json = [
                    {
                        "name": "Ejemplo de ejercicio de rehabilitación",
                        "description": "Descripción del ejercicio",
                        "phase": "Fase subaguda",
                        "sets": 3,
                        "reps": "10-15",
                        "frequency": "2-3 veces por día",
                        "progression": "Aumentar resistencia gradualmente"
                    }
                ]
        
        return RehabilitationOutput(
            response=response_text,
            rehab_protocol=protocol_json,
            exercises=exercises_json
        )

class MobilityAssessmentSkill(GoogleADKSkill):
    name = "mobility_assessment"
    description = "Evalúa limitaciones de movilidad y proporciona estrategias para mejorar el rango de movimiento"
    input_schema = MobilityAssessmentInput
    output_schema = MobilityAssessmentOutput
    
    async def handler(self, input_data: MobilityAssessmentInput) -> MobilityAssessmentOutput:
        """Implementación de la skill de evaluación de movilidad"""
        query = input_data.query
        target_areas = input_data.target_areas or []
        movement_goals = input_data.movement_goals or []
        user_profile = input_data.user_profile or {}
        
        # Construir el prompt para el modelo
        areas_info = f"Áreas objetivo: {', '.join(target_areas)}" if target_areas else "Áreas objetivo no especificadas"
        goals_info = f"Objetivos de movimiento: {', '.join(movement_goals)}" if movement_goals else "Objetivos no especificados"
        
        prompt = f"""
        Eres un especialista en movilidad, flexibilidad y biomecánica.
        
        El usuario solicita información sobre movilidad:
        "{query}"
        
        Información adicional:
        - {areas_info}
        - {goals_info}
        
        Proporciona una respuesta detallada sobre cómo evaluar y mejorar la movilidad en las áreas específicas,
        incluyendo evaluaciones, ejercicios, progresiones y consideraciones especiales.
        
        Estructura tu respuesta en secciones:
        1. Evaluación de movilidad
        2. Limitaciones comunes
        3. Ejercicios recomendados
        4. Progresión
        5. Integración con actividades diarias/deportivas
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar evaluación de movilidad estructurada
        assessment_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera una evaluación de movilidad estructurada en formato JSON con los siguientes campos:
        - target_areas: áreas objetivo para evaluación
        - common_limitations: limitaciones comunes en estas áreas
        - assessment_tests: pruebas para evaluar la movilidad
        - mobility_goals: objetivos de movilidad recomendados
        - progression_timeline: cronograma estimado de progresión
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        assessment_json = await gemini_client.generate_structured_output(assessment_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(assessment_json, dict):
            try:
                assessment_json = json.loads(assessment_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                assessment_json = {
                    "target_areas": target_areas if target_areas else ["Cadera", "Hombros", "Columna torácica"],
                    "common_limitations": {
                        "Cadera": ["Flexión limitada", "Rotación externa reducida"],
                        "Hombros": ["Rotación interna limitada", "Elevación reducida"],
                        "Columna torácica": ["Rotación limitada", "Extensión reducida"]
                    },
                    "assessment_tests": [
                        "Test de sentadilla profunda",
                        "Test de movilidad de hombro",
                        "Test de rotación torácica"
                    ],
                    "mobility_goals": [
                        "Mejorar rango de movimiento funcional",
                        "Reducir compensaciones",
                        "Optimizar patrones de movimiento"
                    ],
                    "progression_timeline": "4-8 semanas para mejoras significativas con práctica consistente"
                }
        
        # Generar ejercicios recomendados
        exercises_prompt = f"""
        Basándote en la consulta del usuario sobre movilidad:
        "{query}"
        
        Genera una lista de 3-5 ejercicios específicos en formato JSON array, donde cada ejercicio es un objeto con:
        - name: nombre del ejercicio
        - target_area: área objetivo
        - description: descripción breve
        - sets: número de series
        - reps_duration: repeticiones o duración
        - frequency: frecuencia recomendada
        - progression: cómo progresar el ejercicio
        
        Devuelve SOLO el JSON array, sin explicaciones adicionales.
        """
        
        exercises_json = await gemini_client.generate_structured_output(exercises_prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(exercises_json, list):
            try:
                exercises_json = json.loads(exercises_json)
                if not isinstance(exercises_json, list):
                    exercises_json = []
            except:
                # Si no se puede convertir, crear una lista básica
                exercises_json = [
                    {
                        "name": "Ejemplo de ejercicio de movilidad",
                        "target_area": "Cadera",
                        "description": "Descripción del ejercicio",
                        "sets": 3,
                        "reps_duration": "30-60 segundos",
                        "frequency": "Diario",
                        "progression": "Aumentar rango de movimiento gradualmente"
                    }
                ]
        
        return MobilityAssessmentOutput(
            response=response_text,
            mobility_assessment=assessment_json,
            exercises=exercises_json
        )

class SleepOptimizationSkill(GoogleADKSkill):
    name = "sleep_optimization"
    description = "Proporciona estrategias personalizadas para mejorar la calidad y cantidad del sueño"
    input_schema = SleepOptimizationInput
    output_schema = SleepOptimizationOutput
    
    async def handler(self, input_data: SleepOptimizationInput) -> SleepOptimizationOutput:
        """Implementación de la skill de optimización del sueño"""
        query = input_data.query
        sleep_issues = input_data.sleep_issues or []
        sleep_data = input_data.sleep_data or {}
        user_profile = input_data.user_profile or {}
        
        # Determinar el tipo de programa del usuario para personalizar las recomendaciones
        context = {
            "user_profile": user_profile,
            "goals": user_profile.get("goals", []) if user_profile else []
        }
        
        try:
            # Clasificar el tipo de programa del usuario
            program_type = await self.agent.program_classification_service.classify_program_type(context)
            logger.info(f"Tipo de programa determinado para optimización del sueño: {program_type}")
            
            # Obtener definición del programa para personalizar las recomendaciones
            program_def = get_program_definition(program_type)
            
            # Preparar contexto específico del programa
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            
            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                
                # Añadir protocolos de sueño específicos del programa si están disponibles
                if program_def.get("key_protocols") and "sleep" in program_def.get("key_protocols", {}):
                    program_context += "- Protocolos de sueño recomendados:\n"
                    for protocol in program_def.get("key_protocols", {}).get("sleep", []):
                        program_context += f"  * {protocol}\n"
                        
                # Añadir consideraciones especiales para la optimización del sueño según el programa
                if program_type == "PRIME":
                    program_context += "\nConsideraciones especiales para PRIME:\n"
                    program_context += "- Enfoque en sueño para optimizar rendimiento y recuperación\n"
                    program_context += "- Priorización de estrategias para maximizar el sueño profundo y REM\n"
                    program_context += "- Uso de técnicas avanzadas de optimización del sueño\n"
                elif program_type == "LONGEVITY":
                    program_context += "\nConsideraciones especiales para LONGEVITY:\n"
                    program_context += "- Enfoque en sueño para promover la longevidad y salud celular\n"
                    program_context += "- Priorización de la regularidad y duración del sueño\n"
                    program_context += "- Estrategias para minimizar la inflamación y optimizar la reparación celular\n"
        except Exception as e:
            logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
            program_type = "GENERAL"
            program_context = ""
        
        # Construir el prompt para el modelo
        issues_info = f"Problemas de sueño: {', '.join(sleep_issues)}" if sleep_issues else "Problemas de sueño no especificados"
        data_info = "Datos de sueño disponibles" if sleep_data else "Sin datos de sueño específicos"
        
        prompt = f"""
        Eres un especialista en optimización del sueño y recuperación.
        
        El usuario solicita información sobre optimización del sueño:
        "{query}"
        
        Información adicional:
        - {issues_info}
        - {data_info}
        - Tipo de programa: {program_type}
        {program_context}
        
        Proporciona una respuesta detallada sobre cómo mejorar la calidad y cantidad del sueño,
        incluyendo estrategias de higiene del sueño, rutinas, entorno óptimo y consideraciones especiales.
        Adapta tus recomendaciones específicamente para el programa {program_type} del usuario.
        
        Estructura tu respuesta en secciones:
        1. Análisis de los problemas de sueño en el contexto del programa {program_type}
        2. Estrategias de higiene del sueño adaptadas al programa {program_type}
        3. Optimización del entorno para maximizar los beneficios del programa
        4. Rutinas recomendadas alineadas con los objetivos del programa
        5. Suplementos y ayudas naturales específicas para el programa (si aplica)
        6. Cuándo buscar ayuda profesional
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar plan de optimización del sueño estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan de optimización del sueño estructurado en formato JSON con los siguientes campos:
        - sleep_issues: problemas de sueño identificados
        - sleep_goals: objetivos de mejora del sueño
        - environment_optimization: optimización del entorno de sueño
        - pre_sleep_routine: rutina recomendada antes de dormir
        - morning_routine: rutina matutina recomendada
        - supplements: suplementos naturales a considerar (si aplica)
        - tracking_metrics: métricas para seguimiento
        
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
                    "sleep_issues": sleep_issues if sleep_issues else ["Dificultad para conciliar el sueño", "Despertares nocturnos"],
                    "sleep_goals": ["Reducir latencia del sueño", "Mejorar continuidad", "Optimizar calidad"],
                    "environment_optimization": {
                        "temperature": "18-20°C (65-68°F)",
                        "light": "Oscuridad completa, sin luces LED",
                        "noise": "Silencio o ruido blanco constante",
                        "bedding": "Colchón y almohada adecuados para postura neutral"
                    },
                    "pre_sleep_routine": [
                        "Apagar pantallas 1 hora antes",
                        "Luz tenue y cálida",
                        "Actividad relajante (lectura, meditación)",
                        "Temperatura corporal: ducha tibia"
                    ],
                    "morning_routine": [
                        "Exposición a luz natural",
                        "Hidratación inmediata",
                        "Actividad física ligera",
                        "Desayuno equilibrado"
                    ],
                    "supplements": [
                        "Magnesio (200-400mg)",
                        "Melatonina (0.3-1mg, solo temporal)",
                        "Té de hierbas (manzanilla, valeriana)"
                    ],
                    "tracking_metrics": [
                        "Tiempo total de sueño",
                        "Latencia del sueño",
                        "Número de despertares",
                        "Calidad subjetiva (1-10)",
                        "Energía matutina (1-10)"
                    ]
                }
        
        # Generar recomendaciones específicas
        recommendations_prompt = f"""
        Basándote en la consulta del usuario sobre optimización del sueño:
        "{query}"
        
        Genera una lista de 5-7 recomendaciones específicas y accionables en formato JSON array.
        Cada recomendación debe ser concreta, práctica y fácil de implementar.
        
        Devuelve SOLO el JSON array de strings, sin explicaciones adicionales.
        """
        
        recommendations_json = await gemini_client.generate_structured_output(recommendations_prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(recommendations_json, list):
            try:
                recommendations_json = json.loads(recommendations_json)
                if not isinstance(recommendations_json, list):
                    recommendations_json = []
            except:
                # Si no se puede convertir, crear una lista básica
                recommendations_json = [
                    "Mantén un horario constante de sueño, incluso los fines de semana",
                    "Evita cafeína después del mediodía",
                    "Crea un ritual nocturno relajante de 30 minutos",
                    "Mantén tu habitación fresca (18-20°C) y completamente oscura",
                    "Exponte a luz natural brillante en las primeras horas de la mañana"
                ]
        
        return SleepOptimizationOutput(
            response=response_text,
            sleep_plan=plan_json,
            recommendations=recommendations_json
        )

class HRVProtocolSkill(GoogleADKSkill):
    name = "hrv_protocols"
    description = "Interpreta datos de variabilidad de frecuencia cardíaca y desarrolla estrategias basadas en ellos"
    input_schema = HRVProtocolInput
    output_schema = HRVProtocolOutput
    
    async def handler(self, input_data: HRVProtocolInput) -> HRVProtocolOutput:
        """Implementación de la skill de protocolos HRV"""
        query = input_data.query
        hrv_data = input_data.hrv_data or {}
        training_context = input_data.training_context or {}
        user_profile = input_data.user_profile or {}
        
        # Determinar el tipo de programa del usuario para personalizar las recomendaciones
        context = {
            "user_profile": user_profile,
            "goals": user_profile.get("goals", []) if user_profile else []
        }
        
        try:
            # Clasificar el tipo de programa del usuario
            program_type = await self.agent.program_classification_service.classify_program_type(context)
            logger.info(f"Tipo de programa determinado para protocolos HRV: {program_type}")
            
            # Obtener definición del programa para personalizar las recomendaciones
            program_def = get_program_definition(program_type)
            
            # Preparar contexto específico del programa
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            
            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                
                # Añadir protocolos de recuperación específicos del programa si están disponibles
                if program_def.get("key_protocols") and "recovery" in program_def.get("key_protocols", {}):
                    program_context += "- Protocolos de recuperación recomendados:\n"
                    for protocol in program_def.get("key_protocols", {}).get("recovery", []):
                        program_context += f"  * {protocol}\n"
                        
                # Añadir consideraciones especiales para HRV según el programa
                if program_type == "PRIME":
                    program_context += "\nConsideraciones especiales de HRV para PRIME:\n"
                    program_context += "- Enfoque en HRV para optimizar rendimiento y periodización del entrenamiento\n"
                    program_context += "- Uso de HRV para determinar intensidad y volumen de entrenamiento\n"
                    program_context += "- Estrategias de recuperación basadas en HRV para maximizar adaptaciones\n"
                elif program_type == "LONGEVITY":
                    program_context += "\nConsideraciones especiales de HRV para LONGEVITY:\n"
                    program_context += "- Enfoque en HRV como biomarcador de salud cardiovascular y longevidad\n"
                    program_context += "- Uso de HRV para monitorizar el balance autónomo y estrés crónico\n"
                    program_context += "- Estrategias para mejorar el HRV a largo plazo\n"
        except Exception as e:
            logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
            program_type = "GENERAL"
            program_context = ""
        
        # Construir el prompt para el modelo
        data_info = "Datos de HRV disponibles" if hrv_data else "Sin datos de HRV específicos"
        context_info = "Contexto de entrenamiento disponible" if training_context else "Sin contexto de entrenamiento específico"
        
        prompt = f"""
        Eres un especialista en variabilidad de la frecuencia cardíaca (HRV) y su aplicación para optimizar entrenamiento y recuperación.
        
        El usuario solicita información sobre HRV:
        "{query}"
        
        Información adicional:
        - {data_info}
        - {context_info}
        - Tipo de programa: {program_type}
        {program_context}
        
        Proporciona una respuesta detallada sobre cómo interpretar y utilizar los datos de HRV,
        incluyendo su significado, aplicaciones prácticas, estrategias de implementación y consideraciones especiales.
        Adapta tus recomendaciones específicamente para el programa {program_type} del usuario.
        
        Estructura tu respuesta en secciones:
        1. Interpretación de los datos de HRV en el contexto del programa {program_type}
        2. Implicaciones para entrenamiento/recuperación alineadas con los objetivos del programa
        3. Estrategias recomendadas específicas para el programa {program_type}
        4. Implementación práctica considerando las necesidades del programa
        5. Factores que afectan el HRV relevantes para el programa
        6. Seguimiento y ajustes para optimizar resultados dentro del programa
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar protocolo HRV estructurado
        protocol_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un protocolo de HRV estructurado en formato JSON con los siguientes campos:
        - interpretation: interpretación de los valores de HRV
        - baseline_establishment: cómo establecer una línea base
        - training_adjustments: ajustes de entrenamiento basados en HRV
        - recovery_strategies: estrategias de recuperación
        - lifestyle_factors: factores de estilo de vida que afectan el HRV
        - measurement_protocol: protocolo de medición recomendado
        - decision_framework: marco de decisión basado en valores de HRV
        
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
                    "interpretation": {
                        "high_hrv": "Buena recuperación, sistema nervioso equilibrado",
                        "normal_hrv": "Recuperación adecuada, balance autonómico normal",
                        "low_hrv": "Recuperación insuficiente, predominio simpático"
                    },
                    "baseline_establishment": "Medir diariamente durante 2-3 semanas en las mismas condiciones",
                    "training_adjustments": {
                        "high_hrv": "Entrenamiento de alta intensidad/volumen apropiado",
                        "normal_hrv": "Seguir plan de entrenamiento normal",
                        "low_hrv": "Reducir intensidad/volumen, priorizar recuperación"
                    },
                    "recovery_strategies": [
                        "Sueño optimizado",
                        "Nutrición adecuada",
                        "Manejo del estrés",
                        "Técnicas de respiración",
                        "Exposición a frío/calor"
                    ],
                    "lifestyle_factors": [
                        "Calidad del sueño",
                        "Estrés psicológico",
                        "Hidratación",
                        "Nutrición",
                        "Alcohol y cafeína"
                    ],
                    "measurement_protocol": "Medición matutina, en ayunas, después de despertar, posición constante",
                    "decision_framework": {
                        "baseline": "Establecer línea base individual",
                        "daily_comparison": "Comparar con línea base y tendencia reciente",
                        "thresholds": "Establecer umbrales personalizados para toma de decisiones",
                        "context": "Considerar factores contextuales (estrés, sueño, etc.)"
                    }
                }
        
        # Generar recomendaciones específicas
        recommendations_prompt = f"""
        Basándote en la consulta del usuario sobre HRV:
        "{query}"
        
        Genera una lista de 5-7 recomendaciones específicas y accionables en formato JSON array.
        Cada recomendación debe ser concreta, práctica y fácil de implementar.
        
        Devuelve SOLO el JSON array de strings, sin explicaciones adicionales.
        """
        
        recommendations_json = await gemini_client.generate_structured_output(recommendations_prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(recommendations_json, list):
            try:
                recommendations_json = json.loads(recommendations_json)
                if not isinstance(recommendations_json, list):
                    recommendations_json = []
            except:
                # Si no se puede convertir, crear una lista básica
                recommendations_json = [
                    "Mide tu HRV cada mañana al despertar, en la misma posición",
                    "Establece una línea base con al menos 2 semanas de mediciones",
                    "Reduce la intensidad del entrenamiento cuando tu HRV esté 10% por debajo de tu línea base",
                    "Practica técnicas de respiración lenta (6 respiraciones/minuto) para mejorar tu HRV",
                    "Evita alcohol, comidas pesadas y pantallas antes de dormir para optimizar tu HRV nocturno"
                ]
        
        return HRVProtocolOutput(
            response=response_text,
            hrv_protocol=protocol_json,
            recommendations=recommendations_json
        )

class ChronicPainSkill(GoogleADKSkill):
    name = "chronic_pain_management"
    description = "Desarrolla estrategias integrales para el manejo del dolor agudo y crónico"
    input_schema = ChronicPainInput
    output_schema = ChronicPainOutput
    
    async def handler(self, input_data: ChronicPainInput) -> ChronicPainOutput:
        """Implementación de la skill de manejo del dolor crónico"""
        query = input_data.query
        pain_location = input_data.pain_location
        pain_intensity = input_data.pain_intensity
        pain_duration = input_data.pain_duration
        user_profile = input_data.user_profile or {}
        
        # Determinar el tipo de programa del usuario para personalizar las recomendaciones
        context = {
            "user_profile": user_profile,
            "goals": user_profile.get("goals", []) if user_profile else []
        }
        
        try:
            # Clasificar el tipo de programa del usuario
            program_type = await self.agent.program_classification_service.classify_program_type(context)
            logger.info(f"Tipo de programa determinado para manejo del dolor crónico: {program_type}")
            
            # Obtener definición del programa para personalizar las recomendaciones
            program_def = get_program_definition(program_type)
            
            # Preparar contexto específico del programa
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            
            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                
                # Añadir protocolos de manejo del dolor específicos del programa si están disponibles
                if program_def.get("key_protocols") and "pain_management" in program_def.get("key_protocols", {}):
                    program_context += "- Protocolos de manejo del dolor recomendados:\n"
                    for protocol in program_def.get("key_protocols", {}).get("pain_management", []):
                        program_context += f"  * {protocol}\n"
                        
                # Añadir consideraciones especiales para el manejo del dolor según el programa
                if program_type == "PRIME":
                    program_context += "\nConsideraciones especiales para PRIME:\n"
                    program_context += "- Enfoque en manejo del dolor para mantener el rendimiento\n"
                    program_context += "- Estrategias para minimizar el tiempo de inactividad\n"
                    program_context += "- Técnicas avanzadas de manejo del dolor para atletas\n"
                elif program_type == "LONGEVITY":
                    program_context += "\nConsideraciones especiales para LONGEVITY:\n"
                    program_context += "- Enfoque en manejo del dolor a largo plazo y sostenible\n"
                    program_context += "- Estrategias para mejorar la calidad de vida y funcionalidad\n"
                    program_context += "- Técnicas de manejo del dolor adaptadas para adultos mayores\n"
                    program_context += "- Consideraciones especiales para condiciones crónicas relacionadas con la edad\n"
        except Exception as e:
            logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
            program_type = "GENERAL"
            program_context = ""
        
        # Construir el prompt para el modelo
        location_info = f"Ubicación del dolor: {pain_location}" if pain_location else "Ubicación del dolor no especificada"
        intensity_info = f"Intensidad del dolor: {pain_intensity}/10" if pain_intensity else "Intensidad del dolor no especificada"
        duration_info = f"Duración del dolor: {pain_duration}" if pain_duration else "Duración del dolor no especificada"
        
        prompt = f"""
        Eres un especialista en manejo del dolor y rehabilitación.
        
        El usuario solicita información sobre manejo del dolor:
        "{query}"
        
        Información adicional:
        - {location_info}
        - {intensity_info}
        - {duration_info}
        - Tipo de programa: {program_type}
        {program_context}
        
        Proporciona una respuesta detallada sobre cómo manejar este dolor específico,
        incluyendo estrategias no farmacológicas, ejercicios, modificaciones de actividad y consideraciones especiales.
        Adapta tus recomendaciones específicamente para el programa {program_type} del usuario.
        
        Estructura tu respuesta en secciones:
        1. Evaluación del dolor en el contexto del programa {program_type}
        2. Estrategias de manejo no farmacológicas alineadas con los objetivos del programa
        3. Ejercicios recomendados considerando las necesidades específicas del programa
        4. Modificaciones de actividad para mantener la funcionalidad dentro del programa
        5. Cuándo buscar ayuda profesional
        
        IMPORTANTE: Aclara que tus recomendaciones no reemplazan la atención médica profesional.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar evaluación del dolor estructurada
        assessment_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera una evaluación del dolor estructurada en formato JSON con los siguientes campos:
        - location: ubicación del dolor
        - intensity: intensidad estimada (1-10)
        - characteristics: características del dolor
        - aggravating_factors: factores que empeoran el dolor
        - relieving_factors: factores que alivian el dolor
        - impact: impacto en actividades diarias
        - possible_causes: posibles causas (aclarar que es educativo, no diagnóstico)
        - red_flags: señales de alerta que requieren atención médica
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        assessment_json = await gemini_client.generate_structured_output(assessment_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(assessment_json, dict):
            try:
                assessment_json = json.loads(assessment_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                assessment_json = {
                    "location": pain_location if pain_location else "No especificada",
                    "intensity": pain_intensity if pain_intensity else "No especificada",
                    "characteristics": "No especificadas",
                    "aggravating_factors": ["No especificados"],
                    "relieving_factors": ["No especificados"],
                    "impact": "No especificado",
                    "possible_causes": ["Nota: Esta información es educativa, no diagnóstica"],
                    "red_flags": [
                        "Dolor severo que no responde a medidas básicas",
                        "Entumecimiento o debilidad progresiva",
                        "Problemas de control de vejiga/intestino",
                        "Fiebre asociada al dolor"
                    ]
                }
        
        # Generar plan de manejo del dolor estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario sobre dolor:
        "{query}"
        
        Genera un plan de manejo del dolor estructurado en formato JSON con los siguientes campos:
        - non_pharmacological: estrategias no farmacológicas
        - movement_strategies: estrategias de movimiento
        - lifestyle_modifications: modificaciones de estilo de vida
        - self_management: técnicas de autogestión
        - pacing_strategies: estrategias de dosificación de actividad
        - progression: progresión recomendada
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        management_json = await gemini_client.generate_structured_output(plan_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(management_json, dict):
            try:
                management_json = json.loads(management_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                management_json = {
                    "non_pharmacological": [
                        "Aplicación de calor/frío",
                        "Técnicas de relajación",
                        "Meditación mindfulness"
                    ],
                    "movement_strategies": [
                        "Movimiento gradual y controlado",
                        "Evitar inmovilización prolongada",
                        "Ejercicio de baja intensidad"
                    ],
                    "lifestyle_modifications": [
                        "Optimización del sueño",
                        "Manejo del estrés",
                        "Nutrición antiinflamatoria"
                    ],
                    "self_management": [
                        "Diario de dolor",
                        "Técnicas de respiración",
                        "Establecimiento de objetivos realistas"
                    ],
                    "pacing_strategies": [
                        "Alternar actividad y descanso",
                        "Incremento gradual de actividad",
                        "Evitar ciclos de sobreactividad-descanso forzado"
                    ],
                    "progression": "Incremento gradual de actividad basado en tiempo, no en dolor"
                }
        
        # Generar recomendaciones específicas
        recommendations_prompt = f"""
        Basándote en la consulta del usuario sobre dolor:
        "{query}"
        
        Genera una lista de 5-7 recomendaciones específicas y accionables en formato JSON array.
        Cada recomendación debe ser concreta, práctica y fácil de implementar.
        
        Devuelve SOLO el JSON array de strings, sin explicaciones adicionales.
        """
        
        recommendations_json = await gemini_client.generate_structured_output(recommendations_prompt)
        
        # Si la respuesta no es una lista, intentar convertirla
        if not isinstance(recommendations_json, list):
            try:
                recommendations_json = json.loads(recommendations_json)
                if not isinstance(recommendations_json, list):
                    recommendations_json = []
            except:
                # Si no se puede convertir, crear una lista básica
                recommendations_json = [
                    "Comienza con 5-10 minutos de movimiento suave cada mañana",
                    "Aplica calor húmedo durante 15-20 minutos para aliviar la tensión muscular",
                    "Practica respiración diafragmática 3 veces al día durante 5 minutos",
                    "Establece un horario regular de sueño para optimizar la recuperación",
                    "Lleva un diario de dolor para identificar patrones y desencadenantes"
                ]
        
        return ChronicPainOutput(
            response=response_text,
            pain_assessment=assessment_json,
            management_plan=management_json,
            recommendations=recommendations_json
        )

class GeneralRecoverySkill(GoogleADKSkill):
    name = "general_recovery"
    description = "Proporciona información general sobre recuperación y responde a consultas diversas sobre el tema"
    input_schema = GeneralRecoveryInput
    output_schema = GeneralRecoveryOutput
    
    async def handler(self, input_data: GeneralRecoveryInput) -> GeneralRecoveryOutput:
        """Implementación de la skill general de recuperación"""
        query = input_data.query
        context = input_data.context or {}
        user_profile = input_data.user_profile or {}
        
        # Construir el prompt para el modelo
        context_info = "Contexto adicional disponible" if context else "Sin contexto adicional"
        
        prompt = f"""
        Eres un especialista en recuperación física, bienestar y optimización del rendimiento.
        
        El usuario solicita información general sobre recuperación:
        "{query}"
        
        Información adicional:
        - {context_info}
        
        Proporciona una respuesta detallada y útil sobre el tema de recuperación,
        incluyendo principios fundamentales, estrategias prácticas y consideraciones especiales.
        
        Estructura tu respuesta de manera clara y organizada, con secciones relevantes al tema consultado.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar protocolo de recuperación estructurado si es aplicable
        protocol_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Si la consulta se relaciona con un protocolo específico de recuperación, genera un protocolo estructurado en formato JSON.
        Si la consulta es demasiado general o no se relaciona con un protocolo específico, devuelve null.
        
        El protocolo debe incluir campos relevantes como:
        - objective: objetivo principal del protocolo
        - strategies: estrategias principales
        - timeline: cronograma recomendado
        - implementation: pasos de implementación
        - monitoring: métricas de seguimiento
        
        Devuelve SOLO el JSON o null, sin explicaciones adicionales.
        """
        
        protocol_json = await gemini_client.generate_structured_output(protocol_prompt)
        
        # Si la respuesta no es un diccionario ni None, intentar convertirla
        if protocol_json is not None and not isinstance(protocol_json, dict):
            try:
                protocol_json = json.loads(protocol_json)
            except:
                # Si no se puede convertir, establecer como None
                protocol_json = None
        
        return GeneralRecoveryOutput(
            response=response_text,
            recovery_protocol=protocol_json
        )

class PostureAnalysisSkill(GoogleADKSkill):
    name = "posture_analysis"
    description = "Analiza la postura a partir de imágenes y proporciona recomendaciones para mejorarla"
    input_schema = PostureAnalysisInput
    output_schema = PostureAnalysisOutput
    
    async def handler(self, input_data: PostureAnalysisInput) -> PostureAnalysisOutput:
        """Implementación de la skill de análisis de postura"""
        image_data = input_data.image_data
        user_id = input_data.user_id or "usuario_anónimo"
        analysis_type = input_data.analysis_type or "general"
        focus_areas = input_data.focus_areas or ["columna", "hombros", "pelvis", "rodillas"]
        user_profile = input_data.user_profile or {}
        
        # Verificar si las capacidades de visión están disponibles
        if not hasattr(self.agent, '_vision_capabilities_available') or not self.agent._vision_capabilities_available:
            logger.warning("Las capacidades de visión no están disponibles. Usando análisis simulado.")
            return await self._generate_mock_posture_analysis(input_data)
        
        try:
            # Determinar el tipo de programa del usuario para personalizar las recomendaciones
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.agent.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para análisis de postura: {program_type}")
                
                # Obtener definición del programa para personalizar las recomendaciones
                program_def = get_program_definition(program_type)
                
                # Preparar contexto específico del programa
                program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir consideraciones especiales para el análisis de postura según el programa
                    if program_type == "PRIME":
                        program_context += "\nConsideraciones especiales para PRIME:\n"
                        program_context += "- Enfoque en postura óptima para rendimiento\n"
                        program_context += "- Análisis de alineación para prevenir lesiones durante entrenamiento intenso\n"
                        program_context += "- Consideraciones para patrones de movimiento específicos del deporte\n"
                    elif program_type == "LONGEVITY":
                        program_context += "\nConsideraciones especiales para LONGEVITY:\n"
                        program_context += "- Enfoque en postura para salud articular a largo plazo\n"
                        program_context += "- Análisis de patrones compensatorios relacionados con la edad\n"
                        program_context += "- Consideraciones para condiciones crónicas y limitaciones existentes\n"
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
                program_type = "GENERAL"
                program_context = ""
            
            # Utilizar las capacidades de visión del agente
            with self.agent.tracer.start_as_current_span("posture_analysis"):
                # Analizar la imagen utilizando el procesador de visión
                vision_analysis = await self.agent.vision_processor.analyze_image(image_data)
                
                # Extraer análisis de postura usando el modelo multimodal
                prompt = f"""
                Eres un experto en análisis postural y biomecánica. Analiza esta imagen
                de un usuario con programa tipo {program_type} y proporciona un análisis detallado
                de su postura.
                
                Tipo de análisis: {analysis_type}
                
                Enfócate específicamente en las siguientes áreas:
                {', '.join(focus_areas)}
                
                {program_context}
                
                Proporciona:
                1. Un resumen general de la postura observada
                2. Análisis detallado de alineación
                3. Desequilibrios posturales identificados
                4. Posibles implicaciones para el movimiento y la función
                5. Recomendaciones específicas para mejorar la postura
                
                Sé objetivo, detallado y proporciona feedback constructivo basado en lo que observas.
                """
                
                multimodal_result = await self.agent.multimodal_adapter.analyze_image(
                    image_data=image_data,
                    analysis_prompt=prompt,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer evaluación postural estructurada
                assessment_prompt = f"""
                Basándote en el siguiente análisis postural, extrae una evaluación estructurada
                en formato JSON con los siguientes campos:
                1. head_position: posición de la cabeza
                2. shoulder_alignment: alineación de hombros
                3. spine_alignment: alineación de columna
                4. pelvic_position: posición pélvica
                5. knee_alignment: alineación de rodillas
                6. foot_position: posición de pies
                7. overall_assessment: evaluación general
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                assessment_response = await self.agent.gemini_client.generate_structured_output(assessment_prompt)
                
                # Procesar evaluación postural
                if not isinstance(assessment_response, dict):
                    try:
                        assessment_response = json.loads(assessment_response)
                    except:
                        assessment_response = {
                            "head_position": "No determinado",
                            "shoulder_alignment": "No determinado",
                            "spine_alignment": "No determinado",
                            "pelvic_position": "No determinado",
                            "knee_alignment": "No determinado",
                            "foot_position": "No determinado",
                            "overall_assessment": "No se pudo determinar con precisión"
                        }
                
                # Extraer desequilibrios posturales
                imbalances_prompt = f"""
                Basándote en el siguiente análisis postural, extrae los desequilibrios posturales
                en formato JSON array, donde cada elemento es un objeto con:
                1. area: área afectada
                2. description: descripción del desequilibrio
                3. severity: severidad (leve, moderada, significativa)
                4. implications: implicaciones para el movimiento y la función
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                imbalances_response = await self.agent.gemini_client.generate_structured_output(imbalances_prompt)
                
                # Procesar desequilibrios posturales
                if not isinstance(imbalances_response, list):
                    try:
                        imbalances_response = json.loads(imbalances_response)
                        if not isinstance(imbalances_response, list):
                            imbalances_response = []
                    except:
                        imbalances_response = []
                
                # Si no hay desequilibrios, crear algunos genéricos
                if not imbalances_response:
                    imbalances_response = [
                        {
                            "area": "General",
                            "description": "No se pudieron determinar desequilibrios específicos",
                            "severity": "indeterminada",
                            "implications": "Indeterminadas"
                        }
                    ]
                
                # Extraer recomendaciones
                recommendations_prompt = f"""
                Basándote en el siguiente análisis postural, genera 3-5 recomendaciones específicas
                para mejorar la postura. Considera el contexto del programa {program_type}.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve las recomendaciones como una lista de strings.
                """
                
                recommendations_response = await self.agent.gemini_client.generate_structured_output(recommendations_prompt)
                
                # Procesar recomendaciones
                if not isinstance(recommendations_response, list):
                    try:
                        recommendations_response = json.loads(recommendations_response)
                        if not isinstance(recommendations_response, list):
                            recommendations_response = []
                    except:
                        recommendations_response = []
                
                # Si no hay recomendaciones, crear algunas genéricas
                if not recommendations_response:
                    recommendations_response = [
                        "Mantener conciencia postural durante actividades diarias",
                        "Realizar ejercicios de fortalecimiento para músculos posturales clave",
                        "Incorporar estiramientos para áreas con tensión",
                        "Considerar una evaluación postural profesional para recomendaciones más específicas"
                    ]
                
                # Generar ejercicios correctivos
                exercises_prompt = f"""
                Basándote en el siguiente análisis postural, genera 3-5 ejercicios correctivos
                en formato JSON array, donde cada ejercicio es un objeto con:
                - name: nombre del ejercicio
                - target_area: área objetivo
                - description: descripción breve
                - sets: número de series
                - reps: número de repeticiones
                - frequency: frecuencia recomendada
                - notes: notas adicionales (opcional)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve SOLO el JSON array, sin explicaciones adicionales.
                """
                
                exercises_response = await self.agent.gemini_client.generate_structured_output(exercises_prompt)
                
                # Procesar ejercicios correctivos
                if not isinstance(exercises_response, list):
                    try:
                        exercises_response = json.loads(exercises_response)
                        if not isinstance(exercises_response, list):
                            exercises_response = []
                    except:
                        exercises_response = []
                
                # Extraer resumen de la postura
                posture_summary = multimodal_result.get("text", "").split("\n\n")[0] if multimodal_result.get("text") else "No se pudo generar un resumen de la postura."
                
                # Crear la salida de la skill
                analysis_id = f"posture_{user_id}_{uuid.uuid4().hex[:8]}"
                return PostureAnalysisOutput(
                    analysis_id=analysis_id,
                    posture_summary=posture_summary,
                    posture_assessment=assessment_response,
                    imbalances=imbalances_response,
                    recommendations=recommendations_response,
                    corrective_exercises=exercises_response
                )
                
        except Exception as e:
            logger.error(f"Error al analizar postura: {e}", exc_info=True)
            
            # En caso de error, devolver un análisis básico
            return PostureAnalysisOutput(
                analysis_id=f"posture_{user_id}_{uuid.uuid4().hex[:8]}",
                posture_summary="No se pudo realizar el análisis debido a un error en el procesamiento.",
                posture_assessment={
                    "head_position": "No determinado",
                    "shoulder_alignment": "No determinado",
                    "spine_alignment": "No determinado",
                    "pelvic_position": "No determinado",
                    "knee_alignment": "No determinado",
                    "foot_position": "No determinado",
                    "overall_assessment": "Error en el procesamiento"
                },
                imbalances=[
                    {
                        "area": "General",
                        "description": "No se pudieron determinar desequilibrios debido a un error",
                        "severity": "indeterminada",
                        "implications": "Indeterminadas"
                    }
                ],
                recommendations=[
                    "Intente nuevamente con una imagen de mejor calidad o en mejor iluminación.",
                    "Considere consultar a un profesional para una evaluación postural en persona."
                ],
                corrective_exercises=None
            )
    
    async def _generate_mock_posture_analysis(self, input_data: PostureAnalysisInput) -> PostureAnalysisOutput:
        """Genera un análisis postural simulado cuando las capacidades de visión no están disponibles."""
        logger.info("Generando análisis postural simulado")
        
        user_id = input_data.user_id or "usuario_anónimo"
        focus_areas = input_data.focus_areas or ["columna", "hombros", "pelvis", "rodillas"]
        
        # Generar un ID de análisis
        analysis_id = f"posture_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Generar evaluación postural simulada
        posture_assessment = {
            "head_position": "Ligeramente adelantada",
            "shoulder_alignment": "Hombro derecho elevado",
            "spine_alignment": "Curvatura lumbar aumentada",
            "pelvic_position": "Anteversión pélvica leve",
            "knee_alignment": "Rotación interna leve",
            "foot_position": "Pronación moderada",
            "overall_assessment": "Postura con desviaciones leves a moderadas"
        }
        
        # Generar desequilibrios posturales simulados
        imbalances = [
            {
                "area": "Hombros",
                "description": "Elevación del hombro derecho con protracción bilateral",
                "severity": "moderada",
                "implications": "Puede contribuir a tensión en trapecio y limitación en rotación glenohumeral"
            },
            {
                "area": "Columna lumbar",
                "description": "Hiperlordosis lumbar",
                "severity": "leve",
                "implications": "Puede aumentar compresión en facetas articulares y contribuir a tensión en erectores espinales"
            },
            {
                "area": "Pelvis",
                "description": "Anteversión pélvica",
                "severity": "leve",
                "implications": "Puede contribuir a hiperlordosis lumbar y tensión en flexores de cadera"
            }
        ]
        
        # Generar recomendaciones simuladas
        recommendations = [
            "Fortalecer musculatura estabilizadora de escápula para mejorar alineación de hombros",
            "Incorporar ejercicios de estabilidad central para mejorar control lumbopélvico",
            "Estirar flexores de cadera para reducir anteversión pélvica",
            "Practicar ejercicios de conciencia postural durante actividades diarias",
            "Considerar una evaluación biomecánica completa con un profesional"
        ]
        
        # Generar ejercicios correctivos simulados
        corrective_exercises = [
            {
                "name": "Retracción escapular con banda",
                "target_area": "Hombros",
                "description": "De pie, con banda elástica sujeta frente a ti, lleva los hombros hacia atrás y abajo",
                "sets": 3,
                "reps": "12-15",
                "frequency": "Diario",
                "notes": "Mantener posición 2-3 segundos en cada repetición"
            },
            {
                "name": "Puente de glúteos",
                "target_area": "Pelvis/Core",
                "description": "Tumbado boca arriba, rodillas flexionadas, elevar cadera manteniendo core estable",
                "sets": 3,
                "reps": "10-12",
                "frequency": "3-4 veces por semana",
                "notes": "Enfocarse en activación de glúteos, no lumbar"
            },
            {
                "name": "Estiramiento de psoas",
                "target_area": "Flexores de cadera",
                "description": "En posición de caballero, avanzar la cadera hacia adelante manteniendo core estable",
                "sets": 2,
                "reps": "30-60 segundos por lado",
                "frequency": "Diario",
                "notes": "Mantener posición neutra de columna"
            }
        ]
        
        # Generar resumen simulado
        posture_summary = (
            f"Análisis simulado de postura para el usuario {user_id}. "
            f"Se observan desviaciones leves a moderadas en las áreas de enfoque: {', '.join(focus_areas)}. "
            "Las principales observaciones incluyen protracción y elevación asimétrica de hombros, "
            "hiperlordosis lumbar leve y anteversión pélvica. "
            "Estos patrones pueden contribuir a tensión muscular y restricciones de movimiento. "
            "Este es un análisis simulado debido a que las capacidades de visión no están disponibles."
        )
        
        return PostureAnalysisOutput(
            analysis_id=analysis_id,
            posture_summary=posture_summary,
            posture_assessment=posture_assessment,
            imbalances=imbalances,
            recommendations=recommendations,
            corrective_exercises=corrective_exercises
        )

class MovementAnalysisSkill(GoogleADKSkill):
    name = "movement_analysis"
    description = "Analiza patrones de movimiento a partir de videos o secuencias de imágenes"
    input_schema = MovementAnalysisInput
    output_schema = MovementAnalysisOutput
    
    async def handler(self, input_data: MovementAnalysisInput) -> MovementAnalysisOutput:
        """Implementación de la skill de análisis de movimiento"""
        video_data = input_data.video_data
        image_sequence = input_data.image_sequence or []
        movement_type = input_data.movement_type
        user_id = input_data.user_id or "usuario_anónimo"
        user_profile = input_data.user_profile or {}
        
        # Verificar si las capacidades de visión están disponibles
        if not hasattr(self.agent, '_vision_capabilities_available') or not self.agent._vision_capabilities_available:
            logger.warning("Las capacidades de visión no están disponibles. Usando análisis simulado.")
            return await self._generate_mock_movement_analysis(input_data)
        
        try:
            # Determinar el tipo de programa del usuario para personalizar las recomendaciones
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.agent.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para análisis de movimiento: {program_type}")
                
                # Obtener definición del programa para personalizar las recomendaciones
                program_def = get_program_definition(program_type)
                
                # Preparar contexto específico del programa
                program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir consideraciones especiales para el análisis de movimiento según el programa
                    if program_type == "PRIME":
                        program_context += "\nConsideraciones especiales para PRIME:\n"
                        program_context += "- Enfoque en optimización de técnica para rendimiento\n"
                        program_context += "- Análisis de eficiencia mecánica y transferencia de fuerza\n"
                        program_context += "- Consideraciones para patrones de movimiento específicos del deporte\n"
                    elif program_type == "LONGEVITY":
                        program_context += "\nConsideraciones especiales para LONGEVITY:\n"
                        program_context += "- Enfoque en técnica segura para salud articular a largo plazo\n"
                        program_context += "- Análisis de patrones compensatorios relacionados con la edad\n"
                        program_context += "- Consideraciones para condiciones crónicas y limitaciones existentes\n"
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
                program_type = "GENERAL"
                program_context = ""
            
            # Utilizar las capacidades de visión del agente
            with self.agent.tracer.start_as_current_span("movement_analysis"):
                # Determinar si usar video o secuencia de imágenes
                if video_data:
                    # Analizar video (simulado por ahora, en un caso real se extraerían frames clave)
                    # En una implementación completa, se procesaría el video para extraer frames clave
                    logger.info("Analizando video para movimiento")
                    frames = ["frame_simulado"]  # Simulación
                else:
                    # Usar secuencia de imágenes
                    frames = image_sequence
                
                if not frames:
                    raise ValueError("No se proporcionaron datos de video ni secuencia de imágenes para el análisis")
                
                # Analizar el primer frame/imagen como ejemplo
                # En una implementación completa, se analizarían todos los frames clave
                sample_image = frames[0]
                vision_analysis = await self.agent.vision_processor.analyze_image(sample_image)
                
                # Extraer análisis de movimiento usando el modelo multimodal
                prompt = f"""
                Eres un experto en biomecánica y análisis de movimiento. Analiza esta imagen/video
                de un usuario con programa tipo {program_type} realizando un {movement_type} y proporciona
                un análisis detallado de su técnica y patrón de movimiento.
                
                {program_context}
                
                Proporciona:
                1. Un resumen general del patrón de movimiento observado
                2. Análisis detallado de la técnica en cada fase del movimiento
                3. Problemas técnicos identificados
                4. Posibles implicaciones para el rendimiento y riesgo de lesión
                5. Recomendaciones específicas para mejorar la técnica
                
                Sé objetivo, detallado y proporciona feedback constructivo basado en lo que observas.
                """
                
                multimodal_result = await self.agent.multimodal_adapter.analyze_image(
                    image_data=sample_image,
                    analysis_prompt=prompt,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer evaluación del movimiento estructurada
                assessment_prompt = f"""
                Basándote en el siguiente análisis de movimiento para un {movement_type}, extrae una evaluación estructurada
                en formato JSON con los siguientes campos:
                1. movement_phases: fases del movimiento y evaluación de cada una
                2. joint_positions: posiciones articulares clave
                3. weight_distribution: distribución del peso
                4. movement_efficiency: eficiencia del movimiento
                5. stability_control: estabilidad y control
                6. overall_technique: evaluación general de la técnica
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                assessment_response = await self.agent.gemini_client.generate_structured_output(assessment_prompt)
                
                # Procesar evaluación del movimiento
                if not isinstance(assessment_response, dict):
                    try:
                        assessment_response = json.loads(assessment_response)
                    except:
                        assessment_response = {
                            "movement_phases": {"preparación": "No determinado", "ejecución": "No determinado", "finalización": "No determinado"},
                            "joint_positions": "No determinado",
                            "weight_distribution": "No determinado",
                            "movement_efficiency": "No determinado",
                            "stability_control": "No determinado",
                            "overall_technique": "No se pudo determinar con precisión"
                        }
                
                # Extraer problemas técnicos
                issues_prompt = f"""
                Basándote en el siguiente análisis de movimiento para un {movement_type}, extrae los problemas técnicos
                en formato JSON array, donde cada elemento es un objeto con:
                1. issue: descripción del problema
                2. phase: fase del movimiento donde ocurre
                3. severity: severidad (leve, moderada, significativa)
                4. implications: implicaciones para el rendimiento y riesgo de lesión
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                issues_response = await self.agent.gemini_client.generate_structured_output(issues_prompt)
                
                # Procesar problemas técnicos
                if not isinstance(issues_response, list):
                    try:
                        issues_response = json.loads(issues_response)
                        if not isinstance(issues_response, list):
                            issues_response = []
                    except:
                        issues_response = []
                
                # Si no hay problemas técnicos, crear algunos genéricos
                if not issues_response:
                    issues_response = [
                        {
                            "issue": "No se pudieron determinar problemas específicos",
                            "phase": "General",
                            "severity": "indeterminada",
                            "implications": "Indeterminadas"
                        }
                    ]
                
                # Extraer recomendaciones
                recommendations_prompt = f"""
                Basándote en el siguiente análisis de movimiento para un {movement_type}, genera 3-5 recomendaciones específicas
                para mejorar la técnica. Considera el contexto del programa {program_type}.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve las recomendaciones como una lista de strings.
                """
                
                recommendations_response = await self.agent.gemini_client.generate_structured_output(recommendations_prompt)
                
                # Procesar recomendaciones
                if not isinstance(recommendations_response, list):
                    try:
                        recommendations_response = json.loads(recommendations_response)
                        if not isinstance(recommendations_response, list):
                            recommendations_response = []
                    except:
                        recommendations_response = []
                
                # Si no hay recomendaciones, crear algunas genéricas
                if not recommendations_response:
                    recommendations_response = [
                        f"Practicar el {movement_type} con peso reducido para perfeccionar la técnica",
                        "Incorporar ejercicios de movilidad para las articulaciones limitantes",
                        "Trabajar en la estabilidad central para mejorar el control durante el movimiento",
                        "Considerar una evaluación técnica con un profesional para recomendaciones más específicas"
                    ]
                
                # Generar ejercicios correctivos
                exercises_prompt = f"""
                Basándote en el siguiente análisis de movimiento para un {movement_type}, genera 3-5 ejercicios correctivos
                en formato JSON array, donde cada ejercicio es un objeto con:
                - name: nombre del ejercicio
                - target_issue: problema que aborda
                - description: descripción breve
                - sets: número de series
                - reps: número de repeticiones
                - frequency: frecuencia recomendada
                - notes: notas adicionales (opcional)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve SOLO el JSON array, sin explicaciones adicionales.
                """
                
                exercises_response = await self.agent.gemini_client.generate_structured_output(exercises_prompt)
                
                # Procesar ejercicios correctivos
                if not isinstance(exercises_response, list):
                    try:
                        exercises_response = json.loads(exercises_response)
                        if not isinstance(exercises_response, list):
                            exercises_response = []
                    except:
                        exercises_response = []
                
                # Extraer resumen del movimiento
                movement_summary = multimodal_result.get("text", "").split("\n\n")[0] if multimodal_result.get("text") else f"No se pudo generar un resumen del {movement_type}."
                
                # Crear la salida de la skill
                analysis_id = f"movement_{user_id}_{uuid.uuid4().hex[:8]}"
                return MovementAnalysisOutput(
                    analysis_id=analysis_id,
                    movement_summary=movement_summary,
                    movement_assessment=assessment_response,
                    technique_issues=issues_response,
                    recommendations=recommendations_response,
                    corrective_exercises=exercises_response
                )
                
        except Exception as e:
            logger.error(f"Error al analizar movimiento: {e}", exc_info=True)
            
            # En caso de error, devolver un análisis básico
            return MovementAnalysisOutput(
                analysis_id=f"movement_{user_id}_{uuid.uuid4().hex[:8]}",
                movement_summary=f"No se pudo realizar el análisis del {movement_type} debido a un error en el procesamiento.",
                movement_assessment={
                    "movement_phases": {"preparación": "No determinado", "ejecución": "No determinado", "finalización": "No determinado"},
                    "joint_positions": "No determinado",
                    "weight_distribution": "No determinado",
                    "movement_efficiency": "No determinado",
                    "stability_control": "No determinado",
                    "overall_technique": "Error en el procesamiento"
                },
                technique_issues=[
                    {
                        "issue": "No se pudieron determinar problemas específicos debido a un error",
                        "phase": "General",
                        "severity": "indeterminada",
                        "implications": "Indeterminadas"
                    }
                ],
                recommendations=[
                    "Intente nuevamente con un video o imágenes de mejor calidad.",
                    f"Considere consultar a un profesional para una evaluación del {movement_type} en persona."
                ],
                corrective_exercises=None
            )
    
    async def _generate_mock_movement_analysis(self, input_data: MovementAnalysisInput) -> MovementAnalysisOutput:
        """Genera un análisis de movimiento simulado cuando las capacidades de visión no están disponibles."""
        logger.info("Generando análisis de movimiento simulado")
        
        user_id = input_data.user_id or "usuario_anónimo"
        movement_type = input_data.movement_type
        
        # Generar un ID de análisis
        analysis_id = f"movement_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Generar evaluación de movimiento simulada
        movement_assessment = {
            "movement_phases": {
                "preparación": "Posición inicial con algunas desviaciones",
                "ejecución": "Patrón de movimiento con compensaciones leves",
                "finalización": "Retorno a posición con control moderado"
            },
            "joint_positions": "Desviaciones leves en alineación de rodillas y caderas",
            "weight_distribution": "Ligeramente desplazado hacia adelante",
            "movement_efficiency": "Moderada, con pérdidas de energía en transiciones",
            "stability_control": "Control central moderado con oscilaciones leves",
            "overall_technique": "Técnica con aspectos positivos y áreas de mejora identificables"
        }
        
        # Generar problemas técnicos simulados
        technique_issues = [
            {
                "issue": "Desplazamiento anterior del peso",
                "phase": "Ejecución",
                "severity": "moderada",
                "implications": "Reduce eficiencia y aumenta estrés en rodillas"
            },
            {
                "issue": "Rotación interna de rodillas",
                "phase": "Ejecución",
                "severity": "leve",
                "implications": "Puede aumentar estrés en ligamentos y tendones de rodilla"
            },
            {
                "issue": "Pérdida de tensión en cadena posterior",
                "phase": "Finalización",
                "severity": "leve",
                "implications": "Reduce estabilidad y control en fase final"
            }
        ]
        
        # Generar recomendaciones simuladas
        recommendations = [
            f"Practicar el {movement_type} con peso reducido enfocándose en mantener el peso centrado",
            "Incorporar ejercicios de conciencia propioceptiva para mejorar alineación de rodillas",
            "Trabajar en la activación y control de cadena posterior",
            "Utilizar feedback visual (espejo o video) para monitorizar técnica",
            "Considerar una evaluación técnica con un profesional para recomendaciones más específicas"
        ]
        
        # Generar ejercicios correctivos simulados
        corrective_exercises = [
            {
                "name": "Sentadilla con banda",
                "target_issue": "Rotación interna de rodillas",
                "description": "Sentadilla con banda elástica alrededor de rodillas para resistir rotación interna",
                "sets": 3,
                "reps": "10-12",
                "frequency": "3 veces por semana",
                "notes": "Enfocarse en empujar rodillas hacia afuera contra la banda"
            },
            {
                "name": "Puente de glúteos con elevación de pierna",
                "target_issue": "Activación de cadena posterior",
                "description": "Puente de glúteos con elevación alternada de piernas manteniendo pelvis estable",
                "sets": 3,
                "reps": "8-10 por lado",
                "frequency": "3-4 veces por semana",
                "notes": "Mantener core activado durante todo el movimiento"
            },
            {
                "name": "Bisagra de cadera con palo",
                "target_issue": "Control de cadena posterior",
                "description": "Bisagra de cadera con palo en contacto con cabeza, espalda y sacro",
                "sets": 3,
                "reps": "10-12",
                "frequency": "Diario",
                "notes": "Mantener los tres puntos de contacto durante todo el movimiento"
            }
        ]
        
        # Generar resumen simulado
        movement_summary = (
            f"Análisis simulado de {movement_type} para el usuario {user_id}. "
            "Se observa un patrón de movimiento con eficiencia moderada y algunas compensaciones. "
            "Las principales observaciones incluyen desplazamiento anterior del peso, "
            "rotación interna leve de rodillas y pérdida parcial de tensión en cadena posterior. "
            "Estos patrones pueden reducir la eficiencia del movimiento y potencialmente aumentar el riesgo de lesión. "
            "Este es un análisis simulado debido a que las capacidades de visión no están disponibles."
        )
        
        return MovementAnalysisOutput(
            analysis_id=analysis_id,
            movement_summary=movement_summary,
            movement_assessment=movement_assessment,
            technique_issues=technique_issues,
            recommendations=recommendations,
            corrective_exercises=corrective_exercises
        )

# Definir la clase principal del agente RecoveryCorrective
class RecoveryCorrective(ADKAgent):
    """
    Agente especializado en recuperación, rehabilitación y corrección de problemas físicos.
    
    Este agente proporciona estrategias personalizadas para la prevención y rehabilitación de lesiones,
    optimización del sueño, manejo del dolor, evaluación de movilidad y protocolos basados en HRV.
    """
    
    def __init__(
        self,
        agent_id: str = None,
        gemini_client: GeminiClient = None,
        supabase_client: SupabaseClient = None,
        mcp_toolkit: MCPToolkit = None,
        state_manager: StateManager = None,
        **kwargs
    ):
        """Inicializa el agente RecoveryCorrective con sus dependencias"""
        
        # Generar ID único si no se proporciona
        if agent_id is None:
            agent_id = f"recovery_corrective_{uuid.uuid4().hex[:8]}"
        
        # Crear tarjeta de agente
        agent_card = AgentCard(
            name="RecoveryCorrective",
            description="Especialista en recuperación, rehabilitación y corrección de problemas físicos",
            instructions="""
            Soy un agente especializado en recuperación, rehabilitación y corrección de problemas físicos.
            
            Puedo ayudarte con:
            - Prevención de lesiones
            - Protocolos de rehabilitación
            - Evaluación y mejora de movilidad
            - Optimización del sueño
            - Interpretación de datos de HRV
            - Manejo del dolor crónico
            - Estrategias generales de recuperación
            
            Proporciono información basada en evidencia y estrategias personalizadas para mejorar
            tu recuperación, movilidad y bienestar general.
            """,
            examples=[
                Example(
                    input="¿Cómo puedo prevenir lesiones al correr?",
                    output="Aquí tienes un plan de prevención de lesiones para corredores..."
                ),
                Example(
                    input="Tengo dolor en la rodilla después de entrenar, ¿qué puedo hacer?",
                    output="Basado en tu descripción, aquí hay un protocolo de rehabilitación..."
                ),
                Example(
                    input="¿Cómo puedo mejorar mi movilidad de cadera?",
                    output="Te proporcionaré una evaluación de movilidad y ejercicios específicos..."
                ),
                Example(
                    input="¿Cómo puedo optimizar mi sueño para recuperarme mejor?",
                    output="Aquí tienes un plan de optimización del sueño personalizado..."
                ),
                Example(
                    input="¿Qué significan mis datos de HRV y cómo usarlos?",
                    output="Te explicaré cómo interpretar tus datos de HRV y cómo aplicarlos..."
                )
            ]
        )
        
        # Crear toolkit con las skills del agente
        toolkit = Toolkit(
            skills=[
                InjuryPreventionSkill(),
                RehabilitationSkill(),
                MobilityAssessmentSkill(),
                SleepOptimizationSkill(),
                HRVProtocolSkill(),
                ChronicPainSkill(),
                GeneralRecoverySkill(),
                PostureAnalysisSkill(),
                MovementAnalysisSkill()
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
            state_manager=state_manager,
            **kwargs
        )
        
        # Inicializar el servicio de clasificación de programas
        self.gemini_client = gemini_client or GeminiClient()
        # Configurar caché para el servicio de clasificación de programas
        use_redis = os.environ.get('USE_REDIS_CACHE', 'false').lower() == 'true'
        cache_ttl = int(os.environ.get('PROGRAM_CACHE_TTL', '3600'))  # 1 hora por defecto
        self.program_classification_service = ProgramClassificationService(
            gemini_client=self.gemini_client,
            use_cache=True  # Habilitar caché para mejorar rendimiento
        )
        
        # Inicializar componentes de visión y multimodales
        try:
            from infrastructure.adapters.vision_adapter import VisionProcessor
            from infrastructure.adapters.multimodal_adapter import MultimodalAdapter
            
            # Inicializar procesador de visión
            self.vision_processor = VisionProcessor(
                gemini_client=self.gemini_client
            )
            
            # Inicializar adaptador multimodal
            self.multimodal_adapter = MultimodalAdapter(
                gemini_client=self.gemini_client
            )
            
            # Establecer bandera de disponibilidad de capacidades de visión
            self._vision_capabilities_available = True
            logger.info("Capacidades de visión y multimodales inicializadas correctamente")
        except Exception as e:
            logger.warning(f"No se pudieron inicializar las capacidades de visión y multimodales: {e}")
            self._vision_capabilities_available = False
        
        logger.info(f"Agente RecoveryCorrective inicializado con ID: {agent_id}")
    
    async def process_message(self, message: str, session_id: str = None, **kwargs) -> str:
        """
        Procesa un mensaje del usuario y genera una respuesta utilizando las skills apropiadas.
        
        Args:
            message: Mensaje del usuario
            session_id: ID de la sesión de chat
            **kwargs: Argumentos adicionales
            
        Returns:
            Respuesta generada para el usuario
        """
        logger.info(f"Procesando mensaje para RecoveryCorrective, session_id: {session_id}")
        
        # Analizar la intención del mensaje para determinar qué skill utilizar
        intent_prompt = f"""
        Analiza el siguiente mensaje del usuario y determina qué categoría de consulta es:
        
        Mensaje: "{message}"
        
        Categorías:
        - injury_prevention: Prevención de lesiones
        - rehabilitation: Rehabilitación de lesiones
        - mobility_assessment: Evaluación y mejora de movilidad
        - sleep_optimization: Optimización del sueño
        - hrv_protocols: Protocolos basados en HRV
        - chronic_pain_management: Manejo del dolor crónico
        - general_recovery: Consulta general sobre recuperación
        
        Devuelve SOLO el nombre de la categoría más relevante, sin explicaciones adicionales.
        """
        
        # Determinar la intención utilizando el cliente Gemini
        intent = await self.gemini_client.generate_response(intent_prompt, temperature=0.1)
        intent = intent.strip().lower()
        
        # Mapear la intención a la skill correspondiente
        skill_mapping = {
            "injury_prevention": "injury_prevention",
            "rehabilitation": "rehabilitation",
            "mobility_assessment": "mobility_assessment",
            "mobility": "mobility_assessment",
            "sleep_optimization": "sleep_optimization",
            "sleep": "sleep_optimization",
            "hrv_protocols": "hrv_protocols",
            "hrv": "hrv_protocols",
            "chronic_pain_management": "chronic_pain_management",
            "pain": "chronic_pain_management",
            "general_recovery": "general_recovery"
        }
        
        # Obtener el nombre de la skill a utilizar
        skill_name = skill_mapping.get(intent, "general_recovery")
        
        logger.info(f"Intención detectada: {intent}, usando skill: {skill_name}")
        
        # Preparar los datos de entrada para la skill
        if skill_name == "injury_prevention":
            # Extraer información relevante para prevención de lesiones
            activity_prompt = f"""
            Extrae el tipo de actividad física mencionada en el mensaje del usuario:
            "{message}"
            
            Devuelve SOLO el nombre de la actividad, o null si no se menciona ninguna actividad específica.
            """
            activity_type = await self.gemini_client.generate_response(activity_prompt, temperature=0.1)
            activity_type = None if activity_type.lower() in ["null", "none", ""] else activity_type
            
            input_data = InjuryPreventionInput(
                query=message,
                activity_type=activity_type
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill(skill_name, input_data)
            return result.response
            
        elif skill_name == "rehabilitation":
            # Extraer información relevante para rehabilitación
            injury_prompt = f"""
            Extrae el tipo de lesión y la fase de la lesión (aguda, subaguda, crónica) mencionada en el mensaje del usuario:
            "{message}"
            
            Devuelve un JSON con dos campos:
            - injury_type: tipo de lesión, o null si no se menciona
            - injury_phase: fase de la lesión, o null si no se menciona
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """
            injury_info = await self.gemini_client.generate_structured_output(injury_prompt)
            
            if isinstance(injury_info, str):
                try:
                    injury_info = json.loads(injury_info)
                except:
                    injury_info = {"injury_type": None, "injury_phase": None}
            
            if not isinstance(injury_info, dict):
                injury_info = {"injury_type": None, "injury_phase": None}
            
            input_data = RehabilitationInput(
                query=message,
                injury_type=injury_info.get("injury_type"),
                injury_phase=injury_info.get("injury_phase")
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill(skill_name, input_data)
            return result.response
            
        elif skill_name == "mobility_assessment":
            # Extraer información relevante para evaluación de movilidad
            mobility_prompt = f"""
            Extrae las áreas objetivo para mejorar movilidad mencionadas en el mensaje del usuario:
            "{message}"
            
            Devuelve un JSON array con las áreas mencionadas, o un array vacío si no se mencionan áreas específicas.
            
            Devuelve SOLO el JSON array, sin explicaciones adicionales.
            """
            target_areas = await self.gemini_client.generate_structured_output(mobility_prompt)
            
            if isinstance(target_areas, str):
                try:
                    target_areas = json.loads(target_areas)
                except:
                    target_areas = []
            
            if not isinstance(target_areas, list):
                target_areas = []
            
            input_data = MobilityAssessmentInput(
                query=message,
                target_areas=target_areas
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill(skill_name, input_data)
            return result.response
            
        elif skill_name == "sleep_optimization":
            # Extraer información relevante para optimización del sueño
            sleep_prompt = f"""
            Extrae los problemas de sueño mencionados en el mensaje del usuario:
            "{message}"
            
            Devuelve un JSON array con los problemas mencionados, o un array vacío si no se mencionan problemas específicos.
            
            Devuelve SOLO el JSON array, sin explicaciones adicionales.
            """
            sleep_issues = await self.gemini_client.generate_structured_output(sleep_prompt)
            
            if isinstance(sleep_issues, str):
                try:
                    sleep_issues = json.loads(sleep_issues)
                except:
                    sleep_issues = []
            
            if not isinstance(sleep_issues, list):
                sleep_issues = []
            
            input_data = SleepOptimizationInput(
                query=message,
                sleep_issues=sleep_issues
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill(skill_name, input_data)
            return result.response
            
        elif skill_name == "hrv_protocols":
            # Ejecutar directamente la skill de HRV
            input_data = HRVProtocolInput(
                query=message
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill(skill_name, input_data)
            return result.response
            
        elif skill_name == "chronic_pain_management":
            # Extraer información relevante para manejo del dolor
            pain_prompt = f"""
            Extrae información sobre el dolor mencionado en el mensaje del usuario:
            "{message}"
            
            Devuelve un JSON con tres campos:
            - location: ubicación del dolor, o null si no se menciona
            - intensity: intensidad del dolor (1-10), o null si no se menciona
            - duration: duración del dolor, o null si no se menciona
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """
            pain_info = await self.gemini_client.generate_structured_output(pain_prompt)
            
            if isinstance(pain_info, str):
                try:
                    pain_info = json.loads(pain_info)
                except:
                    pain_info = {"location": None, "intensity": None, "duration": None}
            
            if not isinstance(pain_info, dict):
                pain_info = {"location": None, "intensity": None, "duration": None}
            
            # Convertir intensidad a entero si es posible
            intensity = pain_info.get("intensity")
            if isinstance(intensity, str) and intensity.isdigit():
                intensity = int(intensity)
            elif not isinstance(intensity, int):
                intensity = None
            
            input_data = ChronicPainInput(
                query=message,
                pain_location=pain_info.get("location"),
                pain_intensity=intensity,
                pain_duration=pain_info.get("duration")
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill(skill_name, input_data)
            return result.response
            
        else:  # general_recovery
            # Ejecutar la skill general
            input_data = GeneralRecoveryInput(
                query=message
            )
            
            # Ejecutar la skill
            result = await self.toolkit.run_skill("general_recovery", input_data)
            return result.response
