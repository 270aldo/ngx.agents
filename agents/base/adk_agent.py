import asyncio
import json
import uuid
import time
import logging
import traceback
import signal
from typing import Dict, List, Any, Optional, Callable, Union, Type, Tuple, Sequence
from datetime import datetime
from pydantic import BaseModel

# Importar componentes de Google ADK directamente desde nuestro adaptador
from adk.agent import Agent as GoogleADKAgent
from adk.agent import Skill as GoogleADKSkill
from adk.toolkit import Toolkit

# Stubs básicos para OpenTelemetry si no está disponible o falla la configuración
class MockTracer:
    def start_as_current_span(self, *args, **kwargs):
        class MockSpan:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def set_attribute(self, key, value): pass
            def record_exception(self, exception): pass
        return MockSpan()

class MockMeter:
    def create_counter(self, *args, **kwargs): 
        # Simular un contador que no hace nada
        mock_counter = type('MockCounter', (), {'add': lambda *a, **k: None})()
        # Asegurar que el nombre sea válido (aunque sea un mock)
        if args and isinstance(args[0], str) and (len(args[0]) > 63 or not args[0].isascii()):
            # logger.warning(f"MockCounter: Nombre de métrica potencialmente inválido: {args[0]}")
            pass # No lanzar excepción aquí para mocks, pero se podría loggear
        return mock_counter

    def create_histogram(self, *args, **kwargs): 
        # Simular un histograma que no hace nada
        mock_histogram = type('MockHistogram', (), {'record': lambda *a, **k: None})()
        if args and isinstance(args[0], str) and (len(args[0]) > 63 or not args[0].isascii()):
            # logger.warning(f"MockHistogram: Nombre de métrica potencialmente inválido: {args[0]}")
            pass
        return mock_histogram

_mock_tracer = MockTracer()
_mock_meter = MockMeter()

# Importaciones de OpenTelemetry
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.sdk.metrics import MeterProvider
    has_telemetry = True
except ImportError:
    has_telemetry = False
    # Los mocks _mock_tracer y _mock_meter se usarán si has_telemetry es False

# Importaciones internas
from agents.base.a2a_agent import A2AAgent
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from infrastructure.adapters.state_manager_adapter import ConversationContext
from infrastructure.adapters.state_manager_adapter import state_manager_adapter as state_manager
from infrastructure.adapters.vision_adapter import vision_adapter
from infrastructure.adapters.multimodal_adapter import multimodal_adapter
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result
from core.budget import budget_manager
from core.vision_processor import vision_processor

# Configurar logger
logger = get_logger(__name__)

class ADKAgent(A2AAgent, GoogleADKAgent):
    """
    Clase base unificada para agentes NGX que usan Google ADK y el protocolo A2A.
    Las clases hijas DEBEN definir `self.skills` ANTES de llamar a `super().__init__(...)`.
    
    Esta clase hereda tanto de A2AAgent como de GoogleADKAgent para proporcionar
    compatibilidad con ambos sistemas.
    """
    tracer: Any
    meter: Any
    request_counter: Any
    response_time_histogram: Any

    gemini_client: Optional[GeminiClient] = None
    supabase_client: Optional[SupabaseClient] = None
    state_manager: Optional[StateManager] = None
    adk_toolkit: Optional[Toolkit] = None
    skills: List[Any] = []
    
    # Adaptadores para capacidades de visión y multimodales
    vision_adapter = vision_adapter
    multimodal_adapter = multimodal_adapter
    vision_processor = vision_processor

    def __init__(
        self,
        agent_id: str, name: str, description: str, model: str, instruction: str,
        gemini_client: Optional[GeminiClient] = None,
        supabase_client: Optional[SupabaseClient] = None,
        state_manager: Optional[StateManager] = None,
        adk_toolkit: Optional[Toolkit] = None,
        capabilities: Optional[List[str]] = None,
        endpoint: Optional[str] = None, auto_register_skills: bool = True,
        a2a_server_url: Optional[str] = None, version: str = "1.0.0",
        **kwargs
    ):
        self._setup_telemetry(name)
        self.agent_id = agent_id
        self.gemini_client = gemini_client if gemini_client else GeminiClient()
        self.supabase_client = supabase_client # Puede ser None
        if state_manager:
            self.state_manager = state_manager
        elif self.supabase_client:
            self.state_manager = StateManager(self.supabase_client.client)
        else:
            self.state_manager = None
            
        # Inicializar adaptadores de visión y multimodales
        self._initialize_vision_capabilities()
        
        # Inicializar el toolkit de ADK si no se proporciona
        if adk_toolkit is None:
            self.adk_toolkit = Toolkit()
        else:
            self.adk_toolkit = adk_toolkit

        if not hasattr(self, 'skills') or not self.skills or not isinstance(self.skills, list):
            logger.warning(f"Agente {name} ({agent_id}) no definió self.skills. No se registrarán skills.")
            processed_google_adk_tools, processed_a2a_skills_for_card, skill_names = [], [], []
        else:
            processed_google_adk_tools, processed_a2a_skills_for_card, skill_names = self._initialize_and_prepare_skills()
        
        final_capabilities = capabilities if capabilities is not None else skill_names
        
        # Inicializar A2AAgent
        A2AAgent.__init__(
            self,
            agent_id=agent_id, name=name, description=description,
            capabilities=final_capabilities, endpoint=endpoint, version=version,
            skills=processed_a2a_skills_for_card, 
            auto_register_skills=auto_register_skills, a2a_server_url=a2a_server_url,
            model=model, instruction=instruction, **kwargs 
        )
        
        # Inicializar GoogleADKAgent
        GoogleADKAgent.__init__(
            self,
            toolkit=self.adk_toolkit,
            name=name,
            description=description,
            **kwargs
        )
        
        logger.info(f"ADKAgent '{self.name}' ({self.agent_id}) inicializado.")
        
    async def _initialize_vision_capabilities(self):
        """Inicializa las capacidades de visión y multimodales."""
        try:
            # Inicializar adaptadores si no están inicializados
            if not self.vision_adapter.is_initialized:
                await self.vision_adapter.initialize()
            
            if not self.multimodal_adapter.is_initialized:
                await self.multimodal_adapter.initialize()
                
            if not self.vision_processor.is_initialized:
                await self.vision_processor.initialize()
                
            logger.info(f"Capacidades de visión y multimodales inicializadas para el agente '{self.name}'")
        except Exception as e:
            logger.error(f"Error al inicializar capacidades de visión para el agente '{self.name}': {e}", exc_info=True)

    def _sanitize_otel_name(self, name: str, max_length: int = 63) -> str:
        """Sanitiza un nombre para cumplir con las restricciones de OpenTelemetry."""
        # Convertir a minúsculas, reemplazar espacios y caracteres no alfanuméricos con guiones bajos
        sanitized = ''.join(c if c.isalnum() else '_' for c in name.lower())
        # Asegurar que no comience ni termine con guion bajo y no tenga múltiples guiones bajos consecutivos
        sanitized = '_'.join(filter(None, sanitized.split('_')))
        # Truncar si es demasiado largo
        return sanitized[:max_length]

    def _setup_telemetry(self, service_name: str):
        # Sanitizar el nombre del servicio para OpenTelemetry
        otel_service_name = self._sanitize_otel_name(service_name)
        otel_tracer_name = f"{otel_service_name}-tracer"
        otel_meter_name = f"{otel_service_name}-meter"
        otel_req_counter_name = self._sanitize_otel_name(f"{service_name.replace(' ', '_')}_req_total")
        otel_resp_time_hist_name = self._sanitize_otel_name(f"{service_name.replace(' ', '_')}_resp_time_secs")

        if not has_telemetry:
            logger.warning("OpenTelemetry SDK no instalado. La telemetría detallada está deshabilitada. Usando mocks.")
            self.tracer = _mock_tracer
            self.meter = _mock_meter
            # Los contadores/histogramas de los mocks no necesitan nombres específicos aquí
            self.request_counter = self.meter.create_counter("mock_req_total") 
            self.response_time_histogram = self.meter.create_histogram("mock_resp_time_secs")
            return
        
        try:
            resource = Resource(attributes={ResourceAttributes.SERVICE_NAME: otel_service_name})
            
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            self.tracer = trace.get_tracer(otel_tracer_name)
            
            self.meter_provider = MeterProvider(resource=resource)
            metrics.set_meter_provider(self.meter_provider)
            self.meter = metrics.get_meter(otel_meter_name)
            
            self.request_counter = self.meter.create_counter(otel_req_counter_name, "1", "Total requests")
            self.response_time_histogram = self.meter.create_histogram(otel_resp_time_hist_name, "s", "Response time")
            
            logger.info(f"Telemetría configurada para el servicio '{otel_service_name}'.")

        except Exception as e:
            logger.error(f"Error en la configuración de telemetría para '{otel_service_name}': {e}. Usando mocks.", exc_info=True)
            # Fallback a los mocks si la configuración de OTel falla
            self.tracer = _mock_tracer
            self.meter = _mock_meter
            self.request_counter = self.meter.create_counter("mock_req_total_fallback") 
            self.response_time_histogram = self.meter.create_histogram("mock_resp_time_fallback")

    def _initialize_and_prepare_skills(self) -> Tuple[List[Callable], List[Dict[str, Any]], List[str]]:
        processed_google_adk_tools = []
        processed_a2a_skills_for_card = []
        skill_names_for_card = [] # Nombres para las A2A cards, que podrían ser diferentes

        if not self.skills:
            logger.warning("No se han definido skills para este agente.")
            return [], [], []

        for skill_object in self.skills: # self.skills es ahora List[Skill]
            skill_name = skill_object.name
            skill_description = skill_object.description
            input_schema_pydantic = skill_object.input_schema
            output_schema_pydantic = skill_object.output_schema
            # Usar 'handler' consistentemente, ya que nuestro Skill stub lo usa.
            skill_callable = getattr(skill_object, 'handler', None)

            # 1. Registrar en el toolkit de Google ADK
            try:
                with self.tracer.start_as_current_span(f"register_skill_{skill_name}"):
                    if hasattr(self.adk_toolkit, 'register_skill'):
                        self.adk_toolkit.register_skill(skill_object)
                    elif hasattr(self.adk_toolkit, 'add_tool'):
                        self.adk_toolkit.add_tool(skill_object)
                    else:
                        logger.warning(f"No se pudo registrar la skill '{skill_name}' en el toolkit de Google ADK.")
            except Exception as e:
                logger.error(f"Error registrando skill '{skill_name}': {e}", exc_info=True)

            # 2. Preparar para Google ADK (lista de callables)
            if skill_callable and callable(skill_callable):
                processed_google_adk_tools.append(skill_callable)
            else:
                logger.warning(f"Skill '{skill_name}' no tiene un atributo 'handler' que sea callable. Saltando para Google ADK tools.")

            # 3. Preparar para A2A Card (lista de diccionarios)
            skill_name_for_card = skill_name.replace('_', ' ').title()
            skill_names_for_card.append(skill_name_for_card)

            a2a_skill_def = {
                "name": skill_name_for_card,
                "description": skill_description,
                "skill_id": skill_name,  # Usar el nombre original como ID único
            }

            if input_schema_pydantic:
                try:
                    # Asegurarse de que input_schema_pydantic es un modelo Pydantic
                    if not (isinstance(input_schema_pydantic, type) and issubclass(input_schema_pydantic, BaseModel)):
                        raise TypeError(f"input_schema para {skill_name} no es un modelo Pydantic.")
                    a2a_skill_def["inputModes"] = [
                        {
                            "format": "json",
                            "schema": input_schema_pydantic.model_json_schema()
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error generando JSON schema para input de {skill_name}: {e}")
            
            if output_schema_pydantic:
                try:
                    if not (isinstance(output_schema_pydantic, type) and issubclass(output_schema_pydantic, BaseModel)):
                        raise TypeError(f"output_schema para {skill_name} no es un modelo Pydantic.")
                    a2a_skill_def["outputModes"] = [
                        {
                            "format": "json",
                            "schema": output_schema_pydantic.model_json_schema()
                        }
                    ]
                except Exception as e:
                    logger.error(f"Error generando JSON schema para output de {skill_name}: {e}")

            processed_a2a_skills_for_card.append(a2a_skill_def)

        return processed_google_adk_tools, processed_a2a_skills_for_card, skill_names_for_card

    async def _get_context(self, user_id: str, session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Método placeholder para obtener contexto (perfil, historial) del usuario.
        Las subclases deberían implementar esto usando su cliente (ej: Supabase).
        """
        logger.warning(f"_get_context no implementado en ADKAgent base para user_id {user_id}")
        return {"client_profile": {}, "history": []}

    async def _update_context(self, user_id: str, session_id: Optional[str], interaction_data: Dict[str, Any], **kwargs) -> None:
        """
        Método placeholder para actualizar el contexto del usuario.
        Las subclases deberían implementar esto.
        """
        logger.warning(f"_update_context no implementado en ADKAgent base para user_id {user_id}")
        pass

    async def _get_program_type_from_profile(self, client_profile: Optional[Dict[str, Any]]) -> str:
        """Devuelve el tipo de programa (PRIME/LONGEVITY/GENERAL) a partir del perfil del cliente.

        Si el perfil o el campo ``program_type`` no está disponible, se asume ``"PRIME"``.
        
        Este método es asíncrono para mantener consistencia con las implementaciones
        en los agentes específicos que pueden necesitar consultar servicios externos.
        """
        # Si no hay perfil o el perfil no es un diccionario válido devolvemos PRIME.
        if not client_profile or not isinstance(client_profile, dict):
            return "PRIME"

        # Extraer program_type y normalizar a mayúsculas.
        program_value = client_profile.get("program_type")

        if not program_value:
            return "PRIME"

        selected_program = str(program_value).upper()

        valid_program_types = ["PRIME", "LONGEVITY", "GENERAL"]

        return selected_program if selected_program in valid_program_types else "GENERAL"

    async def _extract_profile_details(self, client_profile: Dict[str, Any]) -> str:
        """Convierte detalles clave del perfil en un string formateado."""
        details = []
        if client_profile:
            program_type = await self._get_program_type_from_profile(client_profile)
            details.append(f"- Programa: {program_type}")
            if goals := client_profile.get('goals'): details.append(f"- Objetivos: {goals}")
            if level := client_profile.get('experience_level'): details.append(f"- Experiencia: {level}")
            if metrics := client_profile.get('current_metrics'): details.append(f"- Métricas: {metrics}")
            if prefs := client_profile.get('preferences'): details.append(f"- Preferencias: {prefs}")
            if injuries := client_profile.get('injury_history'): details.append(f"- Lesiones: {injuries}")
        return "\n".join(details) if details else "No disponible"

    # Métodos para capacidades de visión
    async def analyze_image(self, image_data, analysis_type="full"):
        """
        Analiza una imagen y extrae información.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            analysis_type: Tipo de análisis ('full', 'labels', 'objects', 'text', 'faces', 'landmarks')
            
        Returns:
            Dict[str, Any]: Resultados del análisis
        """
        with self.tracer.start_as_current_span("agent_analyze_image"):
            return await self.vision_processor.analyze_image(image_data, analysis_type)
    
    async def extract_text_from_image(self, image_data):
        """
        Extrae texto de una imagen.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            
        Returns:
            Dict[str, Any]: Texto extraído y metadatos
        """
        with self.tracer.start_as_current_span("agent_extract_text_from_image"):
            return await self.vision_processor.extract_text(image_data)
    
    async def identify_objects_in_image(self, image_data, min_confidence=0.5):
        """
        Identifica objetos en una imagen.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            min_confidence: Confianza mínima para incluir objetos (0.0-1.0)
            
        Returns:
            Dict[str, Any]: Objetos identificados y metadatos
        """
        with self.tracer.start_as_current_span("agent_identify_objects_in_image"):
            return await self.vision_processor.identify_objects(image_data, min_confidence)
    
    async def analyze_faces_in_image(self, image_data):
        """
        Analiza caras en una imagen.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            
        Returns:
            Dict[str, Any]: Caras analizadas y metadatos
        """
        with self.tracer.start_as_current_span("agent_analyze_faces_in_image"):
            return await self.vision_processor.analyze_faces(image_data)
    
    async def describe_image(self, image_data, detail_level="standard", focus_aspect=None):
        """
        Genera una descripción detallada de una imagen.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            detail_level: Nivel de detalle ('brief', 'standard', 'detailed')
            focus_aspect: Aspecto en el que enfocarse (None, 'objects', 'people', 'scene', 'actions', 'colors')
            
        Returns:
            Dict[str, Any]: Descripción generada y metadatos
        """
        with self.tracer.start_as_current_span("agent_describe_image"):
            return await self.vision_processor.describe_image(image_data, detail_level, focus_aspect)
    
    # Métodos para capacidades multimodales
    async def process_multimodal(self, prompt, image_data, temperature=0.7, max_output_tokens=None):
        """
        Procesa contenido multimodal (texto + imagen).
        
        Args:
            prompt: Texto de prompt
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            temperature: Temperatura para generación
            max_output_tokens: Máximo de tokens a generar
            
        Returns:
            Dict[str, Any]: Respuesta generada
        """
        with self.tracer.start_as_current_span("agent_process_multimodal"):
            return await self.multimodal_adapter.process_multimodal(prompt, image_data, temperature, max_output_tokens)
    
    async def visual_qa(self, question, image_data, temperature=0.2, max_output_tokens=1024):
        """
        Responde preguntas sobre una imagen.
        
        Args:
            question: Pregunta sobre la imagen
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            temperature: Temperatura para generación
            max_output_tokens: Máximo de tokens a generar
            
        Returns:
            Dict[str, Any]: Respuesta a la pregunta
        """
        with self.tracer.start_as_current_span("agent_visual_qa"):
            return await self.multimodal_adapter.visual_qa(question, image_data, temperature, max_output_tokens)
    
    async def generate_image_caption(self, image_data, style="descriptive", max_length=None):
        """
        Genera un pie de foto para una imagen.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            style: Estilo del pie de foto ('descriptive', 'concise', 'creative', 'technical')
            max_length: Longitud máxima del pie de foto
            
        Returns:
            Dict[str, Any]: Pie de foto generado
        """
        with self.tracer.start_as_current_span("agent_generate_image_caption"):
            return await self.multimodal_adapter.generate_image_caption(image_data, style, max_length)
    
    async def compare_images(self, image_data1, image_data2, comparison_aspects=None):
        """
        Compara dos imágenes y genera un análisis de similitudes y diferencias.
        
        Args:
            image_data1: Datos de la primera imagen (base64, bytes o dict con url o path)
            image_data2: Datos de la segunda imagen (base64, bytes o dict con url o path)
            comparison_aspects: Aspectos específicos a comparar (None para comparación general)
            
        Returns:
            Dict[str, Any]: Análisis comparativo de las imágenes
        """
        with self.tracer.start_as_current_span("agent_compare_images"):
            return await self.multimodal_adapter.compare_images(image_data1, image_data2, comparison_aspects)
    
    # Método para manejar la ejecución de Google ADK
    async def run(self, *args, **kwargs):
        """
        Ejecuta el agente utilizando la implementación de Google ADK.
        
        Este método sobrescribe el método run de GoogleADKAgent para proporcionar
        compatibilidad con el sistema NGX Agents.
        """
        try:
            # Registrar la solicitud en telemetría
            self.request_counter.add(1)
            
            # Medir el tiempo de respuesta
            start_time = time.time()
            
            # Establecer el ID del agente en el cliente de Gemini para seguimiento de presupuesto
            if self.gemini_client:
                self.gemini_client.set_current_agent(self.agent_id)
            
            # Verificar estado del presupuesto
            budget_status = budget_manager.get_budget_status(self.agent_id)
            if budget_status.get("percentage", 0) > 90:
                logger.warning(f"Agente {self.agent_id} está cerca del límite de presupuesto: {budget_status.get('percentage')}%")
            
            # Ejecutar el agente utilizando la implementación de Google ADK
            with self.tracer.start_as_current_span("adk_agent_run"):
                result = await GoogleADKAgent.run(self, *args, **kwargs)
            
            # Registrar el tiempo de respuesta
            response_time = time.time() - start_time
            self.response_time_histogram.record(response_time)
            
            return result
        except Exception as e:
            logger.error(f"Error en la ejecución del agente ADK: {e}", exc_info=True)
            with self.tracer.start_as_current_span("adk_agent_run_error") as span:
                span.record_exception(e)
            raise
