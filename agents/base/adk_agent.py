"""
Agente base compatible con Google ADK.

Este módulo proporciona una clase base para agentes compatibles con Google ADK,
que pueden registrarse y comunicarse a través del protocolo A2A.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Union, Type

# Importar ADK cuando esté disponible
try:
    from adk.toolkit import Toolkit
    from adk.client import Client as ADKClient
    from adk.client import ClientConfig
except ImportError:
    # Usar mocks para desarrollo si ADK no está disponible
    from tests.mocks.adk.toolkit import Toolkit
    ADKClient = object
    ClientConfig = object

from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager
from core.logging_config import get_logger
from infrastructure.a2a_server import DEFAULT_A2A_PORT

# Configurar logger
logger = get_logger(__name__)


class ADKAgent(A2AAgent):
    """
    Agente base compatible con Google ADK.
    
    Esta clase extiende A2AAgent para proporcionar compatibilidad con Google ADK,
    permitiendo que los agentes se registren y comuniquen a través del protocolo A2A.
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[str],
        toolkit: Optional[Toolkit] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
        version: str = "1.0.0",
        skills: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ):
        """
        Inicializa un agente compatible con ADK.
        
        Args:
            agent_id: Identificador único del agente
            name: Nombre del agente
            description: Descripción del agente
            capabilities: Lista de capacidades del agente
            toolkit: Toolkit con herramientas disponibles para el agente (opcional)
            a2a_server_url: URL del servidor A2A (opcional)
            state_manager: Gestor de estados para persistencia (opcional)
            version: Versión del agente (opcional)
            skills: Lista de habilidades del agente (opcional)
            **kwargs: Argumentos adicionales
        """
        # Inicializar A2AAgent base
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            a2a_server_url=a2a_server_url or f"ws://localhost:{DEFAULT_A2A_PORT}",
            version=version,
            skills=skills,
            **kwargs
        )
        
        # Inicializar componentes específicos de ADK
        self.toolkit = toolkit or Toolkit()
        self.state_manager = state_manager
        self.adk_client: Optional[ADKClient] = None
        
        # Crear Agent Card
        self.card = self._create_agent_card()
        
        logger.info(f"Agente ADK {agent_id} inicializado")
    
    def _create_agent_card(self) -> AgentCard:
        """
        Crea una Agent Card para el agente.
        
        Returns:
            AgentCard: Agent Card del agente
        """
        # Crear ejemplos de uso
        examples = []
        for capability in self.capabilities:
            # Crear un ejemplo básico para cada capacidad
            example_input = {
                "message": f"Ejemplo de entrada para {capability}",
                "context": {}
            }
            example_output = {
                "response": f"Ejemplo de respuesta para {capability}",
                "confidence": 0.9
            }
            examples.append({
                "input": example_input,
                "output": example_output
            })
        
        # Crear Agent Card
        return AgentCard.create_standard_card(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            skills=self.skills,
            version=self.version,
            examples=examples,
            metadata={
                "adk_compatible": True,
                "a2a_compatible": True
            }
        )
    
    async def connect_to_adk(self) -> None:
        """
        Conecta el agente al servidor ADK.
        """
        if not self.adk_client:
            # Configurar cliente ADK
            config = ClientConfig(server_url=self.a2a_server_url)
            self.adk_client = ADKClient(config)
            
            # Registrar agente en el servidor ADK
            await self.adk_client.register_agent(self.card.to_dict())
            logger.info(f"Agente {self.agent_id} registrado en el servidor ADK")
    
    async def disconnect_from_adk(self) -> None:
        """
        Desconecta el agente del servidor ADK.
        """
        if self.adk_client:
            await self.adk_client.unregister_agent(self.agent_id)
            self.adk_client = None
            logger.info(f"Agente {self.agent_id} desconectado del servidor ADK")
    
    async def send_task_to_agent(self, target_agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía una tarea a otro agente a través del servidor ADK.
        
        Args:
            target_agent_id: ID del agente destinatario
            task: Tarea a enviar
            
        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        if not self.adk_client:
            await self.connect_to_adk()
        
        # Enviar tarea al agente destinatario
        response = await self.adk_client.send_task(target_agent_id, task)
        return response
    
    async def register_skill(self, skill_name: str, skill_function: Callable) -> None:
        """
        Registra una skill en el toolkit del agente.
        
        Args:
            skill_name: Nombre de la skill
            skill_function: Función que implementa la skill
        """
        # Registrar skill en el toolkit
        self.toolkit.add_tool(skill_name, skill_function)
        
        # Actualizar lista de skills
        skill_description = getattr(skill_function, "__doc__", f"Skill {skill_name}")
        self.skills.append({
            "name": skill_name,
            "description": skill_description
        })
        
        logger.info(f"Skill {skill_name} registrada en el agente {self.agent_id}")
    
    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """
        Ejecuta una skill registrada en el toolkit.
        
        Args:
            skill_name: Nombre de la skill
            **kwargs: Argumentos para la skill
            
        Returns:
            Any: Resultado de la ejecución de la skill
        """
        # Verificar que la skill esté registrada
        if not self.toolkit.has_tool(skill_name):
            raise ValueError(f"Skill {skill_name} no registrada en el agente {self.agent_id}")
        
        # Ejecutar skill
        result = await self.toolkit.execute(skill_name, **kwargs)
        return result
    
    async def start(self) -> None:
        """
        Inicia el agente, conectándolo al servidor ADK y registrando sus skills.
        """
        # Conectar al servidor ADK
        await self.connect_to_adk()
        
        # Registrar skills
        for skill in self.skills:
            skill_name = skill["name"]
            # Verificar si la skill ya está registrada
            if not hasattr(self, f"skill_{skill_name}"):
                # Crear una skill genérica si no existe un método específico
                async def generic_skill(**kwargs):
                    return await self.execute_task(kwargs)
                
                # Registrar la skill
                await self.register_skill(skill_name, generic_skill)
        
        logger.info(f"Agente {self.agent_id} iniciado")
    
    async def stop(self) -> None:
        """
        Detiene el agente, desconectándolo del servidor ADK.
        """
        # Desconectar del servidor ADK
        await self.disconnect_from_adk()
        
        logger.info(f"Agente {self.agent_id} detenido")
    
    async def run_forever(self) -> None:
        """
        Mantiene el agente en ejecución indefinidamente.
        """
        # Iniciar el agente
        await self.start()
        
        # Mantener el agente en ejecución
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info(f"Agente {self.agent_id} cancelado")
        finally:
            # Detener el agente
            await self.stop()


# Función para ejecutar un agente ADK como proceso independiente
async def run_agent(agent_class: Type[ADKAgent], **kwargs) -> None:
    """
    Ejecuta un agente ADK como proceso independiente.
    
    Args:
        agent_class: Clase del agente a ejecutar
        **kwargs: Argumentos para inicializar el agente
    """
    # Crear instancia del agente
    agent = agent_class(**kwargs)
    
    # Configurar manejo de señales para detener el agente
    loop = asyncio.get_event_loop()
    
    # Manejador de señales para detener el agente
    async def handle_signal():
        logger.info(f"Recibida señal de terminación. Deteniendo agente {agent.agent_id}...")
        await agent.stop()
    
    # Registrar manejadores de señales
    for sig in (asyncio.SIGINT, asyncio.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(handle_signal()))
    
    # Ejecutar agente
    try:
        await agent.run_forever()
    except Exception as e:
        logger.error(f"Error en el agente {agent.agent_id}: {e}")
        raise
