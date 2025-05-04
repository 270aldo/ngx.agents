"""
Gestor de estados de conversación para NGX Agents.

Este módulo proporciona una clase para gestionar el estado de las conversaciones
entre usuarios y agentes, utilizando Supabase como almacenamiento persistente.
"""
import json
import uuid
from typing import Any, Dict, Optional, List, Union

from core.settings import settings
from core.logging_config import get_logger
from clients.supabase_client import SupabaseClient

# Configurar logger
logger = get_logger(__name__)


class StateManager:
    """
    Gestor de estados de conversación para NGX Agents.
    
    Esta clase proporciona métodos para guardar, cargar y eliminar
    estados de conversación utilizando Supabase como almacenamiento.
    
    Attributes:
        supabase_client: Cliente de Supabase para interactuar con la base de datos
    """
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """
        Inicializa el gestor de estados.
        
        Args:
            supabase_client: Cliente de Supabase (opcional, se crea uno por defecto)
        """
        self.supabase_client = supabase_client or SupabaseClient()
        self.table_name = "conversation_states"
        logger.info("StateManager inicializado")
    
    async def save_state(
        self, 
        state_data: Dict[str, Any], 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guarda el estado de una conversación.
        
        Args:
            state_data: Datos del estado a guardar
            user_id: ID del usuario
            session_id: ID de la sesión (opcional, se genera uno si no se proporciona)
            
        Returns:
            Datos del estado guardado, incluyendo session_id
        """
        # Generar session_id si no se proporciona
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Generando nuevo session_id: {session_id}")
        
        # Preparar datos para guardar
        data = {
            "session_id": session_id,
            "user_id": user_id,
            "state_data": state_data
        }
        
        try:
            # Verificar si ya existe un estado para esta sesión
            existing_state = await self._get_state_by_session_id(session_id)
            
            if existing_state:
                # Actualizar estado existente
                logger.debug(f"Actualizando estado existente para session_id: {session_id}")
                result = await self.supabase_client.update(
                    table_name=self.table_name,
                    data={"state_data": state_data},
                    filters={"session_id": session_id}
                )
            else:
                # Crear nuevo estado
                logger.debug(f"Creando nuevo estado para session_id: {session_id}")
                result = await self.supabase_client.insert(
                    table_name=self.table_name,
                    data=data
                )
            
            if result and len(result) > 0:
                logger.info(f"Estado guardado correctamente para session_id: {session_id}")
                return result[0]
            else:
                logger.error(f"Error al guardar estado para session_id: {session_id}")
                return {"error": "No se pudo guardar el estado", "session_id": session_id}
                
        except Exception as e:
            logger.error(f"Error al guardar estado: {e}")
            return {"error": str(e), "session_id": session_id}
    
    async def load_state(
        self, 
        user_id: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        Carga el estado de una conversación.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Datos del estado cargado o un diccionario vacío si no existe
        """
        try:
            # Buscar estado por session_id y user_id
            result = await self.supabase_client.query(
                table_name=self.table_name,
                filters={
                    "session_id": session_id,
                    "user_id": user_id
                }
            )
            
            if result and len(result) > 0:
                logger.info(f"Estado cargado correctamente para session_id: {session_id}")
                return result[0].get("state_data", {})
            else:
                logger.warning(f"No se encontró estado para session_id: {session_id}")
                return {}
                
        except Exception as e:
            logger.error(f"Error al cargar estado: {e}")
            return {}
    
    async def delete_state(
        self, 
        user_id: str, 
        session_id: str
    ) -> bool:
        """
        Elimina el estado de una conversación.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            # Eliminar estado por session_id y user_id
            result = await self.supabase_client.delete(
                table_name=self.table_name,
                filters={
                    "session_id": session_id,
                    "user_id": user_id
                }
            )
            
            if result and len(result) > 0:
                logger.info(f"Estado eliminado correctamente para session_id: {session_id}")
                return True
            else:
                logger.warning(f"No se encontró estado para eliminar con session_id: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error al eliminar estado: {e}")
            return False
    
    async def list_user_sessions(
        self, 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Lista todas las sesiones de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de sesiones del usuario
        """
        try:
            # Buscar todas las sesiones del usuario
            result = await self.supabase_client.query(
                table_name=self.table_name,
                select="session_id, created_at, updated_at",
                filters={"user_id": user_id},
                order="updated_at.desc"
            )
            
            if result:
                logger.info(f"Se encontraron {len(result)} sesiones para el usuario {user_id}")
                return result
            else:
                logger.info(f"No se encontraron sesiones para el usuario {user_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error al listar sesiones: {e}")
            return []
    
    async def get_state_field(
        self, 
        user_id: str, 
        session_id: str, 
        field_path: str
    ) -> Any:
        """
        Obtiene un campo específico del estado de una conversación.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            field_path: Ruta al campo en formato "campo.subcampo"
            
        Returns:
            Valor del campo o None si no existe
        """
        try:
            # Cargar el estado completo
            state = await self.load_state(user_id, session_id)
            
            if not state:
                return None
            
            # Navegar por la ruta del campo
            parts = field_path.split(".")
            value = state
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    logger.warning(f"Campo {field_path} no encontrado en el estado")
                    return None
            
            return value
                
        except Exception as e:
            logger.error(f"Error al obtener campo {field_path}: {e}")
            return None
    
    async def update_state_field(
        self, 
        user_id: str, 
        session_id: str, 
        field_path: str, 
        value: Any
    ) -> bool:
        """
        Actualiza un campo específico del estado de una conversación.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            field_path: Ruta al campo en formato "campo.subcampo"
            value: Nuevo valor para el campo
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            # Cargar el estado completo
            state = await self.load_state(user_id, session_id)
            
            if not state:
                # Crear un nuevo estado si no existe
                state = {}
            
            # Navegar por la ruta del campo y actualizar
            parts = field_path.split(".")
            current = state
            
            # Navegar hasta el penúltimo nivel
            for i, part in enumerate(parts[:-1]):
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]
            
            # Actualizar el último nivel
            current[parts[-1]] = value
            
            # Guardar el estado actualizado
            result = await self.save_state(state, user_id, session_id)
            
            return "error" not in result
                
        except Exception as e:
            logger.error(f"Error al actualizar campo {field_path}: {e}")
            return False
    
    async def _get_state_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un estado por su session_id.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Estado encontrado o None si no existe
        """
        try:
            result = await self.supabase_client.query(
                table_name=self.table_name,
                filters={"session_id": session_id}
            )
            
            if result and len(result) > 0:
                return result[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error al buscar estado por session_id: {e}")
            return None
