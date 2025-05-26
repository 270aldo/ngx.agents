"""
Pruebas unitarias para el adaptador de Recovery Corrective.
"""

import pytest
from unittest.mock import AsyncMock, patch

from infrastructure.adapters.recovery_corrective_adapter import (
    RecoveryCorrectiveAdapter,
)


@pytest.fixture
def mock_a2a_client():
    """Fixture para crear un mock del cliente A2A."""
    mock = AsyncMock()
    mock.call_agent = AsyncMock()
    mock.call_multiple_agents = AsyncMock()
    return mock


@pytest.fixture
def mock_vertex_client():
    """Fixture para crear un mock del cliente Vertex AI."""
    mock = AsyncMock()
    mock.generate_text = AsyncMock()
    return mock


@pytest.fixture
async def recovery_adapter(mock_a2a_client):
    """Fixture para crear una instancia del adaptador con mocks."""
    with patch("clients.vertex_ai.vertex_ai_client") as mock_vertex_client:
        mock_vertex_client.is_initialized = True
        return RecoveryCorrectiveAdapter(mock_a2a_client)


@pytest.mark.asyncio
async def test_create_method():
    """Prueba el método de fábrica create()."""
    with patch(
        "infrastructure.adapters.a2a_adapter.A2AAdapter.create", new_callable=AsyncMock
    ) as mock_a2a_create:
        with patch("clients.vertex_ai.vertex_ai_client") as mock_vertex_client:
            # Configurar mocks
            mock_a2a_create.return_value = AsyncMock()
            mock_vertex_client.is_initialized = False
            mock_vertex_client.initialize = AsyncMock()

            # Llamar al método create
            adapter = await RecoveryCorrectiveAdapter.create()

            # Verificar que se llamaron los métodos correctos
            mock_a2a_create.assert_called_once()
            mock_vertex_client.initialize.assert_called_once()

            # Verificar que el adaptador se creó correctamente
            assert isinstance(adapter, RecoveryCorrectiveAdapter)
            assert adapter.a2a_client == mock_a2a_create.return_value
            assert adapter.vertex_client == mock_vertex_client_class.return_value


@pytest.mark.asyncio
async def test_analyze_recovery_needs(recovery_adapter, mock_vertex_client):
    """Prueba el método analyze_recovery_needs()."""
    # Configurar mock
    mock_vertex_client.generate_text.return_value = "Respuesta simulada del modelo"

    # Datos de prueba
    user_data = {"user_id": "test_user", "age": 30, "weight": 75}
    training_history = [{"date": "2025-10-01", "type": "strength", "intensity": "high"}]

    # Configurar mock para _parse_recovery_analysis
    with patch.object(recovery_adapter, "_parse_recovery_analysis") as mock_parse:
        mock_parse.return_value = {
            "factors": ["factor1", "factor2"],
            "priority_areas": ["area1", "area2"],
            "recommendations": ["rec1", "rec2"],
            "fatigue_level": "medio",
            "recovery_time": 2,
        }

        # Llamar al método
        result = await recovery_adapter.analyze_recovery_needs(
            user_data, training_history
        )

        # Verificar que se llamaron los métodos correctos
        mock_vertex_client.generate_text.assert_called_once()
        mock_parse.assert_called_once_with("Respuesta simulada del modelo")

        # Verificar el resultado
        assert result == mock_parse.return_value
        assert "factors" in result
        assert len(result["factors"]) == 2
        assert result["fatigue_level"] == "medio"


@pytest.mark.asyncio
async def test_generate_recovery_plan(
    recovery_adapter, mock_a2a_client, mock_vertex_client
):
    """Prueba el método generate_recovery_plan()."""
    # Configurar mocks
    mock_a2a_client.call_agent.side_effect = [
        {
            "recommendations": ["nutrición1", "nutrición2"]
        },  # Respuesta del agente de nutrición
        {
            "recommendations": ["entrenamiento1", "entrenamiento2"]
        },  # Respuesta del agente de entrenamiento
    ]
    mock_vertex_client.generate_text.return_value = "Plan de recuperación simulado"

    # Datos de prueba
    recovery_needs = {"user_id": "test_user", "factors": ["factor1", "factor2"]}
    user_preferences = {"diet": "vegetarian", "recovery_focus": "active"}

    # Configurar mock para _parse_recovery_plan
    with patch.object(recovery_adapter, "_parse_recovery_plan") as mock_parse:
        mock_parse.return_value = {
            "components": ["comp1", "comp2"],
            "duration_days": 3,
            "intensity": "moderada",
        }

        # Llamar al método
        result = await recovery_adapter.generate_recovery_plan(
            recovery_needs, user_preferences
        )

        # Verificar que se llamaron los métodos correctos
        assert mock_a2a_client.call_agent.call_count == 2
        mock_vertex_client.generate_text.assert_called_once()
        mock_parse.assert_called_once_with("Plan de recuperación simulado")

        # Verificar el resultado
        assert result == mock_parse.return_value
        assert "components" in result
        assert result["duration_days"] == 3


@pytest.mark.asyncio
async def test_adjust_training_program(
    recovery_adapter, mock_a2a_client, mock_vertex_client
):
    """Prueba el método adjust_training_program()."""
    # Configurar mocks
    mock_a2a_client.call_agent.return_value = {"adjustments": ["ajuste1", "ajuste2"]}
    mock_vertex_client.generate_text.return_value = "Programa ajustado simulado"

    # Datos de prueba
    current_program = {
        "user_id": "test_user",
        "sessions": [{"day": "lunes", "type": "strength"}],
    }
    recovery_plan = {"components": ["comp1", "comp2"], "duration_days": 3}

    # Configurar mock para _parse_adjusted_program
    with patch.object(recovery_adapter, "_parse_adjusted_program") as mock_parse:
        mock_parse.return_value = {
            "adjustment_level": "moderado",
            "modified_sessions": 3,
            "intensity_reduction": "20%",
        }

        # Llamar al método
        result = await recovery_adapter.adjust_training_program(
            current_program, recovery_plan
        )

        # Verificar que se llamaron los métodos correctos
        mock_a2a_client.call_agent.assert_called_once()
        mock_vertex_client.generate_text.assert_called_once()
        mock_parse.assert_called_once_with("Programa ajustado simulado")

        # Verificar el resultado
        assert result == mock_parse.return_value
        assert result["adjustment_level"] == "moderado"
        assert result["modified_sessions"] == 3


@pytest.mark.asyncio
async def test_provide_recovery_guidance(recovery_adapter):
    """Prueba el método provide_recovery_guidance()."""
    # Configurar mocks para los métodos internos
    with patch.object(recovery_adapter, "_get_user_data") as mock_get_user_data:
        with patch.object(
            recovery_adapter, "_get_training_history"
        ) as mock_get_training_history:
            with patch.object(
                recovery_adapter, "analyze_recovery_needs"
            ) as mock_analyze:
                with patch.object(
                    recovery_adapter, "_build_guidance_prompt"
                ) as mock_build_prompt:
                    with patch.object(
                        recovery_adapter, "_parse_guidance"
                    ) as mock_parse:
                        with patch.object(
                            recovery_adapter.vertex_client, "generate_text"
                        ) as mock_generate:
                            # Configurar valores de retorno
                            mock_get_user_data.return_value = {
                                "user_id": "test_user",
                                "age": 30,
                            }
                            mock_get_training_history.return_value = [
                                {"date": "2025-10-01", "type": "strength"}
                            ]
                            mock_analyze.return_value = {
                                "factors": ["factor1"],
                                "fatigue_level": "medio",
                            }
                            mock_build_prompt.return_value = "Prompt de orientación"
                            mock_generate.return_value = "Orientación simulada"
                            mock_parse.return_value = {
                                "type": "inmediata",
                                "actions": ["acción1", "acción2"],
                                "urgency": "media",
                            }

                            # Llamar al método
                            result = await recovery_adapter.provide_recovery_guidance(
                                "test_user"
                            )

                            # Verificar que se llamaron los métodos correctos
                            mock_get_user_data.assert_called_once_with("test_user")
                            mock_get_training_history.assert_called_once_with(
                                "test_user"
                            )
                            mock_analyze.assert_called_once()
                            mock_build_prompt.assert_called_once()
                            mock_generate.assert_called_once_with(
                                "Prompt de orientación"
                            )
                            mock_parse.assert_called_once_with("Orientación simulada")

                            # Verificar el resultado
                            assert result == mock_parse.return_value
                            assert result["type"] == "inmediata"
                            assert len(result["actions"]) == 2


@pytest.mark.asyncio
async def test_consult_other_agent(recovery_adapter, mock_a2a_client):
    """Prueba el método _consult_other_agent()."""
    # Configurar mock
    mock_a2a_client.call_agent.return_value = {"response": "Respuesta del agente"}

    # Llamar al método
    result = await recovery_adapter._consult_other_agent(
        "test_agent", "consulta de prueba"
    )

    # Verificar que se llamó al método correcto
    mock_a2a_client.call_agent.assert_called_once_with(
        "test_agent", "consulta de prueba", None
    )

    # Verificar el resultado
    assert result == {"response": "Respuesta del agente"}


@pytest.mark.asyncio
async def test_consult_other_agent_with_error(recovery_adapter, mock_a2a_client):
    """Prueba el método _consult_other_agent() cuando ocurre un error."""
    # Configurar mock para lanzar una excepción
    mock_a2a_client.call_agent.side_effect = Exception("Error de prueba")

    # Llamar al método
    result = await recovery_adapter._consult_other_agent(
        "test_agent", "consulta de prueba"
    )

    # Verificar que se llamó al método correcto
    mock_a2a_client.call_agent.assert_called_once_with(
        "test_agent", "consulta de prueba", None
    )

    # Verificar el resultado de fallback
    assert result["status"] == "error"
    assert "Failed to consult test_agent" in result["message"]


@pytest.mark.asyncio
async def test_get_user_data(recovery_adapter):
    """Prueba el método _get_user_data()."""
    # Llamar al método
    result = await recovery_adapter._get_user_data("test_user")

    # Verificar el resultado
    assert result is not None
    assert result["user_id"] == "test_user"
    assert "age" in result
    assert "weight" in result
    assert "height" in result


@pytest.mark.asyncio
async def test_get_training_history(recovery_adapter):
    """Prueba el método _get_training_history()."""
    # Llamar al método
    result = await recovery_adapter._get_training_history("test_user")

    # Verificar el resultado
    assert result is not None
    assert isinstance(result, list)
    assert len(result) > 0
    assert "date" in result[0]
    assert "type" in result[0]
    assert "intensity" in result[0]


def test_build_recovery_analysis_prompt(recovery_adapter):
    """Prueba el método _build_recovery_analysis_prompt()."""
    # Datos de prueba
    user_data = {"user_id": "test_user", "age": 30}
    training_history = [{"date": "2025-10-01", "type": "strength"}]

    # Llamar al método
    result = recovery_adapter._build_recovery_analysis_prompt(
        user_data, training_history
    )

    # Verificar el resultado
    assert result is not None
    assert isinstance(result, str)
    assert "Analiza las necesidades de recuperación" in result
    assert str(user_data) in result
    assert str(training_history) in result


def test_parse_recovery_analysis(recovery_adapter):
    """Prueba el método _parse_recovery_analysis()."""
    # Datos de prueba
    response = "Respuesta simulada del modelo"

    # Llamar al método
    result = recovery_adapter._parse_recovery_analysis(response)

    # Verificar el resultado
    assert result is not None
    assert "factors" in result
    assert "priority_areas" in result
    assert "recommendations" in result
    assert "fatigue_level" in result
    assert "recovery_time" in result
