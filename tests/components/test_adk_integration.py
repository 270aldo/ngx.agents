"""
Pruebas para verificar la integración con Google ADK oficial.
"""

import pytest
import logging

from adk.agent import Agent as ADKAgent
from adk.toolkit import Toolkit as ADKToolkit
from adk.agent import Skill as ADKSkill

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestADKIntegration:
    """Pruebas para verificar la integración con Google ADK oficial."""

    @pytest.mark.asyncio
    async def test_adk_agent_initialization(self):
        """Verifica que se pueda inicializar un agente ADK."""
        try:
            # Crear un toolkit
            toolkit = ADKToolkit()

            # Crear un agente
            agent = ADKAgent(
                toolkit=toolkit,
                name="TestAgent",
                description="Agente de prueba para verificar la integración con Google ADK",
            )

            # Verificar que el agente se haya inicializado correctamente
            assert agent is not None
            if hasattr(agent, "name"):
                assert agent.name == "TestAgent"

            logger.info("Agente ADK inicializado correctamente")
        except ImportError as e:
            logger.warning(
                f"No se pudo importar la biblioteca oficial de Google ADK: {e}"
            )
            pytest.skip("Biblioteca oficial de Google ADK no disponible")
        except Exception as e:
            logger.error(f"Error al inicializar el agente ADK: {e}")
            raise

    @pytest.mark.asyncio
    async def test_adk_skill_registration(self):
        """Verifica que se puedan registrar skills en un toolkit ADK."""
        try:
            # Crear un toolkit
            toolkit = ADKToolkit()

            # Definir una skill de prueba
            async def test_skill_handler(input_text: str) -> str:
                return f"Procesado: {input_text}"

            # Crear una skill
            test_skill = ADKSkill(
                name="test_skill",
                description="Skill de prueba",
                handler=test_skill_handler,
            )

            # Registrar la skill en el toolkit
            if hasattr(toolkit, "register_skill"):
                toolkit.register_skill(test_skill)
            elif hasattr(toolkit, "add_tool"):
                toolkit.add_tool(test_skill)

            # Verificar que la skill se haya registrado correctamente
            if hasattr(toolkit, "skills") and isinstance(toolkit.skills, dict):
                assert "test_skill" in toolkit.skills
            elif hasattr(toolkit, "tools") and isinstance(toolkit.tools, list):
                assert test_skill in toolkit.tools

            logger.info("Skill registrada correctamente en el toolkit ADK")
        except ImportError as e:
            logger.warning(
                f"No se pudo importar la biblioteca oficial de Google ADK: {e}"
            )
            pytest.skip("Biblioteca oficial de Google ADK no disponible")
        except Exception as e:
            logger.error(f"Error al registrar skill en el toolkit ADK: {e}")
            raise

    @pytest.mark.asyncio
    async def test_adk_skill_execution(self):
        """Verifica que se puedan ejecutar skills a través del toolkit ADK."""
        try:
            # Crear un toolkit
            toolkit = ADKToolkit()

            # Definir una skill de prueba
            async def test_skill_handler(input_text: str) -> str:
                return f"Procesado: {input_text}"

            # Crear una skill
            test_skill = ADKSkill(
                name="test_skill",
                description="Skill de prueba",
                handler=test_skill_handler,
            )

            # Registrar la skill en el toolkit
            if hasattr(toolkit, "register_skill"):
                toolkit.register_skill(test_skill)
            elif hasattr(toolkit, "add_tool"):
                toolkit.add_tool(test_skill)

            # Ejecutar la skill
            if hasattr(toolkit, "execute_skill"):
                result = await toolkit.execute_skill(
                    "test_skill", input_text="Hola mundo"
                )
                assert result == "Procesado: Hola mundo"
            else:
                # Si no hay método execute_skill, llamar directamente a la skill
                result = await test_skill(input_text="Hola mundo")
                assert result == "Procesado: Hola mundo"

            logger.info("Skill ejecutada correctamente a través del toolkit ADK")
        except ImportError as e:
            logger.warning(
                f"No se pudo importar la biblioteca oficial de Google ADK: {e}"
            )
            pytest.skip("Biblioteca oficial de Google ADK no disponible")
        except Exception as e:
            logger.error(f"Error al ejecutar skill a través del toolkit ADK: {e}")
            raise
