"""
Pruebas unitarias para la integración entre el endpoint /chat y el Orchestrator.

Este módulo contiene pruebas para verificar que la integración entre
el endpoint /chat y el Orchestrator funcione correctamente.
"""

import pytest
import asyncio
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Importar directamente desde el proyecto
from app import route_message, MessageRequest, StandardResponse
from middleware.auth import get_api_key
from clients.supabase_client import SupabaseClient
from orchestrator.orchestrator import Orchestrator, TaskResult

# Constantes para pruebas
TEST_API_KEY = "test_api_key"
TEST_USER_ID = "test_user_id"
TEST_SESSION_ID = "test_session_id"

# Mock para el cliente Supabase
class MockSupabaseClient:
    def get_or_create_user_by_api_key(self, api_key):
        if api_key == TEST_API_KEY:
            return {"id": TEST_USER_ID, "api_key": api_key}
        return {}
    
    def log_conversation_message(self, user_id, role, message):
        return True

# Mock para el Orchestrator
class MockOrchestrator:
    async def refresh_agents(self):
        return 5  # Número simulado de agentes
    
    async def execute_task(self, task, target_agents=None):
        # Simular diferentes respuestas según el mensaje
        message = task.get("input", "")
        
        if "error" in message.lower():
            return {
                "task_id": "test_task_123",
                "success": False,
                "response": "",
                "error": "Error simulado para pruebas",
                "agents_used": [],
                "confidence": 0.0,
                "execution_time": 0.1,
            }
        
        if "vacío" in message.lower():
            return {
                "task_id": "test_task_123",
                "success": True,
                "response": "",
                "error": None,
                "agents_used": ["agent1"],
                "confidence": 0.7,
                "execution_time": 0.1,
            }
        
        if "múltiple" in message.lower():
            return {
                "task_id": "test_task_123",
                "success": True,
                "response": "Respuesta de múltiples agentes",
                "error": None,
                "agents_used": ["agent1", "agent2", "agent3"],
                "confidence": 0.9,
                "execution_time": 0.3,
            }
        
        # Respuesta para mensajes de entrenamiento
        if any(keyword in message.lower() for keyword in ["entrenamiento", "fuerza", "potencia", "rutina"]):
            return {
                "task_id": "test_task_456",
                "success": True,
                "response": "Plan de entrenamiento personalizado para ganar fuerza y potencia",
                "error": None,
                "agents_used": ["elite_training_strategist"],
                "confidence": 0.85,
                "execution_time": 0.3,
            }
        
        # Respuesta por defecto
        return {
            "task_id": "test_task_123",
            "success": True,
            "response": f"Respuesta simulada para: {message}",
            "error": None,
            "agents_used": ["agent1"],
            "confidence": 0.8,
            "execution_time": 0.2,
        }

# Crear una aplicación FastAPI de prueba
app = FastAPI()

# Configurar el cliente de prueba
client = TestClient(app)

# Configurar rutas de prueba
@app.post("/chat")
async def chat_endpoint(request: MessageRequest, api_key: str = Depends(get_api_key)):
    return await route_message(request, api_key)

# Fixtures para los mocks
@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("app.supabase_client", new=MockSupabaseClient()), \
         patch("app.orchestrator", new=MockOrchestrator()), \
         patch("middleware.auth.SupabaseClient", return_value=MockSupabaseClient()):
        yield

@pytest.fixture
def mock_api_key_header():
    async def mock_header(request):
        return request.headers.get("X-API-Key")
    
    with patch("middleware.auth.api_key_header", new=AsyncMock(side_effect=mock_header)):
        yield

# Pruebas
def test_chat_endpoint_success():
    """Prueba que el endpoint /chat funciona correctamente."""
    # Datos de prueba
    request_data = {
        "message": "Hola, ¿cómo estás?",
        "user_id": TEST_USER_ID,
        "session_id": TEST_SESSION_ID,
        "context": {"key": "value"}
    }
    
    # Realizar solicitud
    response = client.post(
        "/chat",
        json=request_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Respuesta simulada para: Hola, ¿cómo estás?" in data["data"]["response"]
    assert "agent1" in data["data"]["agents_used"]
    assert data["data"]["confidence"] == 0.8
    assert "execution_time" in data["data"]

def test_chat_endpoint_error_response():
    """Prueba que el endpoint /chat maneja correctamente los errores del orquestador."""
    # Datos de prueba con mensaje que provocará un error
    request_data = {
        "message": "Esto debería provocar un error",
        "user_id": TEST_USER_ID
    }
    
    # Realizar solicitud
    response = client.post(
        "/chat",
        json=request_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Verificar que la respuesta está vacía cuando hay error
    assert data["data"]["response"] == ""
    assert len(data["data"]["agents_used"]) == 0
    assert data["data"]["confidence"] == 0.0

def test_chat_endpoint_empty_response():
    """Prueba que el endpoint /chat maneja correctamente respuestas vacías."""
    # Datos de prueba con mensaje que provocará una respuesta vacía
    request_data = {
        "message": "Esto debería dar una respuesta vacío",
        "user_id": TEST_USER_ID
    }
    
    # Realizar solicitud
    response = client.post(
        "/chat",
        json=request_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["response"] == ""
    assert "agent1" in data["data"]["agents_used"]
    assert data["data"]["confidence"] == 0.7

def test_chat_endpoint_multiple_agents():
    """Prueba que el endpoint /chat maneja correctamente respuestas de múltiples agentes."""
    # Datos de prueba con mensaje que provocará una respuesta de múltiples agentes
    request_data = {
        "message": "Esto debería usar múltiple agentes",
        "user_id": TEST_USER_ID
    }
    
    # Realizar solicitud
    response = client.post(
        "/chat",
        json=request_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Respuesta de múltiples agentes" in data["data"]["response"]
    assert len(data["data"]["agents_used"]) == 3
    assert "agent1" in data["data"]["agents_used"]
    assert "agent2" in data["data"]["agents_used"]
    assert "agent3" in data["data"]["agents_used"]
    assert data["data"]["confidence"] == 0.9

def test_chat_endpoint_elite_training():
    """Prueba que el endpoint /chat enruta correctamente los mensajes al agente EliteTrainingStrategist."""
    # Datos de prueba con mensaje que debería enrutarse al agente EliteTrainingStrategist
    request_data = {
        "message": "Necesito un plan de entrenamiento para ganar fuerza y potencia",
        "user_id": TEST_USER_ID,
        "session_id": TEST_SESSION_ID
    }
    
    # Realizar solicitud - el mock del Orchestrator detectará las palabras clave
    # "entrenamiento", "fuerza" y "potencia" y devolverá una respuesta del agente EliteTrainingStrategist
    response = client.post(
        "/chat",
        json=request_data,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verificar respuesta
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Plan de entrenamiento personalizado" in data["data"]["response"]
    assert "elite_training_strategist" in data["data"]["agents_used"]
    assert data["data"]["confidence"] == 0.85

def test_chat_endpoint_without_api_key():
    """Prueba que el endpoint /chat requiere una API key válida."""
    # Datos de prueba
    request_data = {
        "message": "Hola sin API key",
        "user_id": TEST_USER_ID
    }
    
    # Realizar solicitud sin API key
    response = client.post("/chat", json=request_data)
    
    # Verificar respuesta de error
    assert response.status_code == 401
    assert "API key no proporcionada" in response.json()["detail"]

def test_chat_endpoint_with_invalid_api_key():
    """Prueba que el endpoint /chat valida la API key."""
    # Datos de prueba
    request_data = {
        "message": "Hola con API key inválida",
        "user_id": TEST_USER_ID
    }
    
    # Realizar solicitud con API key inválida
    response = client.post(
        "/chat",
        json=request_data,
        headers={"X-API-Key": "invalid_key"}
    )
    
    # Verificar respuesta de error
    assert response.status_code == 401
    assert "API key inválida" in response.json()["detail"]
