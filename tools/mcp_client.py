import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class MCPClient:
    """Cliente para interactuar con servidores compatibles con Model Context Protocol (MCP).

    La URL base y la clave de API se obtienen preferentemente de las variables de entorno
    `MCP_BASE_URL` y `MCP_API_KEY`, lo que evita hard-coding de credenciales.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.base_url: str = (base_url or os.getenv("MCP_BASE_URL", "")).rstrip("/")
        self.api_key: Optional[str] = api_key or os.getenv("MCP_API_KEY")

        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    # ---------------------------------------------------------------------
    # Métodos genéricos
    # ---------------------------------------------------------------------
    def call_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        """Realiza una petición HTTP al endpoint indicado y devuelve JSON."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method.upper(),
                url,
                headers=self.headers,
                params=data if method.upper() == "GET" else None,
                json=data if method.upper() != "GET" else None,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("Error en llamada MCP %s -> %s", url, exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Helpers específicos
    # ------------------------------------------------------------------
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        return self.call_endpoint(f"users/{user_id}")

    def get_program_data(self, program_id: str) -> Dict[str, Any]:
        return self.call_endpoint(f"programs/{program_id}")

    def log_interaction(
        self,
        user_id: str,
        agent_id: str,
        message: str,
        response: str,
    ) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "message": message,
            "response": response,
        }
        return self.call_endpoint("interactions", "POST", payload)

    def search_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        payload = {"query": query, "limit": limit}
        res = self.call_endpoint("knowledge/search", "GET", payload)
        return res.get("results", []) if isinstance(res, dict) else []

    def update_user_data(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.call_endpoint(f"users/{user_id}", "PUT", data)
