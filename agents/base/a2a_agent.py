"""
Clase base para agentes compatibles con el protocolo A2A (Agent-to-Agent).

Implementa el estándar oficial de Google para el protocolo A2A,
permitiendo a los agentes registrarse, comunicarse y ejecutar tareas
a través de un servidor A2A.
"""

import asyncio
import json
import logging
import uuid
import websockets
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional
import random
import time

from config.settings import A2A_SERVER_URL, A2A_WEBSOCKET_URL
from core.skill import Skill, SkillStatus
from core.agent_card import AgentCard
from agents.base.base_agent import BaseAgent

logger = logging.getLogger(__name__)

AGENT_PING_INTERVAL = (
    25  # Segundos, ligeramente menor que HEARTBEAT_INTERVAL del servidor
)


class A2AAgent(BaseAgent):
    """
    Clase base para agentes compatibles con el protocolo A2A (Agent-to-Agent).

    Esta implementación sigue el estándar oficial de Google para el protocolo A2A,
    permitiendo a los agentes registrarse, comunicarse y ejecutar tareas a través
    de un servidor A2A.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[str],
        endpoint: Optional[str] = None,
        version: str = "1.0.0",
        skills: Optional[List[Dict[str, str]]] = None,
        auto_register_skills: bool = True,
        a2a_server_url: Optional[str] = None,
        **kwargs,  # Aceptar parámetros adicionales como toolkit, etc.
    ):
        """
        Inicializa un agente A2A.

        Args:
            agent_id: Identificador único del agente
            name: Nombre del agente
            description: Descripción del agente
            capabilities: Lista de capacidades del agente
            endpoint: Endpoint HTTP para recibir solicitudes
            version: Versión del agente
            skills: Lista de habilidades del agente (nombre y descripción)
            auto_register_skills: Si es True, registra automáticamente las skills disponibles
            a2a_server_url: URL del servidor A2A (opcional, por defecto usa config.settings)
            **kwargs: Parámetros adicionales para pasar a la clase base BaseAgent
        """
        # Pasar parámetros comunes a la clase base BaseAgent
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            version=version,
            **kwargs,
        )

        # Atributos específicos de A2A
        self.endpoint = endpoint

        # Inicializar registro de skills
        self.registered_skills: Dict[str, Skill] = {}
        self.skill_tasks: Dict[str, Dict[str, Any]] = {}

        # Convertir capabilities a skills si no se proporcionan skills
        if not skills and capabilities:
            self.skills = [
                {"name": cap, "description": cap.replace("_", " ").title()}
                for cap in capabilities
            ]
        else:
            self.skills = skills or []

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_registered = False
        self.pending_messages: List[Dict[str, Any]] = (
            []
        )  # Cola para mensajes si se envían antes de conectar
        self._send_pings_task: Optional[asyncio.Task] = None

        # Registrar skills automáticamente si se solicita
        if auto_register_skills:
            self._register_available_skills()

    def _register_available_skills(self) -> None:
        """Registra todas las skills disponibles desde el registro de skills."""
        # TODO: Revisar si este mecanismo de SkillRegistry sigue siendo necesario
        # dado que ADKAgent ahora procesa self.skills de la subclase.
        # Por ahora, se comenta para evitar ImportError con SkillRegistry.
        """
        try:
            # Inicializar el registro de skills
            # skill_registry = SkillRegistry() # Comentado para evitar ImportError
            # # Obtener todas las skills disponibles
            # available_skills = skill_registry.list_skills()
            # logger.info(f"Encontradas {len(available_skills)} skills disponibles")
            # 
            # # Registrar cada skill en el agente
            # for skill_info in available_skills:
            #     skill_name = skill_info["name"]
            #     skill = skill_registry.get_skill(skill_name)
            #     if skill:
            #         self.register_skill(skill)
            #         
            # logger.info(f"Registradas {len(self.registered_skills)} skills en el agente {self.agent_id}")
            # 
            # # Actualizar la lista de skills para el registro en el servidor A2A
            # self._update_skill_list()
            pass # Mantener el try-except por si se reintroduce lógica aquí
            
        except Exception as e:
            logger.error(f"Error al registrar skills disponibles: {str(e)}")
        """

    def register_skill(self, skill: Skill) -> bool:
        """
        Registra una skill en el agente.

        Args:
            skill: Instancia de la skill a registrar

        Returns:
            bool: True si se registró correctamente, False en caso contrario
        """
        try:
            skill_name = skill.name
            if skill_name in self.registered_skills:
                logger.warning(
                    f"Skill {skill_name} ya está registrada en el agente {self.agent_id}. Sobrescribiendo."
                )

            self.registered_skills[skill_name] = skill
            logger.info(f"Skill {skill_name} registrada en el agente {self.agent_id}")

            # Actualizar la lista de skills para el registro en el servidor A2A
            self._update_skill_list()

            return True
        except Exception as e:
            logger.error(
                f"Error al registrar skill {getattr(skill, 'name', 'desconocida')}: {str(e)}"
            )
            return False

    def unregister_skill(self, skill_name: str) -> bool:
        """
        Elimina una skill del agente.

        Args:
            skill_name: Nombre de la skill a eliminar

        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        if skill_name in self.registered_skills:
            del self.registered_skills[skill_name]
            logger.info(f"Skill {skill_name} eliminada del agente {self.agent_id}")

            # Actualizar la lista de skills para el registro en el servidor A2A
            self._update_skill_list()

            return True
        else:
            logger.warning(
                f"Skill {skill_name} no está registrada en el agente {self.agent_id}"
            )
            return False

    def _update_skill_list(self) -> None:
        """
        Actualiza la lista de skills para el registro en el servidor A2A.
        """
        # Convertir las skills registradas a formato para el servidor A2A
        self.skills = [
            {"name": name, "description": skill.description, "version": skill.version}
            for name, skill in self.registered_skills.items()
        ]

        # Agregar las capacidades como skills si no están ya incluidas
        skill_names = {skill["name"] for skill in self.skills}
        for cap in self.capabilities:
            if cap not in skill_names:
                self.skills.append(
                    {
                        "name": cap,
                        "description": cap.replace("_", " ").title(),
                        "version": "1.0.0",
                    }
                )

    async def get_skill_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una tarea de skill.

        Args:
            task_id: ID de la tarea

        Returns:
            Dict con el estado de la tarea o None si no existe
        """
        return self.skill_tasks.get(task_id)

    async def register(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Registra el agente en el servidor A2A con reintentos automáticos.

        Args:
            max_retries: Número máximo de intentos de registro
            retry_delay: Tiempo de espera entre reintentos (en segundos)

        Returns:
            bool: True si el registro fue exitoso, False en caso contrario
        """
        agent_info = {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "endpoint": self.endpoint,
            "version": self.version,
            "skills": self.skills,
            "auth": {"type": "none"},
        }

        # Implementar reintentos con backoff exponencial
        retries = 0
        while retries <= max_retries:
            try:
                logger.info(
                    f"Intento {retries+1}/{max_retries+1} de registro del agente {self.agent_id}"
                )

                # Registrar el agente mediante HTTP
                async with httpx.AsyncClient(
                    base_url=A2A_SERVER_URL, timeout=10.0
                ) as client:
                    response = await client.post("/agents/register", json=agent_info)
                    response.raise_for_status()
                    data = await response.json()

                if data.get("status") == "success":
                    self.is_registered = True
                    logger.info(f"Agente {self.agent_id} registrado correctamente")

                    # Conectar WebSocket para mensajería en tiempo real
                    await self.connect()
                    return True
                else:
                    error_msg = data.get("message", "Sin mensaje de error")
                    logger.warning(
                        f"Fallo al registrar agente {self.agent_id}: {error_msg}"
                    )

                    # Si el error es 409 (conflicto), el agente ya está registrado
                    if response.status_code == 409:
                        logger.info(
                            f"El agente {self.agent_id} ya estaba registrado, intentando conectar..."
                        )
                        self.is_registered = True
                        await self.connect()
                        return True
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Error HTTP al registrar el agente {self.agent_id}: {e.response.status_code} - {e.response.text}"
                )
                # Si el error es 409 (conflicto), el agente ya está registrado
                if e.response.status_code == 409:
                    logger.info(
                        f"El agente {self.agent_id} ya estaba registrado, intentando conectar..."
                    )
                    self.is_registered = True
                    await self.connect()
                    return True
            except Exception as e:
                logger.error(f"Error al registrar el agente {self.agent_id}: {str(e)}")

            # Si llegamos aquí, hubo un error y debemos reintentar
            retries += 1
            if retries <= max_retries:
                # Backoff exponencial con jitter para evitar tormentas de reintentos
                wait_time = retry_delay * (2 ** (retries - 1)) * (0.5 + random.random())
                logger.info(f"Reintentando registro en {wait_time:.2f} segundos...")
                await asyncio.sleep(wait_time)

        logger.error(
            f"Agotados todos los intentos de registro para el agente {self.agent_id}"
        )
        return False

    async def connect(self, max_retries: int = 5, retry_delay: float = 1.5) -> bool:
        """
        Establece una conexión WebSocket con el servidor A2A con reintentos automáticos.

        Args:
            max_retries: Número máximo de intentos de conexión
            retry_delay: Tiempo base de espera entre reintentos (en segundos)
        """
        if self.is_connected:
            logger.debug(f"Agente {self.agent_id} ya está conectado.")
            return True

        if not self.is_registered:
            logger.warning(
                f"Agente {self.agent_id} intentando conectar sin estar registrado."
            )
            # Intentar registrar automáticamente
            if not await self.register():
                logger.error(f"Fallo al registrar {self.agent_id} antes de conectar.")
                return False

        websocket_url = f"{A2A_WEBSOCKET_URL}/agents/connect/{self.agent_id}"

        # Implementar reintentos con backoff exponencial
        retries = 0
        while retries <= max_retries:
            try:
                logger.info(
                    f"Intento {retries+1}/{max_retries+1} de conexión del agente {self.agent_id} a {websocket_url}"
                )
                self.websocket = await websockets.connect(
                    websocket_url,
                    ping_interval=AGENT_PING_INTERVAL,  # Configurar ping automático de websockets
                    ping_timeout=AGENT_PING_INTERVAL
                    * 2,  # Timeout para considerar la conexión perdida
                    close_timeout=5.0,  # Timeout para cerrar la conexión
                )
                self.is_connected = True
                logger.info(
                    f"Agente {self.agent_id} conectado al servidor A2A via WebSocket"
                )

                # Enviar mensajes pendientes si los hay
                if self.pending_messages:
                    logger.info(
                        f"Enviando {len(self.pending_messages)} mensajes pendientes"
                    )
                    for message in self.pending_messages:
                        try:
                            await self.websocket.send(json.dumps(message))
                            logger.debug(f"Mensaje pendiente enviado: {message}")
                        except Exception as e:
                            logger.error(f"Error al enviar mensaje pendiente: {str(e)}")
                    self.pending_messages = []

                # Iniciar el bucle de recepción de mensajes y el envío de pings
                asyncio.create_task(self._message_loop())  # Tarea para recibir
                self._send_pings_task = asyncio.create_task(
                    self._send_pings()
                )  # Tarea para enviar pings

                return True

            except (
                websockets.exceptions.InvalidStatusCode,
                websockets.exceptions.InvalidHandshake,
            ) as e:
                # Errores de handshake/status indican problemas con el servidor o la autenticación
                logger.error(f"Error de protocolo WebSocket: {str(e)}")
                if "401" in str(e) or "403" in str(e):
                    logger.critical(
                        f"Error de autenticación. Agente {self.agent_id} no autorizado."
                    )
                    return False  # No reintentar en caso de error de autenticación

            except (
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
            ) as e:
                # Errores de conexión que pueden ser temporales
                logger.warning(f"Error de conexión WebSocket: {str(e)}")

            except Exception as e:
                # Cualquier otro error
                logger.error(
                    f"Error al conectar el agente {self.agent_id} a {websocket_url}: {str(e)}"
                )

            # Limpiar el estado en caso de error
            self.is_connected = False
            self.websocket = None

            # Si llegamos aquí, hubo un error y debemos reintentar
            retries += 1
            if retries <= max_retries:
                # Backoff exponencial con jitter para evitar tormentas de reintentos
                wait_time = retry_delay * (2 ** (retries - 1)) * (0.5 + random.random())
                logger.info(f"Reintentando conexión en {wait_time:.2f} segundos...")
                await asyncio.sleep(wait_time)

        logger.error(
            f"Agotados todos los intentos de conexión para el agente {self.agent_id}"
        )
        return False

    async def disconnect(self) -> None:
        """
        Cierra la conexión WebSocket con el servidor A2A.
        """
        # Cancelar la tarea de envío de pings si está activa
        if self._send_pings_task and not self._send_pings_task.done():
            self._send_pings_task.cancel()
            try:
                await self._send_pings_task  # Esperar a que se cancele
            except asyncio.CancelledError:
                logger.debug(f"Tarea de envío de pings cancelada para {self.agent_id}")
        self._send_pings_task = None

        if not self.is_connected or not self.websocket:
            logger.debug(
                f"Agente {self.agent_id} ya está desconectado o sin websocket."
            )
            return

        try:
            await self.websocket.close()
            logger.info(f"Agente {self.agent_id} desconectado del servidor A2A")
        except Exception as e:
            logger.error(f"Error al desconectar el agente {self.agent_id}: {e}")
        finally:
            self.is_connected = False
            self.websocket = None

    async def _message_loop(self):
        """
        Bucle para recibir y procesar mensajes del servidor A2A.
        Incluye reconexión automática cuando se detecta una desconexión.
        """
        if not self.is_connected or not self.websocket:
            logger.error(
                f"Intento de iniciar _message_loop sin conexión WebSocket para {self.agent_id}"
            )
            return

        logger.info(f"Iniciando bucle de mensajes para {self.agent_id}")

        # Parámetros para la reconexión automática
        reconnect_delay = 1.0  # Delay inicial para reconexión (segundos)
        max_reconnect_delay = 60.0  # Delay máximo para reconexión (segundos)
        reconnect_attempts = 0
        max_reconnect_attempts = 10  # Número máximo de intentos de reconexión
        reconnect_enabled = (
            True  # Flag para habilitar/deshabilitar reconexión automática
        )

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"Mensaje recibido para {self.agent_id}: {data}")

                    # Manejo de Heartbeat (Ping/Pong)
                    if isinstance(data, dict) and data.get("type") == "ping":
                        logger.debug(
                            f"Ping recibido de servidor, enviando pong para {self.agent_id}"
                        )
                        await self.send_message({"type": "pong"})
                        continue  # No procesar pings más allá

                    # Procesar otros mensajes
                    await self._process_message(data)

                except json.JSONDecodeError:
                    logger.error(
                        f"Mensaje inválido (no JSON) recibido para {self.agent_id}: {message[:100]}"
                    )
                except Exception as e:
                    logger.error(f"Error procesando mensaje para {self.agent_id}: {e}")
                    # Continuar procesando mensajes a pesar del error

        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Conexión WebSocket cerrada limpiamente para {self.agent_id}")
            # Cerrada limpiamente, no intentar reconectar
            reconnect_enabled = False

        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(
                f"Conexión WebSocket cerrada con error para {self.agent_id}: {e}"
            )
            # Mantener reconnect_enabled = True para intentar reconectar

        except Exception as e:
            logger.error(f"Error inesperado en _message_loop para {self.agent_id}: {e}")
            # Mantener reconnect_enabled = True para intentar reconectar

        finally:
            logger.info(
                f"Saliendo de _message_loop para {self.agent_id}. Limpiando conexión."
            )
            # Asegurarse de marcar como desconectado y cancelar pings
            await self.disconnect()

            # Intentar reconectar si está habilitado
            if reconnect_enabled and reconnect_attempts < max_reconnect_attempts:
                reconnect_attempts += 1
                actual_delay = min(
                    reconnect_delay * (1.5 ** (reconnect_attempts - 1)),
                    max_reconnect_delay,
                )
                # Añadir jitter para evitar reconexiones sincronizadas de múltiples agentes
                actual_delay = actual_delay * (0.75 + 0.5 * random.random())

                logger.info(
                    f"Intentando reconectar en {actual_delay:.2f}s (intento {reconnect_attempts}/{max_reconnect_attempts})"
                )
                await asyncio.sleep(actual_delay)

                # Intentar reconectar
                try:
                    # Primero verificar si ya estamos registrados
                    if not self.is_registered:
                        logger.info(
                            "Intentando registrar nuevamente antes de reconectar"
                        )
                        await self.register()
                    else:
                        logger.info("Intentando reconectar")
                        await self.connect()

                    if self.is_connected:
                        logger.info(
                            f"Reconexión exitosa después de {reconnect_attempts} intentos"
                        )
                        # No necesitamos hacer nada más, connect() ya habrá iniciado un nuevo _message_loop
                    else:
                        logger.error("Fallo en la reconexión")
                        # Programar un nuevo intento de reconexión si no hemos alcanzado el límite
                        if reconnect_attempts < max_reconnect_attempts:
                            asyncio.create_task(
                                self._delayed_reconnect(
                                    reconnect_attempts,
                                    max_reconnect_attempts,
                                    reconnect_delay,
                                    max_reconnect_delay,
                                )
                            )
                except Exception as e:
                    logger.error(f"Error al intentar reconectar: {str(e)}")
                    # Programar un nuevo intento de reconexión si no hemos alcanzado el límite
                    if reconnect_attempts < max_reconnect_attempts:
                        asyncio.create_task(
                            self._delayed_reconnect(
                                reconnect_attempts,
                                max_reconnect_attempts,
                                reconnect_delay,
                                max_reconnect_delay,
                            )
                        )
            elif reconnect_attempts >= max_reconnect_attempts:
                logger.error(
                    f"Máximo número de reconexiones alcanzado ({max_reconnect_attempts}). Abandonando."
                )

    async def _delayed_reconnect(
        self, current_attempts, max_attempts, base_delay, max_delay
    ):
        """
        Método auxiliar para intentar reconectar después de un tiempo de espera.
        """
        current_attempts += 1
        if current_attempts > max_attempts:
            logger.error(
                f"Máximo número de reconexiones alcanzado ({max_attempts}). Abandonando."
            )
            return

        actual_delay = min(base_delay * (1.5 ** (current_attempts - 1)), max_delay)
        # Añadir jitter para evitar reconexiones sincronizadas
        actual_delay = actual_delay * (0.75 + 0.5 * random.random())

        logger.info(
            f"Reintentando reconexión en {actual_delay:.2f}s (intento {current_attempts}/{max_attempts})"
        )
        await asyncio.sleep(actual_delay)

        try:
            # Primero verificar si ya estamos registrados
            if not self.is_registered:
                logger.info("Intentando registrar nuevamente antes de reconectar")
                await self.register()
            else:
                logger.info("Intentando reconectar")
                await self.connect()

            if self.is_connected:
                logger.info(
                    f"Reconexión exitosa después de {current_attempts} intentos"
                )
            else:
                # Si falla, programar otro intento
                await self._delayed_reconnect(
                    current_attempts, max_attempts, base_delay, max_delay
                )
        except Exception as e:
            logger.error(f"Error al intentar reconectar: {str(e)}")
            # Programar otro intento
            await self._delayed_reconnect(
                current_attempts, max_attempts, base_delay, max_delay
            )

    async def _send_pings(self):
        """Tarea en segundo plano para enviar pings periódicos al servidor."""
        while self.is_connected and self.websocket:
            try:
                await asyncio.sleep(AGENT_PING_INTERVAL)
                ping_msg = {"type": "ping"}
                logger.debug(f"Enviando ping al servidor desde {self.agent_id}")
                await self.websocket.send(json.dumps(ping_msg))
            except asyncio.CancelledError:
                logger.info(f"Tarea de envío de pings cancelada para {self.agent_id}")
                break  # Salir del bucle si se cancela
            except websockets.exceptions.ConnectionClosed:
                logger.warning(
                    f"No se pudo enviar ping, conexión cerrada para {self.agent_id}"
                )
                break  # Salir si la conexión se cierra
            except Exception as e:
                logger.error(f"Error enviando ping desde {self.agent_id}: {e}")
                # Esperar un poco antes de reintentar en caso de error
                await asyncio.sleep(5)
        logger.debug(f"Tarea _send_pings finalizada para {self.agent_id}")

    async def _process_message(self, data: Dict[str, Any]):
        """
        Procesa un mensaje recibido del servidor A2A.

        Args:
            data: Mensaje recibido
        """
        message_type = data.get("type")
        logger.debug(f"Procesando mensaje tipo '{message_type}' para {self.agent_id}")

        if message_type == "task":
            task_id = data.get("task_id")
            content = data.get("content", {})
            logger.info(f"Tarea '{task_id}' recibida por agente {self.agent_id}")

            try:
                # Llamar al manejador de la tarea
                result, status = await self._handle_task(task_id, content)
                logger.info(
                    f"Tarea '{task_id}' procesada por {self.agent_id} con estado '{status}'"
                )
            except Exception as e:
                logger.error(
                    f"Error al manejar tarea '{task_id}' en agente {self.agent_id}: {e}"
                )
                result = {"error": str(e)}
                status = "failed"

            # Enviar actualización de estado de vuelta al servidor
            update_message = {
                "type": "task_update",
                "task_id": task_id,
                "status": status,
                "result": result,
            }
            await self.send_message(update_message)
            logger.debug(
                f"Enviada actualización para tarea '{task_id}' desde {self.agent_id}"
            )

        elif message_type == "message":
            message_id = data.get("id")
            from_agent = data.get("from")
            content = data.get("content", {})
            logger.info(
                f"Mensaje '{message_id}' de {from_agent} recibido por agente {self.agent_id}"
            )
            # Aquí iría la lógica para procesar mensajes de otros agentes
            # Podría requerir enviar una respuesta con send_message
            if self.message_handler:
                await self.message_handler(data)
            else:
                logger.warning(
                    f"Agente {self.agent_id} no tiene message_handler configurado."
                )

        elif message_type == "ping":
            # Ya manejado en _message_loop, pero podría añadirse lógica aquí si fuera necesario
            pass
        else:
            logger.warning(
                f"Tipo de mensaje desconocido '{message_type}' recibido por {self.agent_id}"
            )

        # Aquí podrías añadir más lógica según otros tipos de mensajes

    async def _handle_task(
        self, task_id: str, content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa una tarea según el protocolo A2A oficial.
        Debe ser sobreescrito por clases de agente específicas.

        Args:
            task_id: ID de la tarea.
            content: Contenido de la tarea.

        Returns:
            Dict[str, Any]: Resultado estandarizado de la tarea según el protocolo A2A.
        """
        try:
            # Extraer información relevante
            input_text = content.get("input", "")
            context = content.get("context", {})
            user_id = context.get("user_id")

            # Ejecutar el método run (que debe ser implementado por las subclases)
            result = await self.run(input_text, user_id=user_id, **context)

            # Si el resultado es un string, convertirlo a formato estándar
            if isinstance(result, str):
                result = {
                    "status": "success",
                    "response": result,
                    "confidence": 0.8,
                    "execution_time": 0.0,
                    "agent_id": self.agent_id,
                    "metadata": {},
                }

            # Formatear respuesta según protocolo A2A
            return {
                "task_id": task_id,
                "status": (
                    "completed" if result.get("status") == "success" else "failed"
                ),
                "result": {
                    "response": result.get("response", ""),
                    "confidence": result.get("confidence", 0.0),
                    "metadata": result.get("metadata", {}),
                },
                "error": (
                    result.get("error") if result.get("status") != "success" else None
                ),
                "execution_time": result.get("execution_time", 0.0),
                "completed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error en _handle_task: {e}")
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": {"message": str(e), "type": "execution_error"},
                "execution_time": 0.0,
                "completed_at": datetime.now().isoformat(),
            }

    async def send_message(self, message: Dict[str, Any]):
        """
        Envía un mensaje al servidor A2A.

        Args:
            message: Mensaje a enviar
        """
        if self.is_connected and self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error al enviar mensaje: {e}")
                self.pending_messages.append(message)
        else:
            # Guardar el mensaje para enviarlo cuando se establezca la conexión
            self.pending_messages.append(message)

            # Intentar conectar
            asyncio.create_task(self.connect())

    async def send_message_to_agent(self, to_agent: str, content: Dict[str, Any]):
        """
        Envía un mensaje a otro agente.

        Args:
            to_agent: ID del agente destinatario
            content: Contenido del mensaje
        """
        message = {
            "type": "message",
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "from": self.agent_id,
            "to": to_agent,
            "content": content,
        }

        await self._send_message(message)

    async def request_task(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Solicita a otro agente que realice una tarea.

        Args:
            agent_id: ID del agente que realizará la tarea
            task: Contenido de la tarea

        Returns:
            Dict[str, Any]: Respuesta del servidor A2A
        """
        task_request = {"agent_id": agent_id, "task": task}

        try:
            async with httpx.AsyncClient(
                base_url=A2A_SERVER_URL, timeout=30.0
            ) as client:
                response = await client.post("/agents/request", json=task_request)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error al solicitar tarea al agente {agent_id}: {e}")
            return {"error": str(e)}

    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea según el protocolo A2A oficial.

        Este método determina si la tarea debe ser ejecutada por una skill registrada
        o por el método _handle_task del agente. Sigue el flujo estándar del protocolo A2A.

        Args:
            task: Tarea a ejecutar con formato {"input": str, "context": dict, "parameters": dict, "skill": str}

        Returns:
            Any: Resultado de la ejecución de la tarea
        """
        try:
            # Generar un ID único para la tarea
            task_id = str(uuid.uuid4())

            # Registrar inicio de la tarea
            logger.info(f"Iniciando tarea {task_id} en agente {self.agent_id}")
            task_start_time = time.time()

            # Verificar si la tarea especifica una skill
            skill_name = task.get("skill")

            if skill_name and skill_name in self.registered_skills:
                # Ejecutar la skill especificada
                skill = self.registered_skills[skill_name]

                # Registrar la tarea
                self.skill_tasks[task_id] = {
                    "skill": skill_name,
                    "status": SkillStatus.PENDING,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "result": None,
                    "error": None,
                }

                try:
                    # Ejecutar la skill
                    result = await skill.execute(task.get("parameters", {}))

                    # Actualizar el estado de la tarea
                    self.skill_tasks[task_id]["status"] = SkillStatus.COMPLETED
                    self.skill_tasks[task_id]["result"] = result
                    self.skill_tasks[task_id]["updated_at"] = datetime.now().isoformat()
                    self.skill_tasks[task_id]["execution_time"] = (
                        time.time() - task_start_time
                    )

                    # Formatear resultado según el estándar A2A
                    if isinstance(result, dict) and "status" in result:
                        # Ya está en formato estándar
                        return result
                    else:
                        # Convertir a formato estándar
                        return {
                            "status": "success",
                            "response": (
                                result
                                if isinstance(result, str)
                                else json.dumps(result)
                            ),
                            "confidence": 0.9,  # Alta confianza para skills específicas
                            "execution_time": time.time() - task_start_time,
                            "agent_id": self.agent_id,
                            "skill_used": skill_name,
                            "metadata": {"task_id": task_id},
                        }

                except Exception as e:
                    # Registrar el error
                    self.skill_tasks[task_id]["status"] = SkillStatus.FAILED
                    self.skill_tasks[task_id]["error"] = str(e)
                    self.skill_tasks[task_id]["updated_at"] = datetime.now().isoformat()
                    self.skill_tasks[task_id]["execution_time"] = (
                        time.time() - task_start_time
                    )

                    logger.error(f"Error al ejecutar skill {skill_name}: {e}")

                    # Devolver error en formato estándar
                    return {
                        "status": "error",
                        "response": f"Error al ejecutar skill {skill_name}",
                        "error": str(e),
                        "execution_time": time.time() - task_start_time,
                        "confidence": 0.0,
                        "agent_id": self.agent_id,
                        "metadata": {"task_id": task_id, "skill_attempted": skill_name},
                    }
            else:
                # No es una skill específica, delegar al método _handle_task
                result = await self._handle_task(task_id, task)

                # Asegurar que el resultado tenga el formato correcto
                if (
                    isinstance(result, dict)
                    and "task_id" in result
                    and "status" in result
                ):
                    # Ya está en formato estándar A2A
                    return result
                else:
                    # Convertir a formato estándar A2A
                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "result": (
                            result
                            if isinstance(result, dict)
                            else {"response": str(result)}
                        ),
                        "execution_time": time.time() - task_start_time,
                        "completed_at": datetime.now().isoformat(),
                    }

        except Exception as e:
            logger.error(f"Error al ejecutar tarea: {e}")
            # Devolver error en formato estándar
            return {
                "status": "error",
                "response": "Error al procesar la tarea",
                "error": str(e),
                "execution_time": (
                    time.time() - task_start_time
                    if "task_start_time" in locals()
                    else 0.0
                ),
                "confidence": 0.0,
                "agent_id": self.agent_id,
                "metadata": {},
            }

        # Si no existe una skill registrada, delegamos al método _handle_task (implementación genérica o de la subclase)
        result, _status = await self._handle_task(task_id, task)
        return result

    def create_file_part(
        self, mime_type: str, data: Optional[str] = None, uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea una parte de archivo según el protocolo A2A.

        Args:
            mime_type: Tipo MIME del archivo
            data: Datos del archivo en base64 (opcional)
            uri: URI del archivo (opcional)

        Returns:
            Dict[str, Any]: Parte de archivo
        """
        file_part = {"mime_type": mime_type}

        if data:
            file_part["data"] = data

        if uri:
            file_part["uri"] = uri

        return {"type": "file", "file": file_part}

    def create_data_part(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una parte de datos según el protocolo A2A.

        Args:
            data: Datos estructurados

        Returns:
            Dict[str, Any]: Parte de datos
        """
        return {"type": "data", "data": data}

    def create_message(self, role: str, parts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crea un mensaje según el protocolo A2A.

        Args:
            role: Rol del mensaje ("user" o "agent")
            parts: Partes del mensaje

        Returns:
            Dict[str, Any]: Mensaje
        """
        return {"role": role, "parts": parts, "created_at": datetime.now().isoformat()}

    def create_artifact(
        self, artifact_id: str, artifact_type: str, parts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Crea un artefacto según el protocolo A2A.

        Args:
            artifact_id: ID del artefacto
            artifact_type: Tipo del artefacto
            parts: Partes del artefacto

        Returns:
            Dict[str, Any]: Artefacto
        """
        return {
            "id": artifact_id,
            "type": artifact_type,
            "parts": parts,
            "created_at": datetime.now().isoformat(),
        }

    def create_task(
        self,
        task_id: str,
        messages: List[Dict[str, Any]],
        artifacts: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Crea una tarea según el protocolo A2A.

        Args:
            task_id: ID de la tarea
            messages: Mensajes de la tarea
            artifacts: Artefactos de la tarea (opcional)

        Returns:
            Dict[str, Any]: Tarea
        """
        return {
            "id": task_id,
            "status": "submitted",
            "messages": messages,
            "artifacts": artifacts or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    # Métodos de la clase BaseAgent que debemos implementar
    async def _run_async_impl(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente A2A.

        Sobrescribe el método de la clase base para proporcionar la implementación
        específica de los agentes A2A que utiliza las skills registradas.

        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales (context, parameters, etc.)

        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        # Preparar el contexto
        context = kwargs.get("context", {})
        if user_id:
            context["user_id"] = user_id
        if session_id:
            context["session_id"] = session_id

        # Crear tarea a partir del texto de entrada
        task = {
            "input": input_text,
            "context": context,
            "parameters": kwargs.get("parameters", {}),
        }

        # Ejecutar la tarea utilizando las skills registradas
        response = await self.execute_task(task)

        # Añadir la interacción al historial de conversación
        if isinstance(response, dict) and "response" in response:
            self.add_to_history(input_text, response["response"])
        elif isinstance(response, str):
            self.add_to_history(input_text, response)

        # Formatear respuesta según el estándar ADK
        if isinstance(response, dict):
            # Si ya es un diccionario, asegurarse de que tenga los campos requeridos
            if "status" not in response:
                response["status"] = "success"
            if "agent_id" not in response:
                response["agent_id"] = self.agent_id
            if "metadata" not in response:
                response["metadata"] = {
                    "capabilities_used": (
                        self.capabilities[:1] if self.capabilities else []
                    ),
                    "user_id": user_id,
                }
            return response
        else:
            # Si es una respuesta simple, convertirla al formato estándar
            return {
                "status": "success",
                "response": str(response),
                "error": None,
                "confidence": 0.8,  # Valor predeterminado
                "agent_id": self.agent_id,
                "metadata": {
                    "capabilities_used": (
                        self.capabilities[:1] if self.capabilities else []
                    ),
                    "user_id": user_id,
                },
            }

    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.

        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        # Crear ejemplos predeterminados si no se han definido
        examples = [
            {
                "input": {"message": "Hola, ¿cómo estás?"},
                "output": {
                    "response": "Hola, soy un agente especializado. ¿En qué puedo ayudarte?"
                },
            }
        ]

        # Usar la clase AgentCard para crear una tarjeta estandarizada
        agent_card = AgentCard.create_standard_card(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            skills=self.skills,
            version=self.version,
            examples=examples,
            metadata={
                "endpoint": self.endpoint or f"/agents/{self.agent_id}",
                "auth": {"type": "none"},
                "last_updated": datetime.now().isoformat(),
            },
        )

        return agent_card.to_dict()
