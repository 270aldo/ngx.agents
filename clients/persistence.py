"""
Módulo para la persistencia de datos en Supabase.

Este módulo proporciona funciones para gestionar usuarios y conversaciones
en la base de datos Supabase.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .supabase_client import SupabaseClient


class PersistenceClient:
    """
    Cliente para la persistencia de datos en Supabase.

    Proporciona métodos para gestionar usuarios y conversaciones.
    """

    def __init__(self, supabase_client: SupabaseClient):
        """
        Inicializa el cliente de persistencia.

        Args:
            supabase_client: Cliente de Supabase
        """
        self.supabase_client = supabase_client

        # Para modo mock
        self.is_mock = False
        self._mock_users = {}
        self._mock_conversations = []

    def get_or_create_user_by_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Obtiene o crea un usuario basado en su API key.

        Args:
            api_key: API key del usuario

        Returns:
            Datos del usuario
        """
        if self.is_mock:
            # Buscar usuario existente por API key
            for user_id, user in self._mock_users.items():
                if user.get("api_key") == api_key:
                    return user

            # Crear nuevo usuario
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "api_key": api_key,
                "created_at": datetime.now().isoformat(),
            }
            self._mock_users[user_id] = user
            return user
        else:
            # Implementación real (asíncrona)
            # Esta implementación no funcionará en pruebas sincrónicas
            # pero es necesaria para la aplicación real
            raise NotImplementedError(
                "Implementación real no disponible en modo sincrónico"
            )

    def log_conversation_message(self, user_id: str, role: str, message: str) -> bool:
        """
        Registra un mensaje de conversación.

        Args:
            user_id: ID del usuario
            role: Rol del mensaje (user, agent, system)
            message: Contenido del mensaje

        Returns:
            True si se registró correctamente
        """
        if self.is_mock:
            # Crear nuevo mensaje
            message_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "role": role,
                "message": message,
                "created_at": datetime.now().isoformat(),
            }
            self._mock_conversations.append(message_data)
            return True
        else:
            # Implementación real (asíncrona)
            raise NotImplementedError(
                "Implementación real no disponible en modo sincrónico"
            )

    def get_conversation_history(
        self, user_id: str, limit: Optional[int] = None, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de conversación de un usuario.

        Args:
            user_id: ID del usuario
            limit: Número máximo de mensajes a obtener
            offset: Número de mensajes a saltar

        Returns:
            Lista de mensajes
        """
        if self.is_mock:
            # Filtrar mensajes por usuario
            messages = [
                msg for msg in self._mock_conversations if msg["user_id"] == user_id
            ]

            # Aplicar paginación
            if limit is not None:
                return messages[offset : offset + limit]
            else:
                return messages[offset:]
        else:
            # Implementación real (asíncrona)
            raise NotImplementedError(
                "Implementación real no disponible en modo sincrónico"
            )
