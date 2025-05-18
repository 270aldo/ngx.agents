"""
Adaptador multimodal para procesamiento de entradas combinadas de texto e imágenes.

Este módulo proporciona capacidades de procesamiento multimodal utilizando
los modelos de Vertex AI, permitiendo analizar conjuntamente texto e imágenes.
"""
import logging
import base64
import os
import json
import asyncio
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import aiohttp
from google.cloud import aiplatform
from google.cloud.aiplatform import VertexAI
from core.logging_config import get_logger
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter

# Configurar logger
logger = get_logger(__name__)

class MultimodalAdapter(BaseAgentAdapter):
    """
    Adaptador para procesamiento multimodal utilizando Vertex AI.
    
    Proporciona métodos para procesar entradas combinadas de texto e imágenes,
    permitiendo realizar análisis que requieren comprensión de múltiples modalidades.
    """
    
    def __init__(self, model: str = "gemini-1.5-pro-vision"):
        """
        Inicializa el adaptador multimodal.
        
        Args:
            model: Modelo de Vertex AI a utilizar para el procesamiento multimodal
        """
        super().__init__()
        self.model = model
        self.vertex_ai_initialized = False
        
        # Inicializar Vertex AI
        try:
            gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
            gcp_region = os.getenv("GCP_REGION", "us-central1")
            
            logger.info(f"Inicializando Vertex AI para MultimodalAdapter con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            self.vertex_ai_initialized = True
            logger.info("Vertex AI inicializado correctamente para MultimodalAdapter")
        except Exception as e:
            logger.error(f"Error al inicializar Vertex AI para MultimodalAdapter: {e}", exc_info=True)
    
    async def process_multimodal(self, prompt: str, image_data: Union[str, Dict[str, Any]], 
                                temperature: float = 0.2, max_output_tokens: int = 1024) -> Dict[str, Any]:
        """
        Procesa una entrada multimodal (texto e imagen) utilizando Vertex AI.
        
        Args:
            prompt: Texto del prompt para el modelo
            image_data: Datos de la imagen (base64, URL o ruta de archivo)
            temperature: Temperatura para la generación (0.0-1.0)
            max_output_tokens: Número máximo de tokens a generar
            
        Returns:
            Dict[str, Any]: Resultados del procesamiento multimodal
        """
        try:
            # Procesar la imagen según el formato proporcionado
            processed_image = await self._process_image_input(image_data)
            
            # Llamar a Vertex AI para el procesamiento multimodal
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id"))
                
                # Configurar el modelo
                generation_config = {
                    "max_output_tokens": max_output_tokens,
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 40
                }
                
                # Crear la solicitud
                request = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": prompt},
                                {"inline_data": {"mime_type": "image/jpeg", "data": processed_image}}
                            ]
                        }
                    ],
                    "generation_config": generation_config
                }
                
                # Enviar la solicitud
                response = await vertex_ai.generate_content_async(
                    model=self.model,
                    **request
                )
                
                # Procesar la respuesta
                result = {
                    "text": response.text,
                    "model": self.model,
                    "status": "success"
                }
            else:
                # Simulación para desarrollo/pruebas
                logger.warning("Vertex AI no inicializado. Usando procesamiento multimodal simulado.")
                result = {
                    "text": "Procesamiento multimodal simulado. Vertex AI no está inicializado correctamente.",
                    "model": "simulado",
                    "status": "simulated"
                }
            
            return result
        except Exception as e:
            logger.error(f"Error en procesamiento multimodal: {e}", exc_info=True)
            return {
                "text": f"Error en procesamiento multimodal: {str(e)}",
                "model": self.model,
                "status": "error",
                "error": str(e)
            }
    
    async def compare_images(self, image_data1: Union[str, Dict[str, Any]], 
                           image_data2: Union[str, Dict[str, Any]], 
                           comparison_prompt: str,
                           temperature: float = 0.2, 
                           max_output_tokens: int = 1024) -> Dict[str, Any]:
        """
        Compara dos imágenes utilizando Vertex AI.
        
        Args:
            image_data1: Datos de la primera imagen (base64, URL o ruta de archivo)
            image_data2: Datos de la segunda imagen (base64, URL o ruta de archivo)
            comparison_prompt: Texto del prompt para guiar la comparación
            temperature: Temperatura para la generación (0.0-1.0)
            max_output_tokens: Número máximo de tokens a generar
            
        Returns:
            Dict[str, Any]: Resultados de la comparación
        """
        try:
            # Procesar las imágenes según el formato proporcionado
            processed_image1 = await self._process_image_input(image_data1)
            processed_image2 = await self._process_image_input(image_data2)
            
            # Llamar a Vertex AI para la comparación de imágenes
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id"))
                
                # Configurar el modelo
                generation_config = {
                    "max_output_tokens": max_output_tokens,
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 40
                }
                
                # Crear la solicitud
                request = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": comparison_prompt},
                                {"inline_data": {"mime_type": "image/jpeg", "data": processed_image1}},
                                {"inline_data": {"mime_type": "image/jpeg", "data": processed_image2}}
                            ]
                        }
                    ],
                    "generation_config": generation_config
                }
                
                # Enviar la solicitud
                response = await vertex_ai.generate_content_async(
                    model=self.model,
                    **request
                )
                
                # Procesar la respuesta
                result = {
                    "text": response.text,
                    "model": self.model,
                    "status": "success"
                }
            else:
                # Simulación para desarrollo/pruebas
                logger.warning("Vertex AI no inicializado. Usando comparación de imágenes simulada.")
                result = {
                    "text": "Comparación de imágenes simulada. Vertex AI no está inicializado correctamente.",
                    "model": "simulado",
                    "status": "simulated"
                }
            
            return result
        except Exception as e:
            logger.error(f"Error en comparación de imágenes: {e}", exc_info=True)
            return {
                "text": f"Error en comparación de imágenes: {str(e)}",
                "model": self.model,
                "status": "error",
                "error": str(e)
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
            
    async def _process_query(self, query: str, user_id: str = None, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario relacionada con procesamiento multimodal.
        
        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta del adaptador
        """
        try:
            # Clasificar el tipo de consulta
            query_type = await self._classify_query(query, user_id)
            
            # Verificar si hay una imagen en los kwargs
            image_data = kwargs.get('image_data')
            image_data2 = kwargs.get('image_data2')
            
            if not image_data:
                return {
                    "success": False,
                    "error": "No se proporcionaron datos de imagen para procesar",
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Determinar la operación a realizar según el tipo de consulta
            result = None
            if query_type == "image_comparison" and image_data2:
                # Si es comparación de imágenes y tenemos dos imágenes
                result = await self.compare_images(image_data, image_data2, comparison_prompt=query)
            else:
                # Procesamiento multimodal estándar
                result = await self.process_multimodal(query, image_data)
            
            return {
                "success": True,
                "output": result.get("text", "Procesamiento multimodal completado"),
                "query_type": query_type,
                "model": result.get("model", self.model),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error al procesar consulta multimodal: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para MultimodalAdapter.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "comparar": "image_comparison",
            "diferencia": "image_comparison",
            "similitud": "image_comparison",
            "describir": "image_description",
            "analizar": "image_analysis",
            "identificar": "object_identification",
            "explicar": "content_explanation"
        }