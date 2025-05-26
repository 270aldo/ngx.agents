"""
Cliente para interactuar con Perplexity AI.

Proporciona métodos para realizar búsquedas, obtener respuestas a preguntas
y generar contenido con acceso a información actualizada.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from clients.base_client import BaseClient, retry_with_backoff
from config.secrets import settings

logger = logging.getLogger(__name__)


class PerplexityClient(BaseClient):
    """
    Cliente para Perplexity AI con patrón Singleton.

    Proporciona métodos para realizar búsquedas y obtener respuestas
    basadas en conocimiento actualizado.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    # URL base de la API
    API_URL = "https://api.perplexity.ai"

    def __new__(cls, *args: Any, **kwargs: Any) -> "PerplexityClient":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(PerplexityClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Inicializa el cliente de Perplexity AI."""
        # Evitar reinicialización en el patrón Singleton
        if self._initialized:
            return

        super().__init__(service_name="perplexity")
        self.api_key = None
        self.http_client = None
        self._initialized = True

    async def initialize(self) -> None:
        """
        Inicializa la conexión con Perplexity AI.

        Configura la API key y prepara el cliente HTTP para su uso.
        """
        if not settings.PERPLEXITY_API_KEY:
            raise ValueError(
                "PERPLEXITY_API_KEY no está configurada en las variables de entorno"
            )

        self.api_key = settings.PERPLEXITY_API_KEY

        # Inicializar cliente HTTP
        self.http_client = httpx.AsyncClient(
            base_url=self.API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=settings.DEFAULT_TIMEOUT,
        )

        logger.info("Cliente Perplexity AI inicializado")

    @retry_with_backoff()
    async def search(
        self, query: str, search_focus: str = "internet", max_sources: int = 5
    ) -> Dict[str, Any]:
        """
        Realiza una búsqueda en internet usando Perplexity AI.

        Args:
            query: Consulta de búsqueda
            search_focus: Enfoque de la búsqueda ("internet", "academic", "news", etc.)
            max_sources: Número máximo de fuentes a incluir

        Returns:
            Resultados de la búsqueda con fuentes y respuesta
        """
        if not self.http_client:
            await self.initialize()

        self._record_call("search")

        payload = {
            "query": query,
            "search_focus": search_focus,
            "max_sources": max_sources,
        }

        response = await self.http_client.post("/search", json=payload)
        response.raise_for_status()

        return response.json()

    @retry_with_backoff()
    async def ask(
        self,
        question: str,
        model: str = "llama-3-sonar-small-online",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """
        Realiza una pregunta a Perplexity AI con acceso a internet.

        Args:
            question: Pregunta a responder
            model: Modelo a utilizar
            temperature: Control de aleatoriedad (0.0-1.0)
            max_tokens: Longitud máxima de la respuesta

        Returns:
            Respuesta con fuentes y metadatos
        """
        if not self.http_client:
            await self.initialize()

        self._record_call("ask")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": question}],
            "options": {"temperature": temperature, "max_tokens": max_tokens},
        }

        response = await self.http_client.post("/chat/completions", json=payload)
        response.raise_for_status()

        return response.json()

    @retry_with_backoff()
    async def research(
        self,
        topic: str,
        depth: str = "medium",
        focus: Optional[str] = None,
        model: str = "llama-3-sonar-small-online",
    ) -> Dict[str, Any]:
        """
        Realiza una investigación profunda sobre un tema.

        Args:
            topic: Tema a investigar
            depth: Profundidad de la investigación ("brief", "medium", "comprehensive")
            focus: Enfoque específico de la investigación (opcional)
            model: Modelo a utilizar

        Returns:
            Resultados de la investigación con fuentes y estructura
        """
        if not self.http_client:
            await self.initialize()

        self._record_call("research")

        # Construir el prompt para la investigación
        prompt = f"Realiza una investigación {depth} sobre: {topic}"
        if focus:
            prompt += f". Enfócate específicamente en: {focus}"

        prompt += (
            ". Estructura la respuesta con secciones claras y cita todas las fuentes."
        )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un asistente de investigación que proporciona información detallada y bien estructurada con fuentes verificables.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        response = await self.http_client.post("/chat/completions", json=payload)
        response.raise_for_status()

        return response.json()

    @retry_with_backoff()
    async def fact_check(
        self, statement: str, model: str = "llama-3-sonar-small-online"
    ) -> Dict[str, Any]:
        """
        Verifica la veracidad de una afirmación.

        Args:
            statement: Afirmación a verificar
            model: Modelo a utilizar

        Returns:
            Resultado de la verificación con fuentes y explicación
        """
        if not self.http_client:
            await self.initialize()

        self._record_call("fact_check")

        prompt = f"""
        Verifica la siguiente afirmación y determina si es verdadera, falsa o parcialmente verdadera.
        Proporciona fuentes confiables y una explicación detallada.
        
        Afirmación: "{statement}"
        
        Formato de respuesta:
        {{
          "verdict": "verdadero|falso|parcialmente verdadero",
          "confidence": float entre 0 y 1,
          "explanation": "explicación detallada",
          "sources": [lista de fuentes]
        }}
        """

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un verificador de hechos preciso y objetivo que siempre proporciona fuentes verificables.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        response = await self.http_client.post("/chat/completions", json=payload)
        response.raise_for_status()

        result = response.json()

        # Intentar extraer el JSON de la respuesta
        try:
            content = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            # Buscar el primer { y el último }
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                fact_check_result = json.loads(json_str)
                result["fact_check"] = fact_check_result
        except Exception as e:
            logger.error(f"Error al parsear el resultado de fact_check: {str(e)}")

        return result

    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        if self.http_client:
            await self.http_client.aclose()


# Instancia global para uso en toda la aplicación
perplexity_client = PerplexityClient()
