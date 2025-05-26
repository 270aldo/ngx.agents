"""
Ejecutor de Runbooks Automatizados para NGX Agents.

Este módulo proporciona la implementación del ejecutor de runbooks,
que permite cargar y ejecutar procedimientos operativos automatizados
definidos en formato YAML.
"""

import os
import yaml
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from infrastructure.adapters import get_telemetry_adapter
from tools.pagerduty_tools import PagerDutyClient


# Configurar logger
logger = logging.getLogger(__name__)


class RunbookExecutor:
    """
    Ejecutor de runbooks automatizados.

    Esta clase proporciona métodos para cargar y ejecutar runbooks
    definidos en formato YAML, registrando su ejecución y resultados.
    """

    def __init__(
        self,
        runbooks_dir: Optional[str] = None,
        telemetry_adapter=None,
        pagerduty_client=None,
    ):
        """
        Inicializa el ejecutor de runbooks.

        Args:
            runbooks_dir: Directorio donde se encuentran los runbooks.
                          Si no se proporciona, se utilizará tools/runbooks/templates.
            telemetry_adapter: Adaptador de telemetría opcional.
            pagerduty_client: Cliente de PagerDuty opcional.
        """
        self.runbooks_dir = runbooks_dir or os.path.join(
            os.path.dirname(__file__), "templates"
        )
        self.telemetry = telemetry_adapter or get_telemetry_adapter()
        self.pagerduty_client = pagerduty_client or PagerDutyClient()

        # Registro de ejecuciones
        self.executions = {}

        # Registro de comandos disponibles
        self._register_commands()

    def _register_commands(self):
        """Registra los comandos disponibles para los runbooks."""
        self.commands = {
            "check_metric": self._cmd_check_metric,
            "check_health": self._cmd_check_health,
            "restart_service": self._cmd_restart_service,
            "scale_service": self._cmd_scale_service,
            "notify": self._cmd_notify,
            "wait": self._cmd_wait,
            "execute_query": self._cmd_execute_query,
            "check_logs": self._cmd_check_logs,
            "run_command": self._cmd_run_command,
            "toggle_feature_flag": self._cmd_toggle_feature_flag,
        }

    async def list_runbooks(self) -> List[Dict[str, Any]]:
        """
        Lista todos los runbooks disponibles.

        Returns:
            List[Dict[str, Any]]: Lista de runbooks con sus metadatos.
        """
        span = self.telemetry.start_span("runbooks.list_runbooks")

        try:
            result = []

            # Listar archivos YAML en el directorio de runbooks
            for filename in os.listdir(self.runbooks_dir):
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    filepath = os.path.join(self.runbooks_dir, filename)

                    try:
                        # Cargar metadatos del runbook
                        with open(filepath, "r") as f:
                            runbook = yaml.safe_load(f)

                        result.append(
                            {
                                "id": os.path.splitext(filename)[0],
                                "name": runbook.get("name", ""),
                                "description": runbook.get("description", ""),
                                "tags": runbook.get("tags", []),
                                "severity": runbook.get("severity", ""),
                                "steps_count": len(runbook.get("steps", [])),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Error al cargar runbook {filename}: {str(e)}")

            return result
        except Exception as e:
            self.telemetry.record_exception(span, e)
            logger.error(f"Error al listar runbooks: {str(e)}")
            return []
        finally:
            self.telemetry.end_span(span)

    async def get_runbook(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la definición de un runbook.

        Args:
            runbook_id: ID del runbook.

        Returns:
            Optional[Dict[str, Any]]: Definición del runbook, o None si no existe.
        """
        span = self.telemetry.start_span(
            "runbooks.get_runbook", {"runbook_id": runbook_id}
        )

        try:
            # Construir ruta del archivo
            filepath = os.path.join(self.runbooks_dir, f"{runbook_id}.yaml")

            # Verificar si existe
            if not os.path.exists(filepath):
                filepath = os.path.join(self.runbooks_dir, f"{runbook_id}.yml")
                if not os.path.exists(filepath):
                    return None

            # Cargar runbook
            with open(filepath, "r") as f:
                runbook = yaml.safe_load(f)

            return runbook
        except Exception as e:
            self.telemetry.record_exception(span, e)
            logger.error(f"Error al obtener runbook {runbook_id}: {str(e)}")
            return None
        finally:
            self.telemetry.end_span(span)

    async def execute_runbook(
        self, runbook_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un runbook.

        Args:
            runbook_id: ID del runbook a ejecutar.
            context: Contexto inicial para la ejecución.

        Returns:
            Dict[str, Any]: Resultado de la ejecución.
        """
        span = self.telemetry.start_span(
            "runbooks.execute_runbook", {"runbook_id": runbook_id}
        )

        execution_id = f"{runbook_id}-{int(time.time())}"

        try:
            # Cargar runbook
            runbook = await self.get_runbook(runbook_id)

            if not runbook:
                raise ValueError(f"Runbook {runbook_id} no encontrado")

            # Inicializar contexto
            ctx = context or {}
            ctx["execution_id"] = execution_id
            ctx["start_time"] = datetime.now().isoformat()
            ctx["runbook_id"] = runbook_id

            # Registrar inicio de ejecución
            self.executions[execution_id] = {
                "id": execution_id,
                "runbook_id": runbook_id,
                "status": "running",
                "start_time": ctx["start_time"],
                "steps": [],
                "context": ctx,
            }

            # Registrar evento de telemetría
            self.telemetry.add_span_event(
                span,
                "runbook_execution_started",
                {"runbook_id": runbook_id, "execution_id": execution_id},
            )

            # Notificar inicio
            if runbook.get("notify_start", False):
                await self._notify_execution_start(runbook, execution_id)

            # Ejecutar pasos
            result = await self._execute_steps(
                runbook.get("steps", []), ctx, execution_id
            )

            # Actualizar estado de ejecución
            self.executions[execution_id]["status"] = "completed"
            self.executions[execution_id]["end_time"] = datetime.now().isoformat()
            self.executions[execution_id]["result"] = result

            # Registrar evento de telemetría
            self.telemetry.add_span_event(
                span,
                "runbook_execution_completed",
                {
                    "runbook_id": runbook_id,
                    "execution_id": execution_id,
                    "success": True,
                },
            )

            # Notificar finalización
            if runbook.get("notify_end", False):
                await self._notify_execution_end(runbook, execution_id, True)

            return {
                "execution_id": execution_id,
                "runbook_id": runbook_id,
                "status": "completed",
                "result": result,
            }
        except Exception as e:
            # Actualizar estado de ejecución
            if execution_id in self.executions:
                self.executions[execution_id]["status"] = "failed"
                self.executions[execution_id]["end_time"] = datetime.now().isoformat()
                self.executions[execution_id]["error"] = str(e)

            # Registrar excepción
            self.telemetry.record_exception(span, e)

            # Registrar evento de telemetría
            self.telemetry.add_span_event(
                span,
                "runbook_execution_failed",
                {
                    "runbook_id": runbook_id,
                    "execution_id": execution_id,
                    "error": str(e),
                },
            )

            # Notificar error
            if runbook and runbook.get("notify_error", True):
                await self._notify_execution_error(runbook, execution_id, str(e))

            return {
                "execution_id": execution_id,
                "runbook_id": runbook_id,
                "status": "failed",
                "error": str(e),
            }
        finally:
            self.telemetry.end_span(span)

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una ejecución de runbook.

        Args:
            execution_id: ID de la ejecución.

        Returns:
            Optional[Dict[str, Any]]: Estado de la ejecución, o None si no existe.
        """
        return self.executions.get(execution_id)

    async def _execute_steps(
        self, steps: List[Dict[str, Any]], context: Dict[str, Any], execution_id: str
    ) -> Dict[str, Any]:
        """
        Ejecuta los pasos de un runbook.

        Args:
            steps: Lista de pasos a ejecutar.
            context: Contexto de ejecución.
            execution_id: ID de la ejecución.

        Returns:
            Dict[str, Any]: Resultado de la ejecución.
        """
        results = {}

        for i, step in enumerate(steps):
            step_id = step.get("id", f"step-{i+1}")
            step_name = step.get("name", f"Paso {i+1}")

            # Registrar inicio de paso
            step_result = {
                "id": step_id,
                "name": step_name,
                "status": "running",
                "start_time": datetime.now().isoformat(),
            }

            if execution_id in self.executions:
                self.executions[execution_id]["steps"].append(step_result)

            span = self.telemetry.start_span(
                "runbooks.execute_step",
                {
                    "runbook_id": context.get("runbook_id", ""),
                    "execution_id": execution_id,
                    "step_id": step_id,
                    "step_name": step_name,
                },
            )

            try:
                # Verificar condición de ejecución
                if "condition" in step and not self._evaluate_condition(
                    step["condition"], context
                ):
                    step_result["status"] = "skipped"
                    step_result["end_time"] = datetime.now().isoformat()
                    step_result["result"] = {
                        "skipped": True,
                        "reason": "condition_not_met",
                    }

                    self.telemetry.add_span_event(
                        span,
                        "step_skipped",
                        {"step_id": step_id, "reason": "condition_not_met"},
                    )

                    results[step_id] = step_result["result"]
                    continue

                # Ejecutar comando
                if "command" in step:
                    command = step["command"]
                    command_name = command.get("name", "")
                    command_args = command.get("args", {})

                    if command_name in self.commands:
                        # Ejecutar comando
                        command_result = await self.commands[command_name](
                            command_args, context
                        )

                        # Actualizar contexto con resultado
                        if "output_var" in command:
                            context[command["output_var"]] = command_result

                        step_result["result"] = command_result
                    else:
                        raise ValueError(f"Comando desconocido: {command_name}")

                # Verificar condición de salida
                if "exit_condition" in step and self._evaluate_condition(
                    step["exit_condition"], context
                ):
                    step_result["status"] = "completed"
                    step_result["end_time"] = datetime.now().isoformat()

                    self.telemetry.add_span_event(
                        span, "step_completed_with_exit", {"step_id": step_id}
                    )

                    results[step_id] = step_result.get("result", {})
                    break

                # Paso completado exitosamente
                step_result["status"] = "completed"
                step_result["end_time"] = datetime.now().isoformat()

                self.telemetry.add_span_event(
                    span, "step_completed", {"step_id": step_id}
                )

                results[step_id] = step_result.get("result", {})
            except Exception as e:
                # Registrar error
                step_result["status"] = "failed"
                step_result["end_time"] = datetime.now().isoformat()
                step_result["error"] = str(e)

                self.telemetry.record_exception(span, e)

                # Verificar si continuar en caso de error
                if not step.get("continue_on_error", False):
                    raise

                results[step_id] = {"error": str(e)}
            finally:
                self.telemetry.end_span(span)

                # Actualizar paso en ejecución
                if execution_id in self.executions:
                    for i, s in enumerate(self.executions[execution_id]["steps"]):
                        if s["id"] == step_id:
                            self.executions[execution_id]["steps"][i] = step_result
                            break

        return results

    def _evaluate_condition(
        self, condition: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """
        Evalúa una condición en el contexto dado.

        Args:
            condition: Condición a evaluar.
            context: Contexto de ejecución.

        Returns:
            bool: Resultado de la evaluación.
        """
        operator = condition.get("operator", "eq")

        if "var" in condition:
            # Obtener valor de variable
            var_name = condition["var"]
            var_value = context.get(var_name)

            # Comparar con valor esperado
            expected = condition.get("value")

            if operator == "eq":
                return var_value == expected
            elif operator == "ne":
                return var_value != expected
            elif operator == "gt":
                return var_value > expected
            elif operator == "lt":
                return var_value < expected
            elif operator == "gte":
                return var_value >= expected
            elif operator == "lte":
                return var_value <= expected
            elif operator == "contains":
                return expected in var_value
            elif operator == "not_contains":
                return expected not in var_value
            elif operator == "exists":
                return var_name in context
            elif operator == "not_exists":
                return var_name not in context
        elif "and" in condition:
            # Evaluar AND de condiciones
            return all(
                self._evaluate_condition(cond, context) for cond in condition["and"]
            )
        elif "or" in condition:
            # Evaluar OR de condiciones
            return any(
                self._evaluate_condition(cond, context) for cond in condition["or"]
            )
        elif "not" in condition:
            # Evaluar NOT de condición
            return not self._evaluate_condition(condition["not"], context)

        return False

    async def _notify_execution_start(self, runbook: Dict[str, Any], execution_id: str):
        """
        Notifica el inicio de una ejecución de runbook.

        Args:
            runbook: Definición del runbook.
            execution_id: ID de la ejecución.
        """
        try:
            # Obtener datos de la ejecución
            execution = self.executions.get(execution_id, {})

            # Crear mensaje
            message = f"Iniciando ejecución de runbook: {runbook.get('name', runbook.get('id', 'Desconocido'))}"
            details = {
                "execution_id": execution_id,
                "runbook_id": runbook.get("id", ""),
                "start_time": execution.get("start_time", ""),
                "description": runbook.get("description", ""),
            }

            # Enviar notificación
            await self.pagerduty_client.send_event(
                summary=message,
                severity="info",
                source="runbook_executor",
                component="runbooks",
                group="runbook_execution",
                class_name="runbook_start",
                custom_details=details,
            )
        except Exception as e:
            logger.warning(f"Error al notificar inicio de ejecución: {str(e)}")

    async def _notify_execution_end(
        self, runbook: Dict[str, Any], execution_id: str, success: bool
    ):
        """
        Notifica la finalización de una ejecución de runbook.

        Args:
            runbook: Definición del runbook.
            execution_id: ID de la ejecución.
            success: Indica si la ejecución fue exitosa.
        """
        try:
            # Obtener datos de la ejecución
            execution = self.executions.get(execution_id, {})

            # Crear mensaje
            status = "completado exitosamente" if success else "fallido"
            message = f"Runbook {status}: {runbook.get('name', runbook.get('id', 'Desconocido'))}"

            details = {
                "execution_id": execution_id,
                "runbook_id": runbook.get("id", ""),
                "start_time": execution.get("start_time", ""),
                "end_time": execution.get("end_time", ""),
                "status": execution.get("status", ""),
                "steps_count": len(execution.get("steps", [])),
                "description": runbook.get("description", ""),
            }

            # Enviar notificación
            await self.pagerduty_client.send_event(
                summary=message,
                severity="info" if success else "warning",
                source="runbook_executor",
                component="runbooks",
                group="runbook_execution",
                class_name="runbook_end",
                custom_details=details,
            )
        except Exception as e:
            logger.warning(f"Error al notificar finalización de ejecución: {str(e)}")

    async def _notify_execution_error(
        self, runbook: Dict[str, Any], execution_id: str, error: str
    ):
        """
        Notifica un error en la ejecución de un runbook.

        Args:
            runbook: Definición del runbook.
            execution_id: ID de la ejecución.
            error: Mensaje de error.
        """
        try:
            # Obtener datos de la ejecución
            execution = self.executions.get(execution_id, {})

            # Crear mensaje
            message = f"Error en ejecución de runbook: {runbook.get('name', runbook.get('id', 'Desconocido'))}"

            details = {
                "execution_id": execution_id,
                "runbook_id": runbook.get("id", ""),
                "start_time": execution.get("start_time", ""),
                "end_time": execution.get("end_time", ""),
                "error": error,
                "description": runbook.get("description", ""),
            }

            # Determinar severidad
            severity = runbook.get("error_severity", "error")

            # Enviar notificación
            await self.pagerduty_client.send_event(
                summary=message,
                severity=severity,
                source="runbook_executor",
                component="runbooks",
                group="runbook_execution",
                class_name="runbook_error",
                custom_details=details,
            )
        except Exception as e:
            logger.warning(f"Error al notificar error de ejecución: {str(e)}")

    # Implementación de comandos

    async def _cmd_check_metric(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para verificar una métrica.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(1)
        return {"status": "ok", "value": 42}

    async def _cmd_check_health(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para verificar el estado de salud de un servicio.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(1)
        return {"status": "healthy"}

    async def _cmd_restart_service(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para reiniciar un servicio.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(2)
        return {"status": "restarted"}

    async def _cmd_scale_service(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para escalar un servicio.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(2)
        return {"status": "scaled", "replicas": args.get("replicas", 1)}

    async def _cmd_notify(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para enviar una notificación.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        try:
            # Enviar notificación
            await self.pagerduty_client.send_event(
                summary=args.get("message", "Notificación de runbook"),
                severity=args.get("severity", "info"),
                source="runbook_executor",
                component=args.get("component", "runbooks"),
                group=args.get("group", "runbook_execution"),
                class_name=args.get("class", "notification"),
                custom_details=args.get("details", {}),
            )

            return {"status": "sent"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _cmd_wait(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para esperar un tiempo determinado.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        seconds = args.get("seconds", 0)
        await asyncio.sleep(seconds)
        return {"status": "completed", "waited_seconds": seconds}

    async def _cmd_execute_query(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para ejecutar una consulta.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(1)
        return {"status": "executed", "rows": 0}

    async def _cmd_check_logs(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para verificar logs.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(1)
        return {"status": "checked", "matches": 0}

    async def _cmd_run_command(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para ejecutar un comando del sistema.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(1)
        return {"status": "executed", "exit_code": 0}

    async def _cmd_toggle_feature_flag(
        self, args: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comando para activar/desactivar un feature flag.

        Args:
            args: Argumentos del comando.
            context: Contexto de ejecución.

        Returns:
            Dict[str, Any]: Resultado del comando.
        """
        # Implementación pendiente
        await asyncio.sleep(1)
        return {"status": "toggled", "enabled": args.get("enabled", False)}
