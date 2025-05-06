"""
Agente especializado en diseñar y periodizar programas de entrenamiento 
para atletas de alto rendimiento.

Este agente utiliza el modelo Gemini para generar planes de entrenamiento
personalizados basados en los objetivos, nivel y restricciones del atleta.
Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
"""
import uuid
from typing import Dict, Any, Optional, List
import time
from datetime import datetime, timezone
import re
import os

# from google.adk.agents import Agent # No longer needed here, imported in base
from agents.base.adk_agent import ADKAgent
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from core.state_manager import StateManager
from core.logging_config import get_logger
from google.cloud import aiplatform

# Configurar OpenTelemetry para observabilidad
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    
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
    
    error_count = meter.create_counter(
        name="agent_errors",
        description="Número de errores en el agente",
        unit="1"
    )
    
    has_telemetry = True
except ImportError:
    # Fallback si OpenTelemetry no está disponible
    has_telemetry = False
    tracer = None
    request_counter = None
    response_time = None
    error_count = None

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

    # Declarar campos para Pydantic/ADK
    gemini_client: Optional[GeminiClient] = None
    supabase_client: Optional[SupabaseClient] = None
    tracer: Optional[trace.Tracer] = None
    request_counter: Optional[metrics.Counter] = None
    response_time: Optional[metrics.Histogram] = None
    error_count: Optional[metrics.Counter] = None

    # Ajustar constructor
    def __init__(self, 
                 # Eliminar toolkit: Optional[Agent] = None, 
                 # Eliminar a2a_server_url: Optional[str] = None, 
                 state_manager: Optional[StateManager] = None,
                 model: str = "gemini-1.5-flash", # Añadir parámetro model
                 instruction: str = "Eres un estratega experto en entrenamiento deportivo.", # Añadir instrucción
                 **kwargs):
        """
        Inicializa el agente EliteTrainingStrategist usando la base ADKAgent refactorizada.
        """
        agent_id = "elite_training_strategist"
        name = "NGX_Elite_Training_Strategist" # Cambiado para ser un identificador válido
        description = "Diseña y periodiza programas de entrenamiento de élite personalizados."
        # capabilities = [...] # Ya no se pasa a la base
        # version = "1.1.0" # Ya no se pasa a la base

        # Definir Skills para Agent Card (ADK)
        # agent_skills_definition = [...] # Ya no se usa esta definición para la base

        # Crear lista de 'tools' (referencias a métodos)
        # Asumiendo que los métodos _skill_... existen más adelante
        agent_tools = []
        if hasattr(self, '_skill_generate_training_plan'):
            agent_tools.append(self._skill_generate_training_plan)
        if hasattr(self, '_skill_analyze_performance'):
            agent_tools.append(self._skill_analyze_performance)
        if hasattr(self, '_skill_design_periodization'):
            agent_tools.append(self._skill_design_periodization)
        if hasattr(self, '_skill_prescribe_exercises'):
            agent_tools.append(self._skill_prescribe_exercises)
        # Añadir más skills aquí si existen

        # Eliminar claves conflictivas de kwargs antes de llamar a super
        kwargs.pop('agent_id', None) # Elimina la clave si existe, ignora si no
        kwargs.pop('name', None)
        kwargs.pop('description', None)

        # Llamar al constructor de ADKAgent refactorizado
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            # capabilities=capabilities, # Eliminado
            # toolkit=toolkit, # Eliminado
            # version=version, # Eliminado
            # a2a_server_url=a2a_server_url, # Eliminado
            state_manager=state_manager,
            # skills=agent_skills_definition, # Eliminado (se pasan 'tools')
            model=model, # Pasar model
            instruction=instruction, # Pasar instruction
            tools=agent_tools, # Pasar la lista de métodos
            **kwargs
        )

        # Inicializar clientes
        try:
            self.gemini_client = GeminiClient()
            logger.info("GeminiClient inicializado.")
        except Exception as e:
            logger.error(f"Error al inicializar GeminiClient: {e}", exc_info=True)
            # self.gemini_client ya es None por la declaración de clase

        try:
            # Asumiendo que SupabaseClient puede necesitar URL y Key
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            if supabase_url and supabase_key:
                self.supabase_client = SupabaseClient(supabase_url, supabase_key)
                logger.info("SupabaseClient inicializado.")
            else:
                 logger.warning("SUPABASE_URL o SUPABASE_KEY no configuradas. SupabaseClient no inicializado.")
                 self.supabase_client = None
        except Exception as e:
            logger.error(f"Error al inicializar SupabaseClient: {e}", exc_info=True)
            # self.supabase_client ya es None por la declaración de clase

        # Inicializar telemetría
        self.tracer = tracer
        self.request_counter = request_counter
        self.response_time = response_time
        self.error_count = error_count

        logger.info(f"EliteTrainingStrategist inicializado ({len(agent_tools)} tools) con protocolo ADK.")

    # --- Métodos de Skill --- 
    # (Mover lógica de _generate_training_plan, _analyze_performance, etc., aquí)

    async def _skill_generate_training_plan(self, user_id: str, goals: List[str], weeks: int, constraints: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Skill para generar un plan de entrenamiento."""
        start_time = time.time()
        logger.info(f"Executing _skill_generate_training_plan for user_id={user_id}")
        
        # Obtener contexto (incluye perfil)
        session_id = kwargs.get("session_id") # Asumiendo que session_id puede venir en kwargs
        context = await self._get_context(user_id, session_id)
        client_profile = context.get("client_profile", {}) 
        program_type = self._get_program_type_from_profile(client_profile) # Determinar tipo de programa
        
        if not self.gemini_client:
             logger.error("GeminiClient no está disponible para generar plan.")
             return {"response": "Error: Servicio de IA no disponible.", "artifacts": []}

        # Construir el prompt para Gemini
        profile_details = self._extract_profile_details(client_profile)
        goal_str = ", ".join(goals)
        constraints_str = f" Restricciones adicionales: {constraints}." if constraints else ""

        # Adaptar el prompt según el tipo de programa
        if program_type == "PRIME":
            prompt_base = f"Eres un entrenador experto en atletas PRIME (alto rendimiento). Diseña un plan de entrenamiento detallado de {weeks} semanas para un atleta con el siguiente perfil:\n{profile_details}\nObjetivos: {goal_str}.{constraints_str}\nEl plan debe incluir fases (ej. base, construcción, pico, descarga), tipos de sesiones (fuerza, resistencia, técnica, recuperación), intensidad (zonas, RPE) y volumen (duración/distancia). Formato: Markdown."
        elif program_type == "LONGEVITY":
            prompt_base = f"Eres un entrenador experto en atletas LONGEVITY (salud y bienestar). Diseña un plan de entrenamiento sostenible de {weeks} semanas para una persona con el siguiente perfil:\n{profile_details}\nObjetivos: {goal_str}.{constraints_str}\nEnfócate en movilidad, fuerza funcional, capacidad cardiovascular moderada y recuperación activa. El plan debe ser adaptable y promover la consistencia. Formato: Markdown."
        else: # General/Unknown
             prompt_base = f"Diseña un plan de entrenamiento general de {weeks} semanas para una persona con el siguiente perfil:\n{profile_details}\nObjetivos: {goal_str}.{constraints_str}\nAsegúrate de que sea equilibrado y seguro. Formato: Markdown."

        # Incluir historial relevante si existe (últimas 2 interacciones)
        history_str = "\nHistorial reciente:\n"
        if context.get("history"):
             for entry in context["history"][-2:]:
                 # Formatear historial (puede necesitar ajuste)
                 input_text = entry.get('input', {}).get('text', 'N/A')
                 output_text = entry.get('output', {}).get('response', 'N/A')
                 skill_used = entry.get('skill_used', 'N/A')
                 history_str += f"- Skill: {skill_used}, In: '{input_text[:50]}...', Out: '{output_text[:50]}...'\n"
        else:
             history_str = ""

        full_prompt = prompt_base + history_str
        logger.debug(f"Prompt para Gemini (generate_training_plan): {full_prompt[:200]}...")

        try:
            # Llamar a Gemini
            response = await self.gemini_client.generate_content(full_prompt)
            training_plan_text = response if isinstance(response, str) else str(response) # Asegurar que sea string
            
            # Crear artefactos (si aplica)
            artifacts = [
                {
                    "type": "markdown",
                    "label": f"Plan de Entrenamiento ({program_type}) - {weeks} Semanas",
                    "content": training_plan_text
                }
            ]
            result = {"response": training_plan_text, "artifacts": artifacts}

        except Exception as e:
            logger.error(f"Error al generar plan de entrenamiento con Gemini para user_id {user_id}: {e}", exc_info=True)
            result = {"response": "Error: No se pudo generar el plan de entrenamiento.", "artifacts": []}

        # Actualizar contexto con esta interacción
        interaction_data = {
            "skill_used": "generate_training_plan",
            "input": {"user_id": user_id, "goals": goals, "weeks": weeks, "constraints": constraints},
            "output": result,
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        await self._update_context(user_id, session_id, interaction_data)

        return result

    async def _skill_analyze_performance(self, user_id: str, performance_data: Dict[str, Any], time_period: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Skill para analizar rendimiento."""
        start_time = time.time()
        logger.info(f"Executing _skill_analyze_performance for user_id={user_id}")
        session_id = kwargs.get("session_id")
        
        # 1. Obtener contexto y perfil
        context = await self._get_context(user_id, session_id)
        client_profile = context.get("client_profile", {})
        program_type = self._get_program_type_from_profile(client_profile)
        profile_details = self._extract_profile_details(client_profile)

        if not self.gemini_client:
             logger.error("GeminiClient no está disponible para analizar rendimiento.")
             return {"response": "Error: Servicio de IA no disponible.", "artifacts": []}

        # 2. Construir el prompt para Gemini
        performance_data_str = "\n".join([f"- {k}: {v}" for k, v in performance_data.items()])
        time_period_str = f" para el período: {time_period}" if time_period else ""

        prompt = f"""
        Actúa como un especialista en análisis de rendimiento deportivo.
        Analiza los siguientes datos de rendimiento{time_period_str}:
        {performance_data_str}

        Contexto del Atleta:
        Programa: {program_type}
        Perfil:
        {profile_details}

        Instrucciones:
        - Identifica tendencias clave (positivas y negativas).
        - Compara el rendimiento con los objetivos del atleta (si se conocen del perfil).
        - Proporciona insights accionables y recomendaciones para ajustar el entrenamiento.
        - Considera el tipo de programa ({program_type}) al hacer recomendaciones.
        - Si es PRIME, enfócate en optimización marginal y picos de forma.
        - Si es LONGEVITY, enfócate en sostenibilidad, prevención y disfrute.
        - Formato: Markdown claro, con secciones para Tendencias, Comparación con Objetivos, y Recomendaciones.
        """
        
        # Añadir historial relevante
        history_str = "\nHistorial reciente:\n"
        if context.get("history"):
             for entry in context["history"][-2:]:
                 input_text = entry.get('input', {}).get('text', 'N/A')
                 output_text = entry.get('output', {}).get('response', 'N/A')
                 skill_used = entry.get('skill_used', 'N/A')
                 history_str += f"- Skill: {skill_used}, In: '{input_text[:50]}...', Out: '{output_text[:50]}...'\n"
        else:
             history_str = ""

        full_prompt = prompt + history_str
        logger.debug(f"Prompt para Gemini (analyze_performance): {full_prompt[:200]}...")

        # 3. Llamar a Gemini y procesar respuesta
        try:
            analysis_result_text = await self.gemini_client.generate_content(full_prompt)
            analysis_result_text = analysis_result_text if isinstance(analysis_result_text, str) else str(analysis_result_text)
            
            # Crear artefactos (ej. resumen del análisis)
            artifacts = [
                {
                    "type": "markdown",
                    "label": f"Análisis de Rendimiento ({program_type}){f' - {time_period}' if time_period else ''}",
                    "content": analysis_result_text
                }
            ]
            result = {"response": analysis_result_text, "artifacts": artifacts}

        except Exception as e:
            logger.error(f"Error al generar análisis de rendimiento con Gemini para user_id {user_id}: {e}", exc_info=True)
            error_message = "Error al generar el análisis de rendimiento. Por favor, intenta de nuevo más tarde."
            result = {"response": error_message, "artifacts": []}

        # 4. Actualizar contexto
        interaction_data = {
            "skill_used": "analyze_performance",
            "input": {"user_id": user_id, "performance_data": performance_data, "time_period": time_period},
            "output": result,
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        await self._update_context(user_id, session_id, interaction_data)
        
        return result

    async def _skill_design_periodization(self, user_id: str, goal_event: str, total_duration_months: int, **kwargs) -> Dict[str, Any]:
        """Skill para diseñar periodización."""
        start_time = time.time()
        logger.info(f"Executing _skill_design_periodization for user_id={user_id}, goal='{goal_event}', duration={total_duration_months} months")
        session_id = kwargs.get("session_id")

        # 1. Obtener contexto y perfil
        context = await self._get_context(user_id, session_id)
        client_profile = context.get("client_profile", {})
        program_type = self._get_program_type_from_profile(client_profile)
        profile_details = self._extract_profile_details(client_profile)

        if not self.gemini_client:
            logger.error("GeminiClient no está disponible para diseñar periodización.")
            return {"response": "Error: Servicio de IA no disponible.", "artifacts": []}

        # 2. Construir el prompt para Gemini
        # total_duration_months ya es un argumento, no se necesita regex.
        total_duration_weeks = total_duration_months * 4 # Aproximación

        prompt = f"""
        Actúa como un diseñador experto de programas de entrenamiento y periodización.
        Diseña un plan de periodización detallado de aproximadamente {total_duration_weeks} semanas ({total_duration_months} meses) para alcanzar el siguiente objetivo/evento:
        '{goal_event}'

        Contexto del Atleta:
        Programa: {program_type}
        Perfil:
        {profile_details}

        Instrucciones:
        - Estructura el plan en fases claras (ej. Base, Construcción, Pico, Transición).
        - Define objetivos específicos para cada fase.
        - Sugiere tipos de entrenamiento y enfoques para cada fase (ej. volumen vs. intensidad).
        - Considera el tipo de programa ({program_type}) al diseñar la estructura:
            - PRIME: Periodización más agresiva, picos definidos, recuperación planificada.
            - LONGEVITY: Ondulaciones más suaves, énfasis en recuperación activa, flexibilidad.
            - GENERAL/UNKNOWN/ERROR: Un modelo de periodización clásico y seguro.
        - Formato: Markdown claro, con secciones por Fase, indicando duración, objetivos y enfoque.
        """
        
        # Añadir historial relevante
        history_str = "\nHistorial reciente:\n"
        if context.get("history"):
             for entry in context["history"][-2:]:
                 input_text = entry.get('input', {}).get('text', 'N/A')
                 output_text = entry.get('output', {}).get('response', 'N/A')
                 skill_used = entry.get('skill_used', 'N/A')
                 history_str += f"- Skill: {skill_used}, In: '{input_text[:50]}...', Out: '{output_text[:50]}...'\n"
        else:
             history_str = ""

        full_prompt = prompt + history_str
        logger.debug(f"Prompt para Gemini (design_periodization): {full_prompt[:200]}...")

        # 3. Llamar a Gemini y procesar respuesta
        try:
            periodization_plan_text = await self.gemini_client.generate_content(full_prompt)
            periodization_plan_text = periodization_plan_text if isinstance(periodization_plan_text, str) else str(periodization_plan_text)
            
            # Crear artefactos
            artifacts = [
                {
                    "type": "markdown",
                    "label": f"Plan de Periodización ({program_type} - {total_duration_months} meses) para '{goal_event}'",
                    "content": periodization_plan_text
                }
            ]
            result = {"response": periodization_plan_text, "artifacts": artifacts}

        except Exception as e:
            logger.error(f"Error al generar periodización con Gemini para user_id {user_id}: {e}", exc_info=True)
            error_message = "Error al generar el plan de periodización. Por favor, intenta de nuevo más tarde."
            result = {"response": error_message, "artifacts": []}

        # 4. Actualizar contexto
        interaction_data = {
            "skill_used": "design_periodization",
            "input": {"user_id": user_id, "goal_event": goal_event, "total_duration_months": total_duration_months},
            "output": result,
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        await self._update_context(user_id, session_id, interaction_data)
        
        return result

    async def _skill_prescribe_exercises(self, user_id: str, session_goal: str, muscle_group: Optional[str] = None, equipment: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Skill para prescribir ejercicios."""
        start_time = time.time()
        logger.info(f"Executing _skill_prescribe_exercises for user_id={user_id}, goal='{session_goal}', muscle='{muscle_group}', equip='{equipment}'")
        session_id = kwargs.get("session_id")

        # 1. Obtener contexto y perfil
        context = await self._get_context(user_id, session_id)
        client_profile = context.get("client_profile", {})
        program_type = self._get_program_type_from_profile(client_profile)
        profile_details = self._extract_profile_details(client_profile)

        if not self.gemini_client:
            logger.error("GeminiClient no está disponible para prescribir ejercicios.")
            return {"response": "Error: Servicio de IA no disponible.", "artifacts": []}

        # 2. Construir el prompt para Gemini
        equipment_str = f"Equipo disponible: {', '.join(equipment)}." if equipment else "Equipo no especificado (asumir equipo básico/peso corporal)."
        muscle_group_str = f"Enfocado en el grupo muscular: {muscle_group}." if muscle_group else "Objetivo general de la sesión."

        prompt = f"""
        Actúa como un entrenador personal experto.
        Prescribe una lista de ejercicios específicos para una sesión de entrenamiento con el siguiente objetivo:
        '{session_goal}'

        {muscle_group_str}
        {equipment_str}

        Contexto del Atleta:
        Programa: {program_type}
        Perfil:
        {profile_details}

        Instrucciones:
        - Selecciona ejercicios apropiados para el objetivo descrito en la solicitud, el perfil del cliente y el equipo potencialmente mencionado.
        - Considera el tipo de programa ({program_type}):
            - PRIME: Ejercicios compuestos eficientes, técnicas avanzadas si aplica.
            - LONGEVITY: Ejercicios seguros, funcionales, con opciones de modificación.
            - GENERAL/UNKNOWN/ERROR: Ejercicios estándar y probados.
        - Proporciona series, repeticiones (o duración) y descansos recomendados para cada ejercicio.
        - Incluye notas breves sobre técnica o enfoque si es relevante.
        - Devuelve la lista de ejercicios EXCLUSIVAMENTE en formato JSON, como una lista de objetos. Cada objeto debe tener las claves: 'exercise_name', 'sets', 'reps_or_duration', 'rest', 'notes'.
        - NO incluyas ningún texto introductorio o explicativo antes o después del JSON.
        - Ejemplo de formato JSON esperado:
          [{{"exercise_name": "Sentadilla con barra", "sets": 3, "reps_or_duration": "8-12 reps", "rest": "60-90s", "notes": "Mantener espalda recta."}},
           {{"exercise_name": "Plancha", "sets": 3, "reps_or_duration": "30-60s", "rest": "30s", "notes": "Core apretado."}}]
        """

        # Añadir historial relevante (podría influir en la selección de ejercicios)
        history_str = "\nHistorial reciente (para contexto):\n"
        if context.get("history"):
             for entry in context["history"][-2:]:
                 input_text = entry.get('input', {}).get('text', 'N/A')
                 output_text = entry.get('output', {}).get('response', 'N/A')
                 skill_used = entry.get('skill_used', 'N/A')
                 history_str += f"- Skill: {skill_used}, In: '{input_text[:50]}...', Out: '{output_text[:50]}...'\n"
        else:
             history_str = ""
             
        # No añadir historial al prompt final si pedimos JSON estricto?
        # Depende de si Gemini puede manejar contexto + JSON estricto.
        # Por ahora, lo omitimos del prompt para maximizar la probabilidad de obtener JSON válido.
        # full_prompt = prompt # + history_str
        logger.debug(f"Prompt para Gemini (prescribe_exercises): {prompt[:200]}...") # Log prompt sin historial

        # 3. Llamar a Gemini y procesar respuesta
        response_text = ""
        exercise_list = []
        artifacts = []
        
        try:
            response_text = await self.gemini_client.generate_content(prompt)
            response_text = response_text if isinstance(response_text, str) else str(response_text)
            logger.debug(f"Respuesta cruda de Gemini (prescribe_exercises): {response_text[:200]}...")
            
            # Intentar parsear JSON
            try:
                # Limpiar posible ```json ... ``` de la respuesta
                json_match = re.search(r'```json\n(.*)\n```', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                else:
                    json_str = response_text.strip() # Asumir que es solo JSON
                
                exercise_list = json.loads(json_str)
                if isinstance(exercise_list, list):
                     logger.info(f"Ejercicios parseados exitosamente como lista JSON ({len(exercise_list)} ejercicios).")
                     # Crear artefacto con la lista estructurada
                     artifacts.append({
                         "type": "exercise_list",
                         "label": f"Ejercicios para '{session_goal}' ({program_type})",
                         "content": exercise_list
                     })
                     # Generar una respuesta textual legible desde la lista JSON
                     response_text = f"Aquí tienes una sugerencia de ejercicios para tu sesión de '{session_goal}':\n\n"
                     for ex in exercise_list:
                         response_text += f"- **{ex.get('exercise_name', 'Ejercicio desconocido')}**: {ex.get('sets', '?')} series x {ex.get('reps_or_duration', '?')} reps/duración, descanso: {ex.get('rest', '?')}. {ex.get('notes', '')}\n"
                else:
                     logger.warning("La respuesta JSON no era una lista. Se devolverá como texto.")
                     exercise_list = [] # Resetear si no es lista
                     # Usar response_text crudo como respuesta
            except json.JSONDecodeError as json_e:
                logger.warning(f"No se pudo parsear la respuesta de Gemini como JSON: {json_e}. Se devolverá como texto crudo.")
                exercise_list = [] # Asegurar que está vacía si falla el parseo
                # response_text ya contiene la respuesta cruda de Gemini

            result = {"response": response_text, "artifacts": artifacts}

        except Exception as e:
            logger.error(f"Error al prescribir ejercicios con Gemini para user_id {user_id}: {e}", exc_info=True)
            error_message = "Error al generar la prescripción de ejercicios. Por favor, intenta de nuevo más tarde."
            result = {"response": error_message, "artifacts": []}
            exercise_list = [] # Asegurar lista vacía en caso de error de Gemini

        # 4. Actualizar contexto
        interaction_data = {
            "skill_used": "prescribe_exercises",
            "input": {"user_id": user_id, "session_goal": session_goal, "muscle_group": muscle_group, "equipment": equipment},
            # Guardar la lista parseada si existe, o la respuesta textual si no.
            "output": {"response": response_text, "parsed_exercises": exercise_list, "artifacts": artifacts},
            "duration_ms": int((time.time() - start_time) * 1000)
        }
        await self._update_context(user_id, session_id, interaction_data)
        
        # Devolver la respuesta textual y los artefactos (que pueden incluir la lista parseada)
        return result

    # --- Lógica Interna Original (Ahora llamada por Skills) --- 
    # (Mantener _design_periodization, _prescribe_exercises como métodos privados 
    # llamados por los métodos _skill_*, adaptando ligeramente si es necesario)

    # --- Métodos de Contexto (Mantener y adaptar si es necesario) --- 
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """
        Obtiene contexto (perfil de usuario, historial) para la solicitud.
        Prioriza StateManager si está disponible.
        """
        context_key = f"context_{user_id}_{session_id}" if user_id and session_id else f"context_ets_default_{uuid.uuid4().hex[:6]}"
        context = {}

        # 1. Intentar cargar desde StateManager
        if self.state_manager and user_id and session_id:
            try:
                state_data = await self.state_manager.load_state(user_id, session_id)
                if state_data and isinstance(state_data.get("context"), dict):
                    context = state_data["context"]
                    logger.debug(f"Contexto cargado desde StateManager para key={context_key}")
                else:
                    logger.debug(f"No se encontró contexto válido en StateManager para key={context_key}, inicializando.")
                    context = {"history": []} # Inicializar si no hay datos o formato incorrecto
            except Exception as e:
                logger.warning(f"Error al cargar contexto desde StateManager para key={context_key}: {e}")
                context = {"history": []} # Inicializar en caso de error
        else:
             logger.debug(f"No se usa StateManager para key={context_key} (faltan IDs o no está habilitado). Inicializando contexto.")
             context = {"history": []} # Inicializar si no se usa StateManager

        # 2. Intentar obtener/actualizar perfil de Supabase si el contexto no lo tiene
        if not context.get("client_profile") and user_id and self.supabase_client:
            try:
                client_profile = await self.supabase_client.get_client_profile(user_id)
                if client_profile:
                    context["client_profile"] = client_profile
                    logger.info(f"Perfil de cliente obtenido/actualizado de Supabase para user_id {user_id}")
                else:
                    logger.warning(f"No se encontró perfil de cliente en Supabase para user_id {user_id}")
                    # No marcar como vacío aquí, podría haber datos previos en el contexto
            except Exception as e:
                logger.error(f"Error al obtener perfil de Supabase para user_id {user_id}: {e}")
                # No modificar el contexto existente en caso de error
                
        # 3. Fallback: usar estado interno (memoria) SOLO si no hay StateManager
        #    Esta parte se eliminó previamente, la mantenemos comentada como referencia.
        #    Si se requiere estado en memoria sin StateManager, necesitaría una implementación específica.
        # if not self.state_manager:
        #      # Lógica para manejar contexto en memoria si es necesario
        #      logger.debug(f"Contexto gestionado en memoria (requiere implementación) para key={context_key}")
        
        # Añadir user_id al contexto si no está (podría venir del StateManager)
        if "user_id" not in context and user_id:
             context["user_id"] = user_id
        
        # Asegurar que history existe y es una lista
        if "history" not in context or not isinstance(context.get("history"), list):
            context["history"] = []

        return context

    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], interaction_data: Dict[str, Any]):
        """
        Actualiza el contexto (perfil de usuario, historial) para la solicitud.
        Utiliza StateManager si está disponible.
        """
        context_key = f"context_{user_id}_{session_id}" if user_id and session_id else f"context_ets_default_{uuid.uuid4().hex[:6]}"
        context = await self._get_context(user_id, session_id)

        # Actualizar datos en el contexto
        context.update(interaction_data)

        # 1. Guardar en StateManager si está disponible
        if self.state_manager and user_id and session_id:
            try:
                await self.state_manager.save_state(user_id, session_id, {"context": context})
                logger.debug(f"Contexto actualizado en StateManager para key={context_key}")
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager para {context_key}: {e}")
        # Corregido: Quitar self.update_state y la lógica de memoria interna si no se implementa
        # else:
        #     # Actualizar estado en memoria si no hay StateManager (requiere implementación)
        #     # self.update_state(context_key, context)
        #     logger.debug(f"Contexto actualizado en memoria (requiere implementación) para key={context_key}")

    # --- Métodos de Ciclo de Vida ADK --- 

    async def start(self) -> None:
        """Inicia el agente, conectando y registrando skills."""
        await super().start() # Llama al start de ADKAgent para conexión y registro base
        if self._running:
            await self._register_skills()
            logger.info(f"Skills de {self.agent_id} registradas.")
        else:
             logger.warning(f"No se registraron skills para {self.agent_id} porque el inicio base falló.")

    async def _register_skills(self) -> None:
        """Registra las skills específicas de este agente con el toolkit ADK."""
        if not self.toolkit:
            logger.error(f"No se puede registrar skills para {self.agent_id}: Toolkit no inicializado.")
            return

        # Registrar cada función de skill
        self.register_skill("generate_training_plan", self._skill_generate_training_plan)
        self.register_skill("analyze_performance", self._skill_analyze_performance)
        self.register_skill("design_periodization", self._skill_design_periodization)
        self.register_skill("prescribe_exercises", self._skill_prescribe_exercises)
        
        logger.info(f"{len(self.skills)} skills registradas para {self.agent_id}.")

    # --- Eliminar métodos A2A/Antiguos --- 
    # (_run_async_impl, _process_request, _classify_request, _handle_*, _create_agent_card, get_agent_card)
    # Ya no son necesarios porque ADKAgent maneja el flujo.

    # --- Mantener métodos auxiliares si son usados por la lógica interna --- 
    # (Ej: _extract_profile_details, _get_program_type_from_profile)
    def _extract_profile_details(self, client_profile_data: Optional[Dict[str, Any]]) -> str:
        details = "" # <<< Inicializar aquí
        # ... (Lógica original sin cambios) ...
        return details
    
    def _get_program_type_from_profile(self, client_profile_data: Optional[Dict[str, Any]]) -> str:
        # Implementación para extraer el tipo de programa del perfil
        if client_profile_data and isinstance(client_profile_data, dict):
            program_type = client_profile_data.get("program_type", "general")
            # Asegurarse de que sea string y convertir a mayúsculas para consistencia
            return str(program_type).upper()
        return "GENERAL" # Default si no hay datos o no es diccionario

    # --- Skills --- #
