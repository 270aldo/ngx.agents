"""
Procesador de visión para análisis de imágenes utilizando Vertex AI.

Este módulo proporciona capacidades de análisis de imágenes, extracción de texto
y otras funcionalidades de visión por computadora utilizando los modelos de Vertex AI.
"""

import base64
import os
from typing import Dict, Any, Union
import aiohttp
from google.cloud import aiplatform
from google.cloud.aiplatform import VertexAI
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)


class VisionProcessor:
    """
    Procesador de visión para análisis de imágenes utilizando Vertex AI.

    Proporciona métodos para analizar imágenes, extraer texto, detectar objetos
    y otras capacidades de visión por computadora.
    """

    def __init__(self, model: str = "gemini-1.5-pro-vision"):
        """
        Inicializa el procesador de visión.

        Args:
            model: Modelo de Vertex AI a utilizar para el análisis de imágenes
        """
        self.model = model
        self.vertex_ai_initialized = False

        # Inicializar Vertex AI
        try:
            gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
            gcp_region = os.getenv("GCP_REGION", "us-central1")

            logger.info(
                f"Inicializando Vertex AI para VisionProcessor con Proyecto: {gcp_project_id}, Región: {gcp_region}"
            )
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            self.vertex_ai_initialized = True
            logger.info("Vertex AI inicializado correctamente para VisionProcessor")
        except Exception as e:
            logger.error(
                f"Error al inicializar Vertex AI para VisionProcessor: {e}",
                exc_info=True,
            )

    async def analyze_image(
        self, image_data: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analiza una imagen utilizando Vertex AI.

        Args:
            image_data: Datos de la imagen (base64, URL o ruta de archivo)

        Returns:
            Dict[str, Any]: Resultados del análisis de la imagen
        """
        try:
            # Procesar la imagen según el formato proporcionado
            processed_image = await self._process_image_input(image_data)

            # Construir el prompt para el análisis
            prompt = """
            Analiza esta imagen y proporciona una descripción detallada de lo que ves.
            Incluye información sobre:
            - Contenido principal de la imagen
            - Elementos visuales importantes
            - Cualquier texto visible
            - Métricas o datos visibles (si es una captura de pantalla de una aplicación)
            - Cualquier otra información relevante
            
            Sé detallado y preciso en tu análisis.
            """

            # Llamar a Vertex AI para el análisis
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(
                    project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
                )

                # Configurar el modelo
                generation_config = {
                    "max_output_tokens": 1024,
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40,
                }

                # Crear la solicitud
                request = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": processed_image,
                                    }
                                },
                            ],
                        }
                    ],
                    "generation_config": generation_config,
                }

                # Enviar la solicitud
                response = await vertex_ai.generate_content_async(
                    model=self.model, **request
                )

                # Procesar la respuesta
                result = {
                    "text": response.text,
                    "model": self.model,
                    "status": "success",
                }
            else:
                # Simulación para desarrollo/pruebas
                logger.warning("Vertex AI no inicializado. Usando análisis simulado.")
                result = {
                    "text": "Análisis simulado de la imagen. Vertex AI no está inicializado correctamente.",
                    "model": "simulado",
                    "status": "simulated",
                }

            return result
        except Exception as e:
            logger.error(f"Error al analizar imagen: {e}", exc_info=True)
            return {
                "text": f"Error al analizar la imagen: {str(e)}",
                "model": self.model,
                "status": "error",
                "error": str(e),
            }

    async def extract_text(
        self, image_data: Union[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extrae texto de una imagen utilizando Vertex AI.

        Args:
            image_data: Datos de la imagen (base64, URL o ruta de archivo)

        Returns:
            Dict[str, Any]: Texto extraído de la imagen
        """
        try:
            # Procesar la imagen según el formato proporcionado
            processed_image = await self._process_image_input(image_data)

            # Construir el prompt para la extracción de texto
            prompt = """
            Extrae todo el texto visible en esta imagen.
            Mantén el formato y la estructura del texto lo más fiel posible al original.
            Incluye números, símbolos y cualquier otro carácter visible.
            No incluyas interpretaciones o análisis, solo el texto extraído.
            """

            # Llamar a Vertex AI para la extracción de texto
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(
                    project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
                )

                # Configurar el modelo
                generation_config = {
                    "max_output_tokens": 1024,
                    "temperature": 0.1,  # Temperatura baja para extracción precisa
                    "top_p": 0.95,
                    "top_k": 40,
                }

                # Crear la solicitud
                request = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": processed_image,
                                    }
                                },
                            ],
                        }
                    ],
                    "generation_config": generation_config,
                }

                # Enviar la solicitud
                response = await vertex_ai.generate_content_async(
                    model=self.model, **request
                )

                # Procesar la respuesta
                result = {
                    "text": response.text,
                    "model": self.model,
                    "status": "success",
                }
            else:
                # Simulación para desarrollo/pruebas
                logger.warning(
                    "Vertex AI no inicializado. Usando extracción de texto simulada."
                )
                result = {
                    "text": "Texto simulado extraído de la imagen. Vertex AI no está inicializado correctamente.",
                    "model": "simulado",
                    "status": "simulated",
                }

            return result
        except Exception as e:
            logger.error(f"Error al extraer texto de imagen: {e}", exc_info=True)
            return {
                "text": f"Error al extraer texto de la imagen: {str(e)}",
                "model": self.model,
                "status": "error",
                "error": str(e),
            }

    async def _process_image_input(self, image_data: Union[str, Dict[str, Any]]) -> str:
        """
        Procesa los datos de entrada de la imagen en el formato requerido por Vertex AI.

        Args:
            image_data: Datos de la imagen (base64, URL o ruta de archivo)

        Returns:
            str: Datos de la imagen en formato base64
        """
        # Si ya es un diccionario con formato específico
        if isinstance(image_data, dict):
            if "base64" in image_data:
                return image_data["base64"]
            elif "url" in image_data:
                # Descargar imagen desde URL
                return await self._download_image(image_data["url"])
            elif "path" in image_data:
                # Leer imagen desde archivo
                return await self._read_image_file(image_data["path"])

        # Si es un string, podría ser base64, URL o ruta
        elif isinstance(image_data, str):
            # Verificar si es base64
            if image_data.startswith("data:image"):
                # Extraer la parte base64 del data URI
                return image_data.split(",")[1]
            elif image_data.startswith("http"):
                # Es una URL
                return await self._download_image(image_data)
            else:
                # Asumir que es una ruta de archivo
                return await self._read_image_file(image_data)

        # Si no se pudo procesar, devolver error
        raise ValueError("Formato de imagen no soportado")

    async def _download_image(self, url: str) -> str:
        """
        Descarga una imagen desde una URL y la convierte a base64.

        Args:
            url: URL de la imagen

        Returns:
            str: Imagen en formato base64
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return base64.b64encode(image_data).decode("utf-8")
                    else:
                        raise Exception(f"Error al descargar imagen: {response.status}")
        except Exception as e:
            logger.error(f"Error al descargar imagen desde URL: {e}", exc_info=True)
            raise

    async def _read_image_file(self, path: str) -> str:
        """
        Lee una imagen desde un archivo y la convierte a base64.

        Args:
            path: Ruta del archivo de imagen

        Returns:
            str: Imagen en formato base64
        """
        try:
            with open(path, "rb") as image_file:
                image_data = image_file.read()
                return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Error al leer imagen desde archivo: {e}", exc_info=True)
            raise
