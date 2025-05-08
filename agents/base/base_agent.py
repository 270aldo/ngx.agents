"""Clase base para todos los agentes NGX.

Extiende el Agent oficial del ADK de Google y proporciona funcionalidad común
para todos los agentes de la plataforma NGX, incluyendo manejo de errores,
gestión de estado, logging y configuración estándar.
"""
from typing import Any, Dict, Optional, List, Union
import asyncio
import logging
import time
import uuid

# Importar el ADK oficial de Google
from adk.agent import Agent as GoogleAgent
from adk.toolkit import Toolkit

# Configurar logging
logger = logging.getLogger(__name__)

class BaseAgent(GoogleAgent):
    """Agente base que extiende el Agent oficial del ADK de Google.
    
    Esta clase proporciona funcionalidad común para todos los agentes NGX,
    incluyendo manejo de errores, timeout, logging y estructura de respuesta
    estandarizada. Todos los agentes especializados deben heredar de esta clase.
    
    Attributes:
        agent_id (str): Identificador único del agente
        name (str): Nombre descriptivo del agente
        description (str): Descripción de las capacidades del agente
        version (str): Versión del agente
    """
    
    def __init__(self, 
                 agent_id: str,
                 name: str,
                 description: str,
                 capabilities: List[str] = None,
                 version: str = "1.0.0",
                 toolkit: Optional[Toolkit] = None,
                 **kwargs):
        """Inicializa un agente base.
        
        Args:
            agent_id: Identificador único del agente
            name: Nombre descriptivo del agente
            description: Descripción de las capacidades del agente
            capabilities: Lista de capacidades del agente
            version: Versión del agente
            toolkit: Toolkit con herramientas disponibles para el agente
            **kwargs: Argumentos adicionales para pasar a la clase base
        """
        # Inicializar la clase base del ADK
        super().__init__(toolkit=toolkit, **kwargs)
        
        # Atributos básicos del agente
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.version = version
        self.created_at = time.strftime("%Y-%m-%d %H:%M:%S")

        # Extraer 'model' e 'instruction' de kwargs si están presentes
        self.model = kwargs.get('model', None) # Asignar un valor por defecto si no está
        self.instruction = kwargs.get('instruction', None) # Asignar un valor por defecto si no está
        
        # Estado interno del agente
        self._state = {}
        self._conversation_history = []
        
        logger.info(f"Agente {self.name} ({self.agent_id}) inicializado")
    
    async def run(self, user_input: str, user_id: Optional[str] = None, 
                 session_id: Optional[str] = None, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """Método público para ejecutar el agente con timeout y manejo de errores.
        
        Args:
            user_input: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            timeout: Tiempo máximo de ejecución en segundos
            **kwargs: Argumentos adicionales para el procesamiento
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        start_time = time.time()
        execution_id = str(uuid.uuid4())[:8]  # ID único para esta ejecución
        
        logger.info(f"[{execution_id}] Ejecutando agente {self.agent_id} para usuario {user_id or 'anónimo'}")
        logger.debug(f"[{execution_id}] Input: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        
        try:
            # Ejecutar la implementación del agente con timeout
            result = await asyncio.wait_for(
                self._run_async_impl(user_input, user_id, session_id, **kwargs), 
                timeout=timeout
            )
            
            # Registrar tiempo de ejecución
            execution_time = time.time() - start_time
            logger.info(f"[{execution_id}] Agente completado en {execution_time:.2f}s")
            
            # Asegurar que el resultado tenga la estructura correcta
            if isinstance(result, dict):
                if "execution_time" not in result:
                    result["execution_time"] = execution_time
                if "agent_id" not in result:
                    result["agent_id"] = self.agent_id
                return result
            else:
                # Si el resultado no es un diccionario, convertirlo al formato estándar
                return {
                    "status": "success",
                    "response": str(result),
                    "execution_time": execution_time,
                    "agent_id": self.agent_id
                }
                
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"[{execution_id}] Timeout al ejecutar agente para usuario {user_id} después de {execution_time:.2f}s")
            return {
                "status": "error",
                "error": "timeout", 
                "response": "Lo siento, la operación ha tardado demasiado tiempo.",
                "execution_time": execution_time,
                "agent_id": self.agent_id
            }
        except Exception as exc:
            execution_time = time.time() - start_time
            logger.error(f"[{execution_id}] Error al ejecutar agente: {exc}", exc_info=True)
            return {
                "status": "error",
                "error": str(exc), 
                "response": "Ha ocurrido un error al procesar tu solicitud.",
                "execution_time": execution_time,
                "agent_id": self.agent_id
            }
    
    async def _run_async_impl(self, user_input: str, user_id: Optional[str] = None,
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Implementación asíncrona del procesamiento del agente.
        
        Esta es la implementación real del procesamiento del agente que debe ser
        sobreescrita por las clases derivadas. La clase base proporciona una
        implementación básica que devuelve un mensaje de error.
        
        Args:
            user_input: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales para el procesamiento
            
        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        # Esta implementación debe ser sobreescrita por las clases derivadas
        return {
            "status": "error",
            "error": "not_implemented",
            "response": "Este agente no ha implementado el método _run_async_impl."
        }
    
    def update_state(self, key: str, value: Any) -> None:
        """Actualiza el estado interno del agente.
        
        Args:
            key: Clave del estado a actualizar
            value: Valor a asignar
        """
        self._state[key] = value
        
    def get_state(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor del estado interno del agente.
        
        Args:
            key: Clave del estado a obtener
            default: Valor por defecto si la clave no existe
            
        Returns:
            Any: Valor del estado o default si no existe
        """
        return self._state.get(key, default)
    
    def add_to_history(self, user_input: str, agent_response: str) -> None:
        """Añade una interacción al historial de conversación.
        
        Args:
            user_input: Entrada del usuario
            agent_response: Respuesta del agente
        """
        self._conversation_history.append({
            "timestamp": time.time(),
            "user": user_input,
            "agent": agent_response
        })
        
        # Limitar el tamaño del historial (mantener las últimas 10 interacciones)
        if len(self._conversation_history) > 10:
            self._conversation_history = self._conversation_history[-10:]
    
    def get_conversation_history(self, max_items: int = None) -> List[Dict[str, Any]]:
        """Obtiene el historial de conversación.
        
        Args:
            max_items: Número máximo de interacciones a devolver (las más recientes)
            
        Returns:
            List[Dict[str, Any]]: Historial de conversación
        """
        if max_items is not None and max_items > 0:
            return self._conversation_history[-max_items:]
        return self._conversation_history
