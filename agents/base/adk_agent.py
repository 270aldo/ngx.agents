import asyncio
import json
import uuid
import time
import logging
import traceback
import signal
from typing import Dict, List, Any, Optional, Callable, Union, Type, Tuple
from datetime import datetime

# Importar componentes de Google ADK directamente
from google.adk.toolkit import Toolkit
from google.adk.client import Client as ADKClient
from google.adk.client import ClientConfig
from google.adk.agent_card import AgentCard as GoogleAgentCard
from google.adk.agent_card import AgentSkill as GoogleAgentSkill
from google.adk.agent_card import AgentCapabilities

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
        self.toolkit = toolkit or Toolkit()
        self.state_manager = state_manager or StateManager()
        
        # Clientes para comunicación con servidores
        self.a2a_server_url = a2a_server_url
        self.adk_client: Optional[ADKClient] = None
        
        # Estado interno del agente
        self._state: Dict[str, Any] = {}
        self._running = False
        self._message_queue = asyncio.Queue()
        
        # Crear Agent Card
        self.agent_card: GoogleAgentCard = self._create_agent_card()
        
        # Configurar telemetría
        self._setup_telemetry()
        
        logger.info(f"Agente ADK '{self.agent_id}' inicializado")

    def _setup_telemetry(self):
        """
        Configura la telemetría para el agente.
        
        Placeholder para configuración futura de OpenTelemetry u otros.
        """
        # TODO: Implementar configuración de telemetría (ej: OpenTelemetry)
        pass

    def update_state(self, key: str, value: Any) -> None:
        """
        Actualiza el estado interno del agente.
        
        Args:
            key: Clave del estado
            value: Valor a almacenar
        """
        self._state[key] = value

    def _create_agent_card(self) -> GoogleAgentCard:
        """
        Crea una Agent Card para el agente según las especificaciones oficiales de ADK.
        
        Returns:
            GoogleAgentCard: Agent Card del agente
        """
        # Convertir skills internas a formato GoogleAgentSkill
        google_skills = []
        for skill_data in self.skills:
            try:
                # Asumir formato {'name': str, 'description': str, 'input_schema': dict, 'output_schema': dict}
                skill_name = skill_data.get('name')
                skill_desc = skill_data.get('description')
                input_schema = skill_data.get('input_schema', {})
                output_schema = skill_data.get('output_schema', {})
                
                if not skill_name or not skill_desc:
                    logger.warning(f"Skill data incompleta, omitiendo: {skill_data}")
                    continue
                    
                google_skills.append(GoogleAgentSkill(
                    name=skill_name,
                    description=skill_desc,
                    input_schema=input_schema,
                    output_schema=output_schema
                ))
            except Exception as e:
                logger.error(f"Error al procesar skill data {skill_data}: {e}")

        # Crear capabilities
        agent_capabilities = AgentCapabilities(capabilities=self.capabilities)

        # Crear Agent Card usando componentes de google.adk
        agent_card = GoogleAgentCard(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            version=self.version,
            capabilities=agent_capabilities,
            skills=google_skills,
            # Añadir otros campos requeridos o recomendados por ADK si es necesario
            # examples=[], 
            # metadata={}
        )
        logger.debug(f"Agent Card creada para {self.agent_id}: {agent_card.to_dict()}")
        return agent_card

    async def connect_to_adk(self) -> None:
        """
        Conecta el agente al servidor ADK usando google.adk.client.
        """
        # Verificar si ya está conectado
        if self.adk_client and self.adk_client.is_connected:
            logger.info(f"Agente {self.agent_id} ya está conectado al servidor ADK")
            return
        
        if not self.a2a_server_url:
            logger.error(f"No se ha configurado A2A_SERVER_URL para el agente {self.agent_id}. No se puede conectar.")
            raise ValueError("A2A_SERVER_URL no configurado")

        # Conectar al servidor ADK usando la implementación oficial
        try:
            logger.info(f"Intentando conectar agente {self.agent_id} al servidor ADK en {self.a2a_server_url}")
            config = ClientConfig(server_url=self.a2a_server_url)
            self.adk_client = ADKClient(config=config, agent_card=self.agent_card)
            
            # Registrar manejadores de eventos (ejemplo - adaptar a los reales de ADKClient)
            # self.adk_client.on_task_request(self._handle_adk_task_request) # Asumiendo que existe
            # self.adk_client.on_connect(self._handle_adk_connect)       # Asumiendo que existe
            # self.adk_client.on_disconnect(self._handle_adk_disconnect) # Asumiendo que existe
            
            await self.adk_client.connect() # Conectar al servidor
            
            # El registro debería ser manejado internamente por ADKClient al conectar
            logger.info(f"Agente {self.agent_id} conectado y registrado (?) en el servidor ADK en {self.a2a_server_url}")
            
        except Exception as e:
            logger.error(f"Error al conectar el agente {self.agent_id} al servidor ADK: {e}")
            logger.debug(traceback.format_exc())
            self.adk_client = None # Asegurar que el cliente no quede en estado inconsistente
            raise # Relanzar la excepción para que sea manejada por el código que llama

    async def disconnect_from_adk(self) -> None:
        """
        Desconecta el agente del servidor ADK.
        """
        if self.adk_client and self.adk_client.is_connected:
            try:
                logger.info(f"Desconectando agente {self.agent_id} del servidor ADK...")
                await self.adk_client.disconnect()
                logger.info(f"Agente {self.agent_id} desconectado del servidor ADK")
            except Exception as e:
                logger.error(f"Error al desconectar el agente {self.agent_id} del servidor ADK: {e}")
                logger.debug(traceback.format_exc())
            finally:
                self.adk_client = None # Limpiar referencia al cliente
        else:
            logger.info(f"Agente {self.agent_id} ya estaba desconectado.")

    async def send_task_to_agent(self, target_agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía una tarea a otro agente usando el cliente ADK.
        
        Args:
            target_agent_id: ID del agente destinatario
            task: Tarea a enviar (debe seguir el formato A2A)
            
        Returns:
            Dict[str, Any]: Respuesta del agente en formato A2A
            
        Raises:
            ConnectionError: Si el agente no está conectado al servidor ADK.
            Exception: Si ocurre un error durante el envío o recepción.
        """
        if not self.adk_client or not self.adk_client.is_connected:
            logger.error(f"Agente {self.agent_id} no está conectado. No se puede enviar tarea.")
            raise ConnectionError(f"Agente {self.agent_id} no conectado al servidor ADK.")

        try:
            logger.info(f"Agente {self.agent_id} enviando tarea a {target_agent_id}: {task.get('task_id')}")
            # Validar la tarea antes de enviarla (opcional pero recomendado)
            validate_task(task)
            
            # Usar el método send_task del cliente ADK oficial
            result = await self.adk_client.send_task(target_agent_id=target_agent_id, task=task)
            
            logger.info(f"Agente {self.agent_id} recibió resultado de {target_agent_id} para tarea {task.get('task_id')}")
            # Validar el resultado recibido (opcional pero recomendado)
            validate_result(result)
            
            return result
        except Exception as e:
            logger.error(f"Error al enviar tarea de {self.agent_id} a {target_agent_id}: {e}")
            logger.debug(traceback.format_exc())
            # Considerar devolver un error estándar o relanzar
            raise

    def register_skill(self, skill_name: str, skill_function: Callable) -> None:
        """
        Registra una skill en el toolkit del agente usando el toolkit de ADK.
        
        Args:
            skill_name: Nombre de la skill
            skill_function: Función que implementa la skill
        """
        try:
            logger.info(f"Registrando skill '{skill_name}' en el toolkit del agente {self.agent_id}")
            # Usar el método register_skill del toolkit oficial
            self.toolkit.register_skill(skill_name=skill_name, skill_function=skill_function)
            logger.info(f"Skill '{skill_name}' registrada correctamente.")
            
            # Actualizar la lista interna y la Agent Card si es necesario (puede ser complejo)
            # Opcionalmente, podríamos requerir que todas las skills se definan en __init__
            # y evitar el registro dinámico para simplificar.
            
        except Exception as e:
            logger.error(f"Error al registrar skill '{skill_name}': {e}")
            logger.debug(traceback.format_exc())
            raise

    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """
        Ejecuta una skill registrada en el toolkit usando el toolkit de ADK.
        
        Args:
            skill_name: Nombre de la skill
            **kwargs: Argumentos para la skill
            
        Returns:
            Any: Resultado de la ejecución de la skill
            
        Raises:
            KeyError: Si la skill no está registrada.
            Exception: Si ocurre un error durante la ejecución.
        """
        logger.info(f"Agente {self.agent_id} ejecutando skill '{skill_name}' con args: {kwargs}")
        try:
            # Usar el método execute_skill del toolkit oficial
            result = await self.toolkit.execute_skill(skill_name=skill_name, **kwargs)
            logger.info(f"Skill '{skill_name}' ejecutada, resultado: {result}")
            return result
        except KeyError:
            logger.error(f"Skill '{skill_name}' no encontrada en el toolkit del agente {self.agent_id}")
            raise # Relanzar KeyError para indicar que la skill no existe
        except Exception as e:
            logger.error(f"Error al ejecutar skill '{skill_name}': {e}")
            logger.debug(traceback.format_exc())
            # Considerar devolver un error estándar o relanzar
            raise
            
    # --- Métodos del ciclo de vida del agente (ADK Standard) ---
    
    async def _handle_adk_task_request(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manejador para tareas entrantes recibidas a través del ADKClient.
        Debe ser registrado con `adk_client.on_task_request`.
        
        Args:
            task: Tarea recibida del servidor ADK.
            
        Returns:
            Dict[str, Any]: Resultado de la ejecución de la tarea.
        """
        logger.info(f"Agente {self.agent_id} recibió tarea: {task.get('task_id')}")
        try:
            validate_task(task)
            skill_name = task.get('skill_name')
            params = task.get('params', {})
            
            if not skill_name:
                raise ValueError("La tarea no contiene 'skill_name'")
            
            # Ejecutar la skill solicitada
            skill_result = await self.execute_skill(skill_name, **params)
            
            # Crear resultado en formato A2A
            result_payload = create_result(
                task_id=task.get('task_id'),
                sender_agent_id=self.agent_id,
                target_agent_id=task.get('sender_agent_id'),
                result=skill_result,
                status='completed'
            )
            validate_result(result_payload)
            logger.info(f"Tarea {task.get('task_id')} completada por {self.agent_id}")
            return result_payload
            
        except Exception as e:
            logger.error(f"Error al manejar la tarea {task.get('task_id')} en {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
            # Crear resultado de error en formato A2A
            error_result = create_result(
                task_id=task.get('task_id'),
                sender_agent_id=self.agent_id,
                target_agent_id=task.get('sender_agent_id'),
                result={'error': str(e), 'traceback': traceback.format_exc() if logging.getLogger().level == logging.DEBUG else None},
                status='failed'
            )
            return error_result
            
    async def _handle_adk_connect(self):
        """
Manejador para el evento de conexión exitosa.
        Debe ser registrado con `adk_client.on_connect`.
        """
        logger.info(f"Agente {self.agent_id} manejó evento de conexión.")
        # Realizar acciones post-conexión si es necesario

    async def _handle_adk_disconnect(self):
        """
Manejador para el evento de desconexión.
        Debe ser registrado con `adk_client.on_disconnect`.
        """
        logger.warning(f"Agente {self.agent_id} manejó evento de desconexión.")
        # Intentar reconectar o limpiar estado si es necesario
        self.adk_client = None # Asegurar que se limpie la referencia

    async def start(self) -> None:
        """
        Inicia el agente, conectándolo al servidor ADK y registrando sus skills.
        """
        if self._running:
            logger.warning(f"El agente {self.agent_id} ya está en ejecución.")
            return
            
        try:
            logger.info(f"Iniciando agente {self.agent_id}...")
            self._running = True
            
            # Conectar al servidor ADK
            await self.connect_to_adk() # Esto ahora usa ADKClient
            
            # Registrar manejadores de eventos del cliente ADK
            if self.adk_client:
                 self.adk_client.on_task_request(self._handle_adk_task_request)
                 self.adk_client.on_connect(self._handle_adk_connect)
                 self.adk_client.on_disconnect(self._handle_adk_disconnect)
            else:
                logger.error(f"No se pudo iniciar el agente {self.agent_id} porque la conexión ADK falló.")
                self._running = False
                return # No continuar si no hay cliente ADK

            # Registrar skills definidas en la inicialización en el toolkit
            # (Asumiendo que skill_function es una referencia a la función real)
            # Esto necesita una forma de mapear el nombre/descripción de self.skills a las funciones
            # TODO: Mejorar la forma en que se definen y registran las skills
            # Ejemplo temporal/conceptual:
            # for skill_data in self.skills:
            #     skill_name = skill_data.get('name')
            #     # Necesitaríamos la función real aquí, no solo la descripción
            #     # skill_func = self.get_skill_function_by_name(skill_name) 
            #     # if skill_name and skill_func:
            #     #     self.register_skill(skill_name, skill_func)
            
            # Ejemplo de registro de una skill genérica (si es necesario)
            # async def generic_skill(**kwargs):
            #     logger.info(f"Ejecutando skill genérica con: {kwargs}")
            #     return {"status": "ok", "details": kwargs}
            # self.register_skill("generic_skill", generic_skill)

            # Implementación específica de inicio si existe
            if hasattr(self, "_start_impl"):
                await self._start_impl()
            
            logger.info(f"Agente {self.agent_id} iniciado y listo.")
            
        except Exception as e:
            logger.error(f"Error al iniciar el agente {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
            self._running = False # Marcar como no corriendo en caso de error
            # Asegurar desconexión si hubo conexión parcial
            await self.disconnect_from_adk()
            raise # Relanzar para que el error sea visible

    async def stop(self) -> None:
        """
        Detiene el agente, desconectándolo del servidor ADK y liberando recursos.
        """
        try:
            # Marcar el agente como no corriendo para detener bucles
            self._running = False 
            
            # Implementación específica de detención si existe
            if hasattr(self, "_stop_impl"):
                await self._stop_impl()
            
            # Desconectar del servidor ADK
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
            
            # Si el inicio falló (ej, no se conectó), self._running será False
            if not self._running:
                 logger.warning(f"El agente {self.agent_id} no pudo iniciarse correctamente. Saliendo de run_forever.")
                 return
            
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
                # El cliente ADK debería manejar la recepción de tareas en su propio bucle/thread
                # Aquí podemos añadir lógica periódica si es necesario
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info(f"Agente {self.agent_id} cancelado")
        except Exception as e:
            logger.error(f"Error en la ejecución del agente {self.agent_id}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Asegurar que el agente se detenga correctamente, incluso si start() falló
            if self._running: # Solo detener si se marcó como corriendo
                 await self.stop()
            logger.info(f"Ejecución de run_forever para {self.agent_id} finalizada.")


# Función para ejecutar un agente ADK como proceso independiente
async def run_agent(agent_class: Type[ADKAgent], **kwargs) -> None:
    """
    Ejecuta un agente ADK como proceso independiente siguiendo las especificaciones oficiales.
    
    Args:
        agent_class: Clase del agente a ejecutar
        **kwargs: Argumentos para inicializar el agente
    """
    agent = None # Inicializar agent a None
    try:
        # Crear instancia del agente
        agent = agent_class(**kwargs)
        logger.info(f"Agente {agent.agent_id} creado correctamente")
        
        # Ejecutar el agente indefinidamente
        await agent.run_forever()
    except Exception as e:
        logger.error(f"Error al ejecutar el agente: {e}")
        logger.debug(traceback.format_exc())
        # Asegurarse de detener el agente si se creó y ocurrió un error después
        if agent and agent._running:
            await agent.stop()
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
        # Configurar logging básico si no está ya configurado
        if not logging.getLogger().hasHandlers():
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
