from core.logging_config import get_logger

"""
Script para verificar la conformidad de los agentes con los protocolos A2A y ADK.

Este script analiza todos los agentes registrados y verifica que implementen
correctamente los protocolos oficiales de Agent-to-Agent (A2A) y Agent Development Kit (ADK).
"""
import os
import sys
import inspect
import importlib
import logging
import json
from typing import Dict, Any, Optional
import asyncio

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentes.a2a_agent import A2AAgent
from orchestrator.orchestrator import Orchestrator

# Requisitos de conformidad para A2A
A2A_REQUIRED_METHODS = [
    "run",
    "get_agent_card",
    "_handle_task",
    "execute_task",
    "register",
    "connect",
    "disconnect",
]

# Requisitos de conformidad para ADK
ADK_REQUIRED_FIELDS = [
    "agent_id",
    "name",
    "description",
    "capabilities",
    "version",
]

# Campos requeridos en la respuesta de run()
RUN_RESPONSE_REQUIRED_FIELDS = [
    "status",
    "response",
    "agent_id",
]

logger = get_logger(__name__)


class ProtocolComplianceChecker:
    """
    Verifica la conformidad de los agentes con los protocolos A2A y ADK.
    """

    def __init__(self, agents_dir: str = "agentes", verbose: bool = False):
        """
        Inicializa el verificador de conformidad.

        Args:
            agents_dir: Directorio donde se encuentran los agentes
            verbose: Si es True, muestra información detallada
        """
        self.agents_dir = agents_dir
        self.verbose = verbose
        self.orchestrator = Orchestrator()
        self.agents: Dict[str, A2AAgent] = {}
        self.compliance_results: Dict[str, Dict[str, Any]] = {}

    async def load_agents(self) -> None:
        """
        Carga todos los agentes disponibles en el directorio especificado.
        """
        logger.info(f"Buscando agentes en el directorio: {self.agents_dir}")

        # Obtener la ruta absoluta del directorio de agentes
        agents_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.agents_dir
        )

        if not os.path.exists(agents_path):
            logger.error(f"El directorio {agents_path} no existe")
            return

        # Cargar todos los módulos de Python en el directorio de agentes
        for filename in os.listdir(agents_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]  # Quitar la extensión .py

                try:
                    # Importar el módulo
                    module_path = f"{self.agents_dir}.{module_name}"
                    module = importlib.import_module(module_path)

                    # Buscar clases que hereden de A2AAgent
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, A2AAgent)
                            and obj != A2AAgent
                        ):

                            try:
                                # Instanciar el agente
                                agent = obj()
                                self.agents[agent.agent_id] = agent
                                logger.info(
                                    f"Agente cargado: {agent.agent_id} ({agent.name})"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error al instanciar el agente {name}: {e}"
                                )

                except Exception as e:
                    logger.error(f"Error al cargar el módulo {module_name}: {e}")

        logger.info(f"Total de agentes cargados: {len(self.agents)}")

    def check_a2a_compliance(self, agent: A2AAgent) -> Dict[str, Any]:
        """
        Verifica la conformidad del agente con el protocolo A2A.

        Args:
            agent: Agente a verificar

        Returns:
            Dict[str, Any]: Resultados de la verificación
        """
        results = {
            "compliant": True,
            "missing_methods": [],
            "agent_card_issues": [],
            "other_issues": [],
        }

        # Verificar métodos requeridos
        for method_name in A2A_REQUIRED_METHODS:
            if not hasattr(agent, method_name) or not callable(
                getattr(agent, method_name)
            ):
                results["compliant"] = False
                results["missing_methods"].append(method_name)

        # Verificar Agent Card
        try:
            agent_card = agent.get_agent_card()

            # Verificar que sea un diccionario
            if not isinstance(agent_card, dict):
                results["compliant"] = False
                results["agent_card_issues"].append("Agent Card no es un diccionario")

            # Verificar campos requeridos en Agent Card
            for field in ADK_REQUIRED_FIELDS:
                if field not in agent_card:
                    results["compliant"] = False
                    results["agent_card_issues"].append(
                        f"Campo requerido '{field}' no está presente en Agent Card"
                    )

            # Verificar que las capabilities sean una lista
            if "capabilities" in agent_card and not isinstance(
                agent_card["capabilities"], list
            ):
                results["compliant"] = False
                results["agent_card_issues"].append(
                    "El campo 'capabilities' debe ser una lista"
                )

            # Verificar que el nombre y la descripción no estén vacíos
            if "name" in agent_card and not agent_card["name"]:
                results["compliant"] = False
                results["agent_card_issues"].append(
                    "El campo 'name' no puede estar vacío"
                )

            if "description" in agent_card and not agent_card["description"]:
                results["compliant"] = False
                results["agent_card_issues"].append(
                    "El campo 'description' no puede estar vacío"
                )

        except Exception as e:
            results["compliant"] = False
            results["agent_card_issues"].append(
                f"Error al obtener Agent Card: {str(e)}"
            )

        return results

    async def check_adk_compliance(self, agent: A2AAgent) -> Dict[str, Any]:
        """
        Verifica la conformidad del agente con el protocolo ADK.

        Args:
            agent: Agente a verificar

        Returns:
            Dict[str, Any]: Resultados de la verificación
        """
        results = {
            "compliant": True,
            "missing_fields": [],
            "run_method_issues": [],
            "other_issues": [],
        }

        # Verificar campos requeridos
        for field in ADK_REQUIRED_FIELDS:
            if not hasattr(agent, field) or getattr(agent, field) is None:
                results["compliant"] = False
                results["missing_fields"].append(field)

        # Verificar método run()
        if hasattr(agent, "run") and callable(getattr(agent, "run")):
            try:
                # Ejecutar el método run con un input de prueba
                response = await agent.run(
                    "Este es un mensaje de prueba para verificar la conformidad con ADK."
                )

                # Verificar que la respuesta sea un diccionario
                if not isinstance(response, dict):
                    results["compliant"] = False
                    results["run_method_issues"].append(
                        "La respuesta de run() no es un diccionario"
                    )

                # Verificar campos requeridos en la respuesta
                for field in RUN_RESPONSE_REQUIRED_FIELDS:
                    if field not in response:
                        results["compliant"] = False
                        results["run_method_issues"].append(
                            f"Campo requerido '{field}' no está presente en la respuesta de run()"
                        )

                # Verificar que el campo status sea "success" o "error"
                if "status" in response and response["status"] not in [
                    "success",
                    "error",
                ]:
                    results["compliant"] = False
                    results["run_method_issues"].append(
                        "El campo 'status' debe ser 'success' o 'error'"
                    )

                # Verificar que el campo agent_id coincida con el ID del agente
                if "agent_id" in response and response["agent_id"] != agent.agent_id:
                    results["compliant"] = False
                    results["run_method_issues"].append(
                        "El campo 'agent_id' en la respuesta no coincide con el ID del agente"
                    )

            except Exception as e:
                results["compliant"] = False
                results["run_method_issues"].append(
                    f"Error al ejecutar run(): {str(e)}"
                )
        else:
            results["compliant"] = False
            results["run_method_issues"].append("Método run() no implementado")

        return results

    async def check_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Verifica la conformidad de todos los agentes cargados.

        Returns:
            Dict[str, Dict[str, Any]]: Resultados de la verificación para cada agente
        """
        if not self.agents:
            await self.load_agents()

        for agent_id, agent in self.agents.items():
            logger.info(f"Verificando conformidad del agente: {agent_id}")

            # Verificar conformidad con A2A
            a2a_results = self.check_a2a_compliance(agent)

            # Verificar conformidad con ADK
            adk_results = await self.check_adk_compliance(agent)

            # Combinar resultados
            self.compliance_results[agent_id] = {
                "agent_name": agent.name,
                "agent_description": agent.description,
                "a2a_compliant": a2a_results["compliant"],
                "adk_compliant": adk_results["compliant"],
                "overall_compliant": a2a_results["compliant"]
                and adk_results["compliant"],
                "a2a_results": a2a_results,
                "adk_results": adk_results,
            }

            # Mostrar resultados si verbose es True
            if self.verbose:
                logger.info(f"Resultados para {agent_id}:")
                logger.info(f"  A2A compliant: {a2a_results['compliant']}")
                logger.info(f"  ADK compliant: {adk_results['compliant']}")
                logger.info(
                    f"  Overall compliant: {a2a_results['compliant'] and adk_results['compliant']}"
                )

                if not a2a_results["compliant"]:
                    logger.info(f"  A2A issues:")
                    if a2a_results["missing_methods"]:
                        logger.info(
                            f"    Missing methods: {', '.join(a2a_results['missing_methods'])}"
                        )
                    if a2a_results["agent_card_issues"]:
                        logger.info(
                            f"    Agent Card issues: {', '.join(a2a_results['agent_card_issues'])}"
                        )
                    if a2a_results["other_issues"]:
                        logger.info(
                            f"    Other issues: {', '.join(a2a_results['other_issues'])}"
                        )

                if not adk_results["compliant"]:
                    logger.info(f"  ADK issues:")
                    if adk_results["missing_fields"]:
                        logger.info(
                            f"    Missing fields: {', '.join(adk_results['missing_fields'])}"
                        )
                    if adk_results["run_method_issues"]:
                        logger.info(
                            f"    Run method issues: {', '.join(adk_results['run_method_issues'])}"
                        )
                    if adk_results["other_issues"]:
                        logger.info(
                            f"    Other issues: {', '.join(adk_results['other_issues'])}"
                        )

        return self.compliance_results

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Genera un informe de conformidad en formato JSON.

        Args:
            output_file: Ruta del archivo donde guardar el informe (opcional)

        Returns:
            str: Informe en formato JSON
        """
        if not self.compliance_results:
            logger.warning(
                "No hay resultados de conformidad disponibles. Ejecute check_all_agents() primero."
            )
            return "{}"

        # Calcular estadísticas
        total_agents = len(self.compliance_results)
        a2a_compliant = sum(
            1 for result in self.compliance_results.values() if result["a2a_compliant"]
        )
        adk_compliant = sum(
            1 for result in self.compliance_results.values() if result["adk_compliant"]
        )
        overall_compliant = sum(
            1
            for result in self.compliance_results.values()
            if result["overall_compliant"]
        )

        # Crear informe
        report = {
            "summary": {
                "total_agents": total_agents,
                "a2a_compliant": a2a_compliant,
                "adk_compliant": adk_compliant,
                "overall_compliant": overall_compliant,
                "a2a_compliance_rate": (
                    a2a_compliant / total_agents if total_agents > 0 else 0
                ),
                "adk_compliance_rate": (
                    adk_compliant / total_agents if total_agents > 0 else 0
                ),
                "overall_compliance_rate": (
                    overall_compliant / total_agents if total_agents > 0 else 0
                ),
            },
            "agents": self.compliance_results,
        }

        # Convertir a JSON
        report_json = json.dumps(report, indent=2)

        # Guardar en archivo si se especifica
        if output_file:
            try:
                with open(output_file, "w") as f:
                    f.write(report_json)
                logger.info(f"Informe guardado en: {output_file}")
            except Exception as e:
                logger.error(f"Error al guardar el informe: {e}")

        return report_json


async def main():
    """
    Función principal para ejecutar el verificador de conformidad.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Verificador de conformidad con protocolos A2A y ADK"
    )
    parser.add_argument(
        "--agents-dir",
        default="agentes",
        help="Directorio donde se encuentran los agentes",
    )
    parser.add_argument("--output", help="Archivo donde guardar el informe")
    parser.add_argument(
        "--verbose", action="store_true", help="Mostrar información detallada"
    )

    args = parser.parse_args()

    checker = ProtocolComplianceChecker(
        agents_dir=args.agents_dir, verbose=args.verbose
    )
    await checker.load_agents()
    await checker.check_all_agents()

    report = checker.generate_report(output_file=args.output)

    if not args.output:
        logger.info(report)


if __name__ == "__main__":
    asyncio.run(main())
