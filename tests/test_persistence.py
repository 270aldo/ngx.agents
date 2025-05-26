"""
Pruebas unitarias para la capa de persistencia con Supabase.

Este módulo contiene pruebas para verificar el funcionamiento
de la persistencia de usuarios y conversaciones en Supabase.
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock

from clients.supabase_client import SupabaseClient

# Constantes para pruebas
TEST_API_KEY = "test_api_key_123"
TEST_USER_ID = str(uuid.uuid4())
TEST_MESSAGE = "Mensaje de prueba"


@pytest.fixture
def supabase_client():
    """Fixture que proporciona un cliente Supabase simulado."""
    client = SupabaseClient()
    # Forzar modo simulado
    client.is_mock = True
    client._mock_users = {}
    client._mock_conversations = []
    return client


class TestUserPersistence:
    """Pruebas para la persistencia de usuarios."""

    def test_get_or_create_user_by_api_key_new(self, supabase_client):
        """Prueba la creación de un nuevo usuario por API key."""
        # Obtener un usuario que no existe (se creará)
        user = supabase_client.get_or_create_user_by_api_key(TEST_API_KEY)

        # Verificar que se creó correctamente
        assert user is not None
        assert "id" in user
        assert user["api_key"] == TEST_API_KEY
        assert "created_at" in user

        # Verificar que se almacenó en el diccionario mock
        assert len(supabase_client._mock_users) == 1
        assert user["id"] in supabase_client._mock_users

    def test_get_or_create_user_by_api_key_existing(self, supabase_client):
        """Prueba la obtención de un usuario existente por API key."""
        # Crear un usuario primero
        user1 = supabase_client.get_or_create_user_by_api_key(TEST_API_KEY)

        # Obtener el mismo usuario
        user2 = supabase_client.get_or_create_user_by_api_key(TEST_API_KEY)

        # Verificar que es el mismo usuario
        assert user1["id"] == user2["id"]
        assert user1["api_key"] == user2["api_key"]

        # Verificar que no se creó un nuevo usuario
        assert len(supabase_client._mock_users) == 1


class TestConversationPersistence:
    """Pruebas para la persistencia de conversaciones."""

    def test_log_conversation_message(self, supabase_client):
        """Prueba el registro de un mensaje de conversación."""
        # Registrar un mensaje
        result = supabase_client.log_conversation_message(
            TEST_USER_ID, "user", TEST_MESSAGE
        )

        # Verificar que se registró correctamente
        assert result is True
        assert len(supabase_client._mock_conversations) == 1

        # Verificar los datos del mensaje
        message = supabase_client._mock_conversations[0]
        assert message["user_id"] == TEST_USER_ID
        assert message["role"] == "user"
        assert message["message"] == TEST_MESSAGE
        assert "id" in message
        assert "created_at" in message

    def test_get_conversation_history_empty(self, supabase_client):
        """Prueba la obtención de un historial de conversación vacío."""
        # Obtener historial (vacío)
        history = supabase_client.get_conversation_history(TEST_USER_ID)

        # Verificar que está vacío
        assert history == []

    def test_get_conversation_history_with_messages(self, supabase_client):
        """Prueba la obtención de un historial de conversación con mensajes."""
        # Registrar varios mensajes
        supabase_client.log_conversation_message(TEST_USER_ID, "user", "Mensaje 1")
        supabase_client.log_conversation_message(TEST_USER_ID, "agent", "Respuesta 1")
        supabase_client.log_conversation_message(TEST_USER_ID, "user", "Mensaje 2")
        supabase_client.log_conversation_message(TEST_USER_ID, "agent", "Respuesta 2")

        # Obtener historial
        history = supabase_client.get_conversation_history(TEST_USER_ID)

        # Verificar que contiene los mensajes
        assert len(history) == 4
        assert history[0]["message"] == "Mensaje 1"
        assert history[1]["message"] == "Respuesta 1"
        assert history[2]["message"] == "Mensaje 2"
        assert history[3]["message"] == "Respuesta 2"

    def test_get_conversation_history_with_pagination(self, supabase_client):
        """Prueba la paginación del historial de conversación."""
        # Registrar varios mensajes en orden específico para asegurar el orden en las pruebas
        messages = [
            ("user", "Mensaje 1"),
            ("agent", "Respuesta 1"),
            ("user", "Mensaje 2"),
            ("agent", "Respuesta 2"),
            ("user", "Mensaje 3"),
            ("agent", "Respuesta 3"),
            ("user", "Mensaje 4"),
            ("agent", "Respuesta 4"),
            ("user", "Mensaje 5"),
            ("agent", "Respuesta 5"),
        ]

        for role, message in messages:
            supabase_client.log_conversation_message(TEST_USER_ID, role, message)

        # Obtener primera página (limit=4, offset=0)
        page1 = supabase_client.get_conversation_history(
            TEST_USER_ID, limit=4, offset=0
        )
        assert len(page1) == 4
        assert page1[0]["message"] == "Mensaje 1"
        assert page1[1]["message"] == "Respuesta 1"
        assert page1[2]["message"] == "Mensaje 2"
        assert page1[3]["message"] == "Respuesta 2"

        # Obtener segunda página (limit=4, offset=4)
        page2 = supabase_client.get_conversation_history(
            TEST_USER_ID, limit=4, offset=4
        )
        assert len(page2) == 4
        assert page2[0]["message"] == "Mensaje 3"
        assert page2[1]["message"] == "Respuesta 3"
        assert page2[2]["message"] == "Mensaje 4"
        assert page2[3]["message"] == "Respuesta 4"

    def test_get_conversation_history_for_different_users(self, supabase_client):
        """Prueba que el historial se filtra correctamente por usuario."""
        # Crear otro ID de usuario
        other_user_id = str(uuid.uuid4())

        # Registrar mensajes para ambos usuarios
        supabase_client.log_conversation_message(
            TEST_USER_ID, "user", "Mensaje usuario 1"
        )
        supabase_client.log_conversation_message(
            other_user_id, "user", "Mensaje usuario 2"
        )

        # Obtener historial para el primer usuario
        history1 = supabase_client.get_conversation_history(TEST_USER_ID)
        assert len(history1) == 1
        assert history1[0]["message"] == "Mensaje usuario 1"

        # Obtener historial para el segundo usuario
        history2 = supabase_client.get_conversation_history(other_user_id)
        assert len(history2) == 1
        assert history2[0]["message"] == "Mensaje usuario 2"


@pytest.mark.parametrize(
    "mock_mode,expected_calls",
    [
        (True, 0),  # En modo mock, no se llama a la API de Supabase
        (
            False,
            2,
        ),  # En modo real, se llama a la API de Supabase dos veces (select e insert)
    ],
)
class TestSupabaseClientModes:
    """Pruebas para verificar el comportamiento en modo mock vs. real."""

    @patch("supabase.Client.table")
    def test_get_or_create_user_mode(
        self, mock_table, supabase_client, mock_mode, expected_calls
    ):
        """Prueba que el modo mock funciona correctamente para usuarios."""
        # Configurar el modo
        supabase_client.is_mock = mock_mode
        if not mock_mode:
            # Configurar mock para modo real
            mock_execute = MagicMock()
            mock_execute.data = None
            mock_single = MagicMock()
            mock_single.execute.return_value = mock_execute
            mock_eq = MagicMock()
            mock_eq.single.return_value = mock_single
            mock_select = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_table.return_value.select.return_value = mock_select

            # Configurar cliente real
            supabase_client.client = MagicMock()
            supabase_client.client.table = mock_table

            # Resetear el contador de llamadas después de configurar los mocks
            mock_table.reset_mock()

        # Ejecutar la función
        supabase_client.get_or_create_user_by_api_key(TEST_API_KEY)

        # Verificar llamadas
        assert mock_table.call_count == expected_calls

    @patch("supabase.Client.table")
    def test_log_conversation_message_mode(
        self, mock_table, supabase_client, mock_mode, expected_calls
    ):
        """Prueba que el modo mock funciona correctamente para mensajes."""
        # Configurar el modo
        supabase_client.is_mock = mock_mode
        if not mock_mode:
            # Configurar cliente real
            supabase_client.client = MagicMock()
            supabase_client.client.table = mock_table

            # Resetear el contador de llamadas después de configurar los mocks
            mock_table.reset_mock()

        # Ejecutar la función
        supabase_client.log_conversation_message(TEST_USER_ID, "user", TEST_MESSAGE)

        # Verificar llamadas - en este caso solo hay una llamada a table() para insert
        if not mock_mode:
            assert mock_table.call_count == 1
