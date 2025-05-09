import asyncio
import json
import uuid
import time
import logging
import traceback
import signal
from typing import Dict, List, Any, Optional, Callable, Union, Type, Tuple, Sequence
from datetime import datetime

# Importar componentes de Google ADK directamente
try:
    from adk.toolkit import Toolkit
except ImportError:
    class Toolkit:
        """Stub Toolkit si el paquete adk no está instalado."""
        def __init__(self):
            pass

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
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)

class ADKAgent(A2AAgent):
    """
    Clase base unificada para agentes NGX que usan Google ADK y el protocolo A2A.
    Las clases hijas DEBEN definir `self.skills` ANTES de llamar a `super().__init__(...)`.
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
        self.adk_toolkit = adk_toolkit

        if not hasattr(self, 'skills') or not self.skills or not isinstance(self.skills, list):
            logger.warning(f"Agente {name} ({agent_id}) no definió self.skills. No se registrarán skills.")
            processed_google_adk_tools, processed_a2a_skills_for_card, skill_names = [], [], []
        else:
            processed_google_adk_tools, processed_a2a_skills_for_card, skill_names = self._initialize_and_prepare_skills()
        
        final_capabilities = capabilities if capabilities is not None else skill_names
        if processed_google_adk_tools: kwargs['tools'] = processed_google_adk_tools
        if self.adk_toolkit: kwargs['toolkit'] = self.adk_toolkit

        super().__init__(
            agent_id=agent_id, name=name, description=description,
            capabilities=final_capabilities, endpoint=endpoint, version=version,
            skills=processed_a2a_skills_for_card, 
            auto_register_skills=auto_register_skills, a2a_server_url=a2a_server_url,
            model=model, instruction=instruction, **kwargs 
        )
        logger.info(f"ADKAgent '{self.name}' ({self.agent_id}) inicializado.")

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
        google_tools: List[Callable] = []
        a2a_card_skills: List[Dict[str, Any]] = []
        skill_names: List[str] = []

        if not hasattr(self, 'skills') or not self.skills or not isinstance(self.skills, list):
            logger.warning("ADKAgent.skills no está definido como una lista válida o está vacía. Saltando inicialización de skills.")
            return google_tools, a2a_card_skills, skill_names

        for skill_object in self.skills:
            # Asumimos que skill_object es un objeto con atributos, 
            # similar a como EliteTrainingStrategist los define.
            skill_method = getattr(skill_object, 'method', None)
            skill_name_attr = getattr(skill_object, 'name', None)
            skill_description = getattr(skill_object, 'description', 'Descripción no disponible')
            # Usar skill_id si está presente, si no, generar uno a partir del nombre o del método.
            explicit_skill_id = getattr(skill_object, 'skill_id', None)
            s_input_schema = getattr(skill_object, 'input_schema', None)
            s_output_schema = getattr(skill_object, 'output_schema', None)

            if not callable(skill_method):
                logger.warning(f"Skill '{skill_name_attr or 'NombreDesconocido'}' no tiene un atributo 'method' que sea callable. Saltando.")
                continue
            
            google_tools.append(skill_method)
            
            # Determinar el nombre para la tarjeta y el ID de la skill
            card_name = skill_name_attr or skill_method.__name__.replace('_', ' ').title()
            # Priorizar explicit_skill_id, luego skill_name_attr (normalizado), luego nombre del método.
            actual_skill_id = explicit_skill_id or (skill_name_attr.lower().replace(" ", "_") if skill_name_attr else skill_method.__name__)

            skill_names.append(card_name) # Este es el nombre para mostrar en la UI/logs
            
            entry = {
                "name": card_name,
                "description": skill_description,
                "skill_id": actual_skill_id
            }
            
            if s_input_schema and hasattr(s_input_schema, 'model_json_schema'):
                try:
                    entry['inputModes'] = [{'format': 'json', 'schema': s_input_schema.model_json_schema()}]
                except Exception as e:
                    logger.error(f"Error generando JSON schema para input_schema de skill '{card_name}': {e}")
            else:
                logger.debug(f"Skill '{card_name}' no tiene un input_schema Pydantic o model_json_schema no está disponible.")
                        
            if s_output_schema and hasattr(s_output_schema, 'model_json_schema'):
                try:
                    entry['outputModes'] = [{'format': 'json', 'schema': s_output_schema.model_json_schema()}]
                except Exception as e:
                    logger.error(f"Error generando JSON schema para output_schema de skill '{card_name}': {e}")
            else:
                logger.debug(f"Skill '{card_name}' no tiene un output_schema Pydantic o model_json_schema no está disponible.")
                        
            a2a_card_skills.append(entry)
            
        return google_tools, a2a_card_skills, skill_names

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

    def _get_program_type_from_profile(self, client_profile: Dict[str, Any]) -> str:
        """Obtiene el tipo de programa (PRIME/LONGEVITY/GENERAL) del perfil del cliente."""
        # Obtener el valor de program_type del perfil.
        program_value = client_profile.get("program_type")

        # Si program_type no está presente, es None, o es un string vacío, usar "PRIME" por defecto.
        if not program_value: # Esto cubre None, '', False, etc.
            selected_program = "PRIME"
        else:
            # Convertir a string (por si acaso) y luego a mayúsculas.
            selected_program = str(program_value).upper()
        
        # Lista de tipos de programa válidos que pueden ser retornados directamente.
        valid_program_types = ["PRIME", "LONGEVITY", "GENERAL"]
        
        # Si el programa seleccionado (después de uppercasing) está en la lista de válidos, retornarlo.
        # De lo contrario, retornar "GENERAL" como fallback.
        if selected_program in valid_program_types:
            return selected_program
        else:
            return "GENERAL"

    def _extract_profile_details(self, client_profile: Dict[str, Any]) -> str:
        """Convierte detalles clave del perfil en un string formateado."""
        details = []
        if client_profile:
            details.append(f"- Programa: {self._get_program_type_from_profile(client_profile)}")
            if goals := client_profile.get('goals'): details.append(f"- Objetivos: {goals}")
            if level := client_profile.get('experience_level'): details.append(f"- Experiencia: {level}")
            if metrics := client_profile.get('current_metrics'): details.append(f"- Métricas: {metrics}")
            if prefs := client_profile.get('preferences'): details.append(f"- Preferencias: {prefs}")
            if injuries := client_profile.get('injury_history'): details.append(f"- Lesiones: {injuries}")
        return "\n".join(details) if details else "No disponible"

# Nota: Se eliminaron los métodos _handle_adk_*, start, stop, run, _process_messages,
# ya que se asume que la clase base google.adk.agents.Agent se encarga del ciclo
# de vida principal y la comunicación, y A2AAgent maneja la lógica A2A.
