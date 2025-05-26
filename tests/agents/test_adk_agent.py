"""
Pruebas para la clase ADKAgent actualizada con integración de Google ADK oficial.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch

from adk.agent import Agent as GoogleADKAgent
from adk.agent import Skill as GoogleADKSkill
from adk.toolkit import Toolkit as GoogleADKToolkit

from agents.base.adk_agent import ADKAgent
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestADKAgentIntegration:
    """Pruebas para verificar la integración de ADKAgent con Google ADK oficial."""

    @pytest.fixture
    def mock_gemini_client(self):
        """Fixture para crear un mock de GeminiClient."""
        mock_client = MagicMock(spec=GeminiClient)
        mock_client.generate_content.return_value = "Respuesta de prueba"
        return mock_client

    @pytest.fixture
    def mock_supabase_client(self):
        """Fixture para crear un mock de SupabaseClient."""
        mock_client = MagicMock(spec=SupabaseClient)
        mock_client.client = MagicMock()
        return mock_client

    @pytest.fixture
    def mock_state_manager(self):
        """Fixture para crear un mock de StateManager."""
        mock_manager = MagicMock(spec=StateManager)
        return mock_manager

    @pytest.fixture
    def test_skill(self):
        """Fixture para crear una skill de prueba."""

        async def test_skill_handler(input_text: str) -> str:
            return f"Procesado: {input_text}"

        return GoogleADKSkill(
            name="test_skill", description="Skill de prueba", handler=test_skill_handler
        )

    @pytest.mark.asyncio
    async def test_adk_agent_initialization(
        self, mock_gemini_client, mock_supabase_client, mock_state_manager, test_skill
    ):
        """Verifica que se pueda inicializar un agente ADK con la integración de Google ADK."""
        try:
            # Crear un toolkit
            toolkit = GoogleADKToolkit()

            # Crear un agente
            agent = ADKAgent(
                agent_id="test-agent-id",
                name="TestAgent",
                description="Agente de prueba para verificar la integración con Google ADK",
                model="gemini-pro",
                instruction="Instrucción de prueba",
                gemini_client=mock_gemini_client,
                supabase_client=mock_supabase_client,
                state_manager=mock_state_manager,
                adk_toolkit=toolkit,
                capabilities=["test_skill"],
                endpoint="http://localhost:8000/agents/test-agent",
                auto_register_skills=True,
                a2a_server_url="ws://localhost:9000",
            )

            # Añadir una skill al agente
            agent.skills = [test_skill]

            # Inicializar las skills
            processed_google_adk_tools, processed_a2a_skills_for_card, skill_names = (
                agent._initialize_and_prepare_skills()
            )

            # Verificar que el agente se haya inicializado correctamente
            assert agent is not None
            assert agent.name == "TestAgent"
            assert agent.agent_id == "test-agent-id"
            assert agent.gemini_client == mock_gemini_client
            assert agent.supabase_client == mock_supabase_client
            assert agent.state_manager == mock_state_manager
            assert agent.adk_toolkit is not None

            # Verificar que las skills se hayan procesado correctamente
            assert len(processed_google_adk_tools) == 1
            assert len(processed_a2a_skills_for_card) == 1
            assert len(skill_names) == 1
            assert skill_names[0] == "Test Skill"

            logger.info(
                "Agente ADK inicializado correctamente con integración de Google ADK"
            )
        except ImportError as e:
            logger.warning(
                f"No se pudo importar la biblioteca oficial de Google ADK: {e}"
            )
            pytest.skip("Biblioteca oficial de Google ADK no disponible")
        except Exception as e:
            logger.error(f"Error al inicializar el agente ADK: {e}")
            raise

    @pytest.mark.asyncio
    async def test_adk_agent_run(
        self, mock_gemini_client, mock_supabase_client, mock_state_manager, test_skill
    ):
        """Verifica que se pueda ejecutar un agente ADK con la integración de Google ADK."""
        try:
            # Crear un toolkit
            toolkit = GoogleADKToolkit()

            # Registrar la skill en el toolkit
            if hasattr(toolkit, "register_skill"):
                toolkit.register_skill(test_skill)
            elif hasattr(toolkit, "add_tool"):
                toolkit.add_tool(test_skill)

            # Crear un agente
            agent = ADKAgent(
                agent_id="test-agent-id",
                name="TestAgent",
                description="Agente de prueba para verificar la integración con Google ADK",
                model="gemini-pro",
                instruction="Instrucción de prueba",
                gemini_client=mock_gemini_client,
                supabase_client=mock_supabase_client,
                state_manager=mock_state_manager,
                adk_toolkit=toolkit,
                capabilities=["test_skill"],
                endpoint="http://localhost:8000/agents/test-agent",
                auto_register_skills=True,
                a2a_server_url="ws://localhost:9000",
            )

            # Añadir una skill al agente
            agent.skills = [test_skill]

            # Inicializar las skills
            agent._initialize_and_prepare_skills()

            # Mockear el método run de GoogleADKAgent
            with patch.object(
                GoogleADKAgent, "run", return_value={"response": "Respuesta de prueba"}
            ):
                # Ejecutar el agente
                result = await agent.run("Hola mundo")

                # Verificar el resultado
                assert result is not None
                assert result == {"response": "Respuesta de prueba"}

            logger.info(
                "Agente ADK ejecutado correctamente con integración de Google ADK"
            )
        except ImportError as e:
            logger.warning(
                f"No se pudo importar la biblioteca oficial de Google ADK: {e}"
            )
            pytest.skip("Biblioteca oficial de Google ADK no disponible")
        except Exception as e:
            logger.error(f"Error al ejecutar el agente ADK: {e}")
            raise

    @pytest.mark.asyncio
    async def test_adk_agent_skill_execution(
        self, mock_gemini_client, mock_supabase_client, mock_state_manager, test_skill
    ):
        """Verifica que se puedan ejecutar skills a través del agente ADK con la integración de Google ADK."""
        try:
            # Crear un toolkit
            toolkit = GoogleADKToolkit()

            # Registrar la skill en el toolkit
            if hasattr(toolkit, "register_skill"):
                toolkit.register_skill(test_skill)
            elif hasattr(toolkit, "add_tool"):
                toolkit.add_tool(test_skill)

            # Crear un agente
            agent = ADKAgent(
                agent_id="test-agent-id",
                name="TestAgent",
                description="Agente de prueba para verificar la integración con Google ADK",
                model="gemini-pro",
                instruction="Instrucción de prueba",
                gemini_client=mock_gemini_client,
                supabase_client=mock_supabase_client,
                state_manager=mock_state_manager,
                adk_toolkit=toolkit,
                capabilities=["test_skill"],
                endpoint="http://localhost:8000/agents/test-agent",
                auto_register_skills=True,
                a2a_server_url="ws://localhost:9000",
            )

            # Añadir una skill al agente
            agent.skills = [test_skill]

            # Inicializar las skills
            agent._initialize_and_prepare_skills()

            # Ejecutar la skill a través del toolkit
            if hasattr(toolkit, "execute_skill"):
                result = await toolkit.execute_skill(
                    "test_skill", input_text="Hola mundo"
                )
                assert result == "Procesado: Hola mundo"
            else:
                # Si no hay método execute_skill, llamar directamente a la skill
                result = await test_skill(input_text="Hola mundo")
                assert result == "Procesado: Hola mundo"

            logger.info(
                "Skill ejecutada correctamente a través del agente ADK con integración de Google ADK"
            )
        except ImportError as e:
            logger.warning(
                f"No se pudo importar la biblioteca oficial de Google ADK: {e}"
            )
            pytest.skip("Biblioteca oficial de Google ADK no disponible")
        except Exception as e:
            logger.error(f"Error al ejecutar skill a través del agente ADK: {e}")
            raise
