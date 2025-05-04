"""
Agente base compatible con Google ADK (Agent Development Kit).

Este módulo proporciona una clase base para agentes compatibles con Google ADK,
que implementa correctamente el protocolo A2A (Agent-to-Agent) según las especificaciones
oficiales de Google.

Referencias:
- Google ADK: https://github.com/google/adk-docs
- Protocolo A2A: https://github.com/google/a2a
"""

import asyncio
import json
import uuid
import time
import logging
import traceback
import signal
from typing import Dict, List, Any, Optional, Callable, Union, Type, Tuple
from datetime import datetime

# Importar ADK cuando esté disponible
try:
    from google.adk import Agent as GoogleADKAgent
    from google.adk.toolkit import Toolkit
    from google.adk.client import Client as ADKClient
    from google.adk.client import ClientConfig
    from google.adk.agent_card import AgentCard as GoogleAgentCard
    from google.adk.agent_card import AgentSkill as GoogleAgentSkill
    from google.adk.agent_card import AgentCapabilities
    HAS_ADK = True
except ImportError:
    # Usar mocks para desarrollo si ADK no está disponible
    GoogleADKAgent = object
    Toolkit = object
    ADKClient = object
    ClientConfig = object
    GoogleAgentCard = object
    GoogleAgentSkill = object
    AgentCapabilities = object
    HAS_ADK = False

# Importar A2A cuando esté disponible
try:
    from google.a2a import A2AClient
    from google.a2a.agent_card import AgentCard as A2AAgentCard
    from google.a2a.agent_card import AgentSkill as A2AAgentSkill
    from google.a2a.agent_card import AgentCapabilities as A2ACapabilities
    HAS_A2A = True
except ImportError:
    # Usar mocks para desarrollo si A2A no está disponible
    A2AClient = object
    A2AAgentCard = object
    A2AAgentSkill = object
    A2ACapabilities = object
    HAS_A2A = False

# Importaciones internas
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)


class ADKAgent:
    """
    Agente base compatible con Google ADK (Agent Development Kit).
    
    Esta clase implementa la interfaz estándar de Google ADK y el protocolo A2A,
    permitiendo que los agentes se registren, comuniquen y ejecuten tareas
    siguiendo las especificaciones oficiales de Google.
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[str] = None,
        toolkit: Optional[Toolkit] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
        version: str = "1.0.0",
        skills: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Inicializa un agente compatible con Google ADK y el protocolo A2A.
        
        Args:
            agent_id: Identificador único del agente
            name: Nombre del agente
            description: Descripción del agente
            capabilities: Lista de capacidades del agente (opcional)
            toolkit: Toolkit con herramientas disponibles para el agente (opcional)
            a2a_server_url: URL del servidor A2A (opcional)
            state_manager: Gestor de estados para persistencia (opcional)
            version: Versión del agente (opcional)
            skills: Lista de habilidades del agente (opcional)
            **kwargs: Argumentos adicionales
        """
        # Atributos básicos del agente
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.version = version
        self.capabilities = capabilities or []
        self.skills = skills or []
        
        # Componentes del agente
        self.toolkit = toolkit or Toolkit() if HAS_ADK else None
        self.state_manager = state_manager or StateManager()
        
        # Clientes para comunicación con servidores
        self.a2a_server_url = a2a_server_url
        self.a2a_client = None
        self.adk_client = None
        
        # Estado interno
        self._state = {}
        self._running = False
        self._session_contexts = {}
        
        # Crear Agent Card según especificaciones A2A
        self.agent_card = self._create_agent_card()
        
        # Registrar métricas y telemetría
        self._setup_telemetry()
        
        logger.info(f"Agente ADK {agent_id} inicializado con {len(self.capabilities)} capacidades")
        
    def _setup_telemetry(self):
        """
        Configura la telemetría para el agente.
        """
        # Intentar configurar OpenTelemetry si está disponible
        try:
            from opentelemetry import trace, metrics
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.metrics import MeterProvider
            
            # Configurar trazas
            tracer_provider = TracerProvider()
            trace.set_tracer_provider(tracer_provider)
            self.tracer = trace.get_tracer(f"agent.{self.agent_id}")
            
            # Configurar métricas
            meter_provider = MeterProvider()
            metrics.set_meter_provider(meter_provider)
            meter = metrics.get_meter(f"agent.{self.agent_id}")
            
            # Crear contadores y medidores
            self.request_counter = meter.create_counter(
                name="agent_requests",
                description="Número de solicitudes recibidas por el agente",
                unit="1"
            )
            
            self.response_time = meter.create_histogram(
                name="agent_response_time",
                description="Tiempo de respuesta del agente en segundos",
                unit="s"
            )
            
            self.has_telemetry = True
            logger.info(f"Telemetría configurada para el agente {self.agent_id}")
        except ImportError:
            self.tracer = None
            self.request_counter = None
            self.response_time = None
            self.has_telemetry = False
            logger.warning(f"OpenTelemetry no disponible para el agente {self.agent_id}")
        except Exception as e:
            self.tracer = None
            self.request_counter = None
            self.response_time = None
            self.has_telemetry = False
            logger.warning(f"Error al configurar telemetría: {e}")
            
    def update_state(self, key: str, value: Any) -> None:
        """
        Actualiza el estado interno del agente.
        
        Args:
            key: Clave del estado
            value: Valor a almacenar
        """
        self._state[key] = value
    
    def _create_agent_card(self) -> Union[GoogleAgentCard, Dict[str, Any]]:
        """
        Crea una Agent Card para el agente según las especificaciones oficiales del protocolo A2A.
        
        Returns:
            Union[GoogleAgentCard, Dict[str, Any]]: Agent Card del agente
        """
        # Convertir skills a formato A2A
        agent_skills = []
        for skill in self.skills:
            # Verificar formato de skill
            if isinstance(skill, dict):
                skill_id = skill.get("id", f"{self.agent_id}-{skill.get('name', '').lower().replace(' ', '-')}")
                skill_name = skill.get("name", "")
                skill_description = skill.get("description", "")
                skill_tags = skill.get("tags", [])
                skill_examples = skill.get("examples", [])
                skill_input_modes = skill.get("inputModes", ["text"])
                skill_output_modes = skill.get("outputModes", ["text"])
                
                # Crear skill en formato A2A
                if HAS_A2A:
                    agent_skill = A2AAgentSkill(
                        id=skill_id,
                        name=skill_name,
                        description=skill_description,
                        tags=skill_tags,
                        examples=skill_examples,
                        inputModes=skill_input_modes,
                        outputModes=skill_output_modes
                    )
                else:
                    # Fallback si A2A no está disponible
                    agent_skill = {
                        "id": skill_id,
                        "name": skill_name,
                        "description": skill_description,
                        "tags": skill_tags,
                        "examples": skill_examples,
                        "inputModes": skill_input_modes,
                        "outputModes": skill_output_modes
                    }
                
                agent_skills.append(agent_skill)
        
        # Crear Agent Card según protocolo A2A
        if HAS_A2A:
            # Crear capacidades A2A
            capabilities = A2ACapabilities(
                streaming=False,
                pushNotifications=False,
                stateTransitionHistory=True
            )
            
            # Crear Agent Card A2A
            return A2AAgentCard(
                name=self.name,
                description=self.description,
                url=self.a2a_server_url,
                version=self.version,
                capabilities=capabilities,
                defaultInputModes=["text"],
                defaultOutputModes=["text"],
                skills=agent_skills
            )
        elif HAS_ADK:
            # Crear capacidades ADK
            capabilities = AgentCapabilities(
                streaming=False,
                push_notifications=False,
                state_transition_history=True
            )
            
            # Crear Agent Card ADK
            return GoogleAgentCard(
                name=self.name,
                description=self.description,
                url=self.a2a_server_url,
                version=self.version,
                capabilities=capabilities,
                default_input_modes=["text"],
                default_output_modes=["text"],
                skills=[GoogleAgentSkill(**s) if isinstance(s, dict) else s for s in agent_skills]
            )
        else:
            # Fallback si ni A2A ni ADK están disponibles
            return {
                "name": self.name,
                "description": self.description,
                "url": self.a2a_server_url,
                "version": self.version,
                "capabilities": {
                    "streaming": False,
                    "pushNotifications": False,
                    "stateTransitionHistory": True
                },
                "defaultInputModes": ["text"],
                "defaultOutputModes": ["text"],
                "skills": agent_skills
            }
    
    async def connect_to_adk(self) -> None:
        """
        Conecta el agente al servidor ADK siguiendo las especificaciones oficiales.
        """
        # Verificar si ya está conectado
        if self.adk_client is not None:
            logger.info(f"Agente {self.agent_id} ya está conectado al servidor ADK")
            return
        
        # Conectar al servidor ADK
        try:
            if HAS_ADK:
                # Usar implementación oficial de Google ADK
                config = ClientConfig(server_url=self.a2a_server_url)
                self.adk_client = ADKClient(config)
                await self.adk_client.connect()
                
                # Registrar el agente en el servidor ADK
                await self.adk_client.register_agent(self.agent_id, self.agent_card)
                
                logger.info(f"Agente {self.agent_id} conectado y registrado en el servidor ADK en {self.a2a_server_url}")
            elif HAS_A2A:
                # Usar implementación oficial de Google A2A
                self.a2a_client = A2AClient(self.a2a_server_url)
                await self.a2a_client.connect()
                
                # Registrar el agente en el servidor A2A
                await self.a2a_client.register_agent(self.agent_id, self.agent_card)
                
                logger.info(f"Agente {self.agent_id} conectado y registrado en el servidor A2A en {self.a2a_server_url}")
            else:
                logger.warning(f"No se puede conectar el agente {self.agent_id} al servidor: ni ADK ni A2A están disponibles")
        except Exception as e:
            logger.error(f"Error al conectar al servidor: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def disconnect_from_adk(self) -> None:
        """
        Desconecta el agente del servidor ADK o A2A.
        """
        try:
            # Desconectar del servidor ADK si está disponible
            if self.adk_client is not None:
                await self.adk_client.disconnect()
                self.adk_client = None
                logger.info(f"Agente {self.agent_id} desconectado del servidor ADK")
            
            # Desconectar del servidor A2A si está disponible
            if self.a2a_client is not None:
                await self.a2a_client.disconnect()
                self.a2a_client = None
                logger.info(f"Agente {self.agent_id} desconectado del servidor A2A")
        except Exception as e:
            logger.error(f"Error al desconectar el agente {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
    
    async def send_task_to_agent(self, target_agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía una tarea a otro agente siguiendo el protocolo A2A.
        
        Args:
            target_agent_id: ID del agente destinatario
            task: Tarea a enviar (debe seguir el formato A2A)
            
        Returns:
            Dict[str, Any]: Respuesta del agente en formato A2A
        """
        # Validar la tarea según el protocolo A2A
        if not validate_task(task):
            # Si la tarea no sigue el formato A2A, convertirla
            task = create_task(
                content=task.get("content", ""),
                metadata=task.get("metadata", {}),
                task_type=task.get("type", "text"),
                task_id=task.get("id", str(uuid.uuid4()))
            )
        
        try:
            # Intentar enviar la tarea usando ADK si está disponible
            if HAS_ADK and self.adk_client is not None:
                # Conectar si no está conectado
                if self.adk_client is None:
                    await self.connect_to_adk()
                
                # Enviar tarea al agente destinatario
                response = await self.adk_client.send_task(target_agent_id, task)
                return response
            
            # Intentar enviar la tarea usando A2A si está disponible
            elif HAS_A2A and self.a2a_client is not None:
                # Conectar si no está conectado
                if self.a2a_client is None:
                    await self.connect_to_adk()
                
                # Enviar tarea al agente destinatario
                response = await self.a2a_client.send_task(target_agent_id, task)
                return response
            
            # Si no hay cliente disponible, lanzar excepción
            else:
                raise ValueError(f"No hay cliente ADK o A2A disponible para enviar la tarea al agente {target_agent_id}")
        
        except Exception as e:
            logger.error(f"Error al enviar tarea al agente {target_agent_id}: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def register_skill(self, skill_name: str, skill_function: Callable) -> None:
        """
        Registra una skill en el toolkit del agente siguiendo las especificaciones de ADK.
        
        Args:
            skill_name: Nombre de la skill
            skill_function: Función que implementa la skill
        """
        try:
            # Obtener documentación y metadatos de la función
            skill_description = getattr(skill_function, "__doc__", f"Skill {skill_name}")
            skill_id = f"{self.agent_id}-{skill_name.lower().replace(' ', '-')}"
            
            # Crear skill en formato A2A
            skill_info = {
                "id": skill_id,
                "name": skill_name,
                "description": skill_description,
                "tags": getattr(skill_function, "tags", []),
                "examples": getattr(skill_function, "examples", []),
                "inputModes": getattr(skill_function, "input_modes", ["text"]),
                "outputModes": getattr(skill_function, "output_modes", ["text"])
            }
            
            # Registrar skill en el toolkit si ADK está disponible
            if HAS_ADK and self.toolkit is not None:
                self.toolkit.add_tool(skill_name, skill_function)
                logger.info(f"Skill {skill_name} registrada en el toolkit del agente {self.agent_id}")
            
            # Añadir skill a la lista de skills del agente
            self.skills.append(skill_info)
            
            # Actualizar Agent Card
            self.agent_card = self._create_agent_card()
            
            logger.info(f"Skill {skill_name} registrada en el agente {self.agent_id}")
        except Exception as e:
            logger.error(f"Error al registrar skill {skill_name}: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """
        Ejecuta una skill registrada en el toolkit siguiendo las especificaciones de ADK.
        
        Args:
            skill_name: Nombre de la skill
            **kwargs: Argumentos para la skill
            
        Returns:
            Any: Resultado de la ejecución de la skill
        """
        start_time = time.time()
        skill_found = False
        
        try:
            # Registrar métrica de ejecución de skill si telemetría está disponible
            if hasattr(self, "has_telemetry") and self.has_telemetry and hasattr(self, "request_counter"):
                self.request_counter.add(1, {"agent_id": self.agent_id, "skill": skill_name})
            
            # Crear span para trazar la ejecución si telemetría está disponible
            if hasattr(self, "has_telemetry") and self.has_telemetry and hasattr(self, "tracer"):
                with self.tracer.start_as_current_span(f"execute_skill_{skill_name}") as span:
                    span.set_attribute("agent_id", self.agent_id)
                    span.set_attribute("skill_name", skill_name)
                    
                    # Verificar que la skill esté registrada en el toolkit
                    if HAS_ADK and self.toolkit is not None and self.toolkit.has_tool(skill_name):
                        skill_found = True
                        # Ejecutar skill usando el toolkit de ADK
                        result = await self.toolkit.execute(skill_name, **kwargs)
                    else:
                        # Buscar la skill en la lista de skills
                        for skill in self.skills:
                            if skill.get("name") == skill_name:
                                skill_found = True
                                # Ejecutar la función directamente si está disponible como método
                                method_name = f"_skill_{skill_name.lower().replace(' ', '_')}"
                                if hasattr(self, method_name):
                                    result = await getattr(self, method_name)(**kwargs)
                                else:
                                    raise ValueError(f"Método {method_name} no implementado para la skill {skill_name}")
                                break
                        
                        if not skill_found:
                            raise ValueError(f"Skill {skill_name} no registrada en el agente {self.agent_id}")
                    
                    # Registrar métrica de tiempo de respuesta
                    end_time = time.time()
                    if hasattr(self, "response_time") and self.response_time:
                        self.response_time.record(end_time - start_time, {"agent_id": self.agent_id, "skill": skill_name})
                    
                    return result
            else:
                # Ejecución sin telemetría
                # Verificar que la skill esté registrada en el toolkit
                if HAS_ADK and self.toolkit is not None and self.toolkit.has_tool(skill_name):
                    skill_found = True
                    # Ejecutar skill usando el toolkit de ADK
                    result = await self.toolkit.execute(skill_name, **kwargs)
                else:
                    # Buscar la skill en la lista de skills
                    for skill in self.skills:
                        if skill.get("name") == skill_name:
                            skill_found = True
                            # Ejecutar la función directamente si está disponible como método
                            method_name = f"_skill_{skill_name.lower().replace(' ', '_')}"
                            if hasattr(self, method_name):
                                result = await getattr(self, method_name)(**kwargs)
                            else:
                                raise ValueError(f"Método {method_name} no implementado para la skill {skill_name}")
                            break
                    
                    if not skill_found:
                        raise ValueError(f"Skill {skill_name} no registrada en el agente {self.agent_id}")
                
                # Registrar tiempo de ejecución en logs
                end_time = time.time()
                logger.debug(f"Skill {skill_name} ejecutada en {end_time - start_time:.3f} segundos")
                
                return result
                
        except Exception as e:
            logger.error(f"Error al ejecutar skill {skill_name}: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def start(self) -> None:
        """
        Inicia el agente, conectándolo al servidor ADK/A2A y registrando sus skills.
        """
        try:
            # Marcar el agente como en ejecución
            self._running = True
            
            # Conectar al servidor ADK/A2A
            await self.connect_to_adk()
            
            # Registrar skills predefinidas
            if hasattr(self, "_register_skills"):
                await self._register_skills()
            
            # Registrar skills adicionales definidas en la lista de skills
            for skill in self.skills:
                if isinstance(skill, dict):
                    skill_name = skill.get("name", "")
                    if skill_name:
                        # Verificar si la skill ya está registrada en el toolkit
                        if HAS_ADK and self.toolkit and not self.toolkit.has_tool(skill_name):
                            # Buscar método específico para la skill
                            method_name = f"_skill_{skill_name.lower().replace(' ', '_')}"
                            if hasattr(self, method_name):
                                # Registrar método como skill
                                await self.register_skill(skill_name, getattr(self, method_name))
                            else:
                                # Crear una skill genérica si no existe un método específico
                                async def generic_skill(**kwargs):
                                    return await self.execute_task({"skill": skill_name, **kwargs})
                                
                                # Registrar la skill genérica
                                await self.register_skill(skill_name, generic_skill)
            
            # Implementación específica de inicio si existe
            if hasattr(self, "_start_impl"):
                await self._start_impl()
            
            logger.info(f"Agente {self.agent_id} iniciado correctamente")
        except Exception as e:
            self._running = False
            logger.error(f"Error al iniciar el agente {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    async def stop(self) -> None:
        """
        Detiene el agente, desconectándolo del servidor ADK/A2A y liberando recursos.
        """
        try:
            # Marcar el agente como detenido
            self._running = False
            
            # Implementación específica de detención si existe
            if hasattr(self, "_stop_impl"):
                await self._stop_impl()
            
            # Desconectar del servidor ADK/A2A
            await self.disconnect_from_adk()
            
            # Limpiar recursos
            if hasattr(self, "_cleanup"):
                await self._cleanup()
            
            logger.info(f"Agente {self.agent_id} detenido correctamente")
        except Exception as e:
            logger.error(f"Error al detener el agente {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
            # No relanzar la excepción para asegurar que el proceso de detención continúe
    
    async def run_forever(self) -> None:
        """
        Mantiene el agente en ejecución indefinidamente, siguiendo las especificaciones de ADK.
        """
        # Iniciar el agente
        try:
            await self.start()
            
            # Configurar manejo de señales para detener el agente
            loop = asyncio.get_running_loop()
            
            # Manejador de señales para detener el agente
            async def handle_signal():
                logger.info(f"Recibida señal de terminación. Deteniendo agente {self.agent_id}...")
                await self.stop()
            
            # Registrar manejadores de señales
            for sig_name in ('SIGINT', 'SIGTERM'):
                try:
                    sig = getattr(signal, sig_name)
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(handle_signal()))
                except (NotImplementedError, AttributeError):
                    # Ignorar si la plataforma no soporta add_signal_handler
                    pass
            
            # Mantener el agente en ejecución mientras esté activo
            logger.info(f"Agente {self.agent_id} en ejecución. Presiona Ctrl+C para detener.")
            while self._running:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info(f"Agente {self.agent_id} cancelado")
        except Exception as e:
            logger.error(f"Error en la ejecución del agente {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Asegurar que el agente se detenga correctamente
            await self.stop()


# Función para ejecutar un agente ADK como proceso independiente
async def run_agent(agent_class: Type[ADKAgent], **kwargs) -> None:
    """
    Ejecuta un agente ADK como proceso independiente siguiendo las especificaciones oficiales.
    
    Args:
        agent_class: Clase del agente a ejecutar
        **kwargs: Argumentos para inicializar el agente
    """
    try:
        # Crear instancia del agente
        agent = agent_class(**kwargs)
        logger.info(f"Agente {agent.agent_id} creado correctamente")
        
        # Ejecutar el agente indefinidamente
        await agent.run_forever()
    except Exception as e:
        logger.error(f"Error al ejecutar el agente: {e}")
        logger.debug(traceback.format_exc())
        raise

# Función auxiliar para ejecutar un agente desde la línea de comandos
def run_agent_cli(agent_class: Type[ADKAgent], **kwargs):
    """
    Ejecuta un agente ADK desde la línea de comandos.
    
    Args:
        agent_class: Clase del agente a ejecutar
        **kwargs: Argumentos para inicializar el agente
    """
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Crear y ejecutar el bucle de eventos
        asyncio.run(run_agent(agent_class, **kwargs))
    except KeyboardInterrupt:
        print("\nAgente detenido por el usuario")
    except Exception as e:
        print(f"Error al ejecutar el agente: {e}")
        traceback.print_exc()
