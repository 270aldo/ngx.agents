from core.logging_config import get_logger

"""
Pruebas de integración para el endpoint /chat/ de la aplicación principal.

Este módulo contiene pruebas para verificar que la integración entre
el endpoint /chat/ y el Orchestrator funcione correctamente.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import (
    patch,
    MagicMock,
    AsyncMock,
)  # Mantener AsyncMock si MockOrchestrator lo usa

# Importar la aplicación principal y los esquemas correctos
from app.main import app
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    AgentResponse,
)  # Esquemas correctos

# Constantes para pruebas
TEST_API_KEY = (
    "test_api_key"  # Podría no ser necesario si get_current_user se mockea directamente
)
TEST_USER_ID = "test_user_id"
TEST_SESSION_ID = "test_session_id"

# Mock para el NGXNexusOrchestrator (o el resultado de get_orchestrator)
# Este mock es similar al MockOrchestrator anterior pero adaptado.
logger = get_logger(__name__)


class MockNGXNexusOrchestrator:
    def __init__(self, a2a_server_url: str, state_manager: Any):
        self.a2a_server_url = a2a_server_url
        self.state_manager = state_manager
        self.is_connected = True  # Simular conexión

    async def connect(self):
        self.is_connected = True
        logger.info("MockNGXNexusOrchestrator connected")

    async def run_async(
        self, input_text: str, user_id: str, session_id: str, context: dict
    ):
        # Simular diferentes respuestas según el mensaje
        if "error" in input_text.lower():
            return {
                "response": "",
                "agents_used": [],
                "agent_responses": [],
                "metadata": {"error": "Error simulado para pruebas"},
                "session_id": session_id,
            }

        if "vacío" in input_text.lower():
            return {
                "response": "",
                "agents_used": ["agent1"],
                "agent_responses": [
                    AgentResponse(
                        agent_id="agent1",
                        agent_name="Agent 1",
                        response="",
                        confidence=0.7,
                        artifacts=[],
                    )
                ],
                "metadata": {},
                "session_id": session_id,
            }

        if "múltiple" in input_text.lower():
            return {
                "response": "Respuesta de múltiples agentes",
                "agents_used": ["agent1", "agent2", "agent3"],
                "agent_responses": [
                    AgentResponse(
                        agent_id="agent1",
                        agent_name="Agent 1",
                        response="R1",
                        confidence=0.9,
                        artifacts=[],
                    ),
                    AgentResponse(
                        agent_id="agent2",
                        agent_name="Agent 2",
                        response="R2",
                        confidence=0.9,
                        artifacts=[],
                    ),
                    AgentResponse(
                        agent_id="agent3",
                        agent_name="Agent 3",
                        response="R3",
                        confidence=0.9,
                        artifacts=[],
                    ),
                ],
                "metadata": {},
                "session_id": session_id,
            }

        if any(
            keyword in input_text.lower()
            for keyword in ["entrenamiento", "fuerza", "potencia", "rutina"]
        ):
            return {
                "response": "Plan de entrenamiento personalizado para ganar fuerza y potencia",
                "agents_used": ["elite_training_strategist"],
                "agent_responses": [
                    AgentResponse(
                        agent_id="elite_training_strategist",
                        agent_name="ETS",
                        response="Plan...",
                        confidence=0.85,
                        artifacts=[],
                    )
                ],
                "metadata": {},
                "session_id": session_id,
            }

        return {
            "response": f"Respuesta simulada para: {input_text}",
            "agents_used": ["agent1"],
            "agent_responses": [
                AgentResponse(
                    agent_id="agent1",
                    agent_name="Agent 1",
                    response=f"Respuesta para {input_text}",
                    confidence=0.8,
                    artifacts=[],
                )
            ],
            "metadata": {},
            "session_id": session_id,
        }

    async def close(self):
        self.is_connected = False
        logger.info("MockNGXNexusOrchestrator closed")


# Configurar el cliente de prueba con la aplicación principal
client = TestClient(app)


@pytest.fixture
def mock_get_current_user():
    """Mockea la dependencia get_current_user."""
    return lambda: TEST_USER_ID  # Devuelve directamente el ID de usuario de prueba


@pytest.fixture
def mock_get_orchestrator(mocker):  # mocker es un fixture de pytest-mock
    """Mockea la dependencia get_orchestrator para que devuelva nuestro MockNGXNexusOrchestrator."""
    # Se instancia el mock aquí para que use los parámetros que get_orchestrator normalmente usaría
    # (a2a_server_url y state_manager), aunque en el mock no los usemos activamente.
    # Esto también permite que el orchestrator mockeado se cree una vez por test si es necesario.
    mock_orch = MockNGXNexusOrchestrator(
        a2a_server_url="ws://mockhost:8000", state_manager=MagicMock()
    )
    return lambda: mock_orch


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch, mock_get_current_user, mock_get_orchestrator):
    """Sobrescribe las dependencias de la app para los tests."""
    from app.routers import chat as chat_router  # Importar el módulo del router

    monkeypatch.setattr(chat_router, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(chat_router, "get_orchestrator", mock_get_orchestrator)
    # Si NGXNexusOrchestrator.connect es llamado por BackgroundTasks y quieres controlarlo:
    # monkeypatch.setattr(MockNGXNexusOrchestrator, 'connect', AsyncMock()) # Ejemplo


# Pruebas


def test_chat_endpoint_success():
    """Prueba que el endpoint /chat/ funciona correctamente."""
    request_data = ChatRequest(
        text="Hola mundo",
        user_id=TEST_USER_ID,  # Puede ser opcional si get_current_user lo provee
        session_id=TEST_SESSION_ID,
    )

    response = client.post(
        "/chat/",  # Ruta del endpoint real
        json=request_data.dict(),  # Usar .dict() para Pydantic models
    )

    assert response.status_code == 200
    data = ChatResponse(**response.json())  # Validar con el Pydantic model
    assert "Respuesta simulada para: Hola mundo" in data.response
    assert "agent1" in data.agents_used
    assert data.session_id == TEST_SESSION_ID


def test_chat_endpoint_error_response():
    """Prueba que el endpoint /chat/ maneja correctamente los errores del orquestador."""
    request_data = ChatRequest(text="provocar error")

    response = client.post("/chat/", json=request_data.dict())

    assert (
        response.status_code == 200
    )  # El endpoint maneja el error y devuelve 200 con error en metadata
    data = ChatResponse(**response.json())
    assert data.response == ""
    assert data.metadata is not None
    assert "error" in data.metadata
    assert data.metadata["error"] == "Error simulado para pruebas"


def test_chat_endpoint_empty_response():
    """Prueba que el endpoint /chat/ maneja correctamente respuestas vacías."""
    request_data = ChatRequest(text="mensaje vacío")

    response = client.post("/chat/", json=request_data.dict())

    assert response.status_code == 200
    data = ChatResponse(**response.json())
    assert data.response == ""
    assert "agent1" in data.agents_used
    assert len(data.agent_responses) == 1
    assert data.agent_responses[0].confidence == 0.7


def test_chat_endpoint_multiple_agents():
    """Prueba que el endpoint /chat/ maneja correctamente respuestas de múltiples agentes."""
    request_data = ChatRequest(text="mensaje múltiple")

    response = client.post("/chat/", json=request_data.dict())

    assert response.status_code == 200
    data = ChatResponse(**response.json())
    assert "Respuesta de múltiples agentes" in data.response
    assert len(data.agents_used) == 3
    assert "agent1" in data.agents_used
    assert "agent2" in data.agents_used
    assert "agent3" in data.agents_used
    assert len(data.agent_responses) == 3


def test_chat_endpoint_elite_training():
    """Prueba que el endpoint /chat/ enruta correctamente los mensajes al agente EliteTrainingStrategist."""
    request_data = ChatRequest(
        text="Necesito un plan de entrenamiento para ganar fuerza y potencia"
    )

    response = client.post("/chat/", json=request_data.dict())

    assert response.status_code == 200
    data = ChatResponse(**response.json())
    assert "Plan de entrenamiento personalizado" in data.response
    assert "elite_training_strategist" in data.agents_used
    assert data.agent_responses[0].confidence == 0.85


def test_chat_endpoint_auth_dependency_error(monkeypatch):
    """Prueba que el endpoint /chat/ maneja errores de la dependencia de autenticación."""
    from app.routers import chat as chat_router

    # Simular que get_current_user lanza una excepción HTTPException
    def mock_auth_exception():
        raise HTTPException(status_code=401, detail="Simulated Auth Error")

    monkeypatch.setattr(chat_router, "get_current_user", mock_auth_exception)

    request_data = ChatRequest(text="Test auth error")
    response = client.post("/chat/", json=request_data.dict())

    assert response.status_code == 401
    assert "Simulated Auth Error" in response.json()["detail"]
