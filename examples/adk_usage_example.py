"""
Ejemplo de uso de la integración con Google ADK oficial.

Este script muestra cómo utilizar la integración con Google ADK
para crear un agente simple con skills personalizadas.
"""

import asyncio
import logging
from typing import Dict, Any

from adk.agent import Agent, Skill
from adk.toolkit import Toolkit

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Definir una skill de saludo
async def greeting_skill_handler(name: str = "Usuario") -> str:
    """
    Skill que genera un saludo personalizado.

    Args:
        name: Nombre del usuario (opcional, por defecto "Usuario")

    Returns:
        Saludo personalizado
    """
    return f"¡Hola, {name}! Bienvenido al sistema NGX Agents."


# Definir una skill de cálculo
async def calculator_skill_handler(
    operation: str, a: float, b: float
) -> Dict[str, Any]:
    """
    Skill que realiza operaciones matemáticas básicas.

    Args:
        operation: Operación a realizar (suma, resta, multiplicación, división)
        a: Primer operando
        b: Segundo operando

    Returns:
        Resultado de la operación
    """
    operation = operation.lower()
    result = None

    if operation == "suma":
        result = a + b
    elif operation == "resta":
        result = a - b
    elif operation == "multiplicacion" or operation == "multiplicación":
        result = a * b
    elif operation == "division" or operation == "división":
        if b == 0:
            return {"error": "No se puede dividir por cero"}
        result = a / b
    else:
        return {"error": f"Operación '{operation}' no soportada"}

    return {"operation": operation, "a": a, "b": b, "result": result}


async def main():
    """Función principal que demuestra el uso de Google ADK."""
    try:
        # Crear un toolkit
        toolkit = Toolkit()
        logger.info("Toolkit creado")

        # Crear skills
        greeting_skill = Skill(
            name="greeting",
            description="Genera un saludo personalizado",
            handler=greeting_skill_handler,
        )

        calculator_skill = Skill(
            name="calculator",
            description="Realiza operaciones matemáticas básicas",
            handler=calculator_skill_handler,
        )

        # Registrar skills en el toolkit
        if hasattr(toolkit, "register_skill"):
            toolkit.register_skill(greeting_skill)
            toolkit.register_skill(calculator_skill)
            logger.info("Skills registradas en el toolkit")
        elif hasattr(toolkit, "add_tool"):
            toolkit.add_tool(greeting_skill)
            toolkit.add_tool(calculator_skill)
            logger.info("Skills añadidas como herramientas al toolkit")

        # Crear un agente
        agent = Agent(
            toolkit=toolkit,
            name="ExampleAgent",
            description="Agente de ejemplo para demostrar la integración con Google ADK",
        )
        logger.info("Agente creado")

        # Ejecutar skills a través del toolkit
        if hasattr(toolkit, "execute_skill"):
            # Ejecutar skill de saludo
            greeting_result = await toolkit.execute_skill("greeting", name="María")
            logger.info(f"Resultado de greeting: {greeting_result}")

            # Ejecutar skill de calculadora
            calculator_result = await toolkit.execute_skill(
                "calculator", operation="suma", a=5, b=3
            )
            logger.info(f"Resultado de calculator: {calculator_result}")
        else:
            # Si no hay método execute_skill, llamar directamente a las skills
            greeting_result = await greeting_skill(name="María")
            logger.info(f"Resultado de greeting: {greeting_result}")

            calculator_result = await calculator_skill(operation="suma", a=5, b=3)
            logger.info(f"Resultado de calculator: {calculator_result}")

        # Ejecutar el agente (si implementa run)
        if hasattr(agent, "run"):
            agent_result = await agent.run("Hola, ¿cómo estás?")
            logger.info(f"Resultado del agente: {agent_result}")

    except ImportError as e:
        logger.warning(f"No se pudo importar la biblioteca oficial de Google ADK: {e}")
        logger.info("Usando stubs locales como fallback")
    except Exception as e:
        logger.error(f"Error en el ejemplo: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
