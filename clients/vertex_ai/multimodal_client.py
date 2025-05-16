"""
Cliente específico para capacidades multimodales de Vertex AI.

Este módulo proporciona un cliente especializado para interactuar con las APIs
multimodales de Vertex AI, permitiendo procesar entradas combinadas de texto e imágenes
y realizar análisis que requieren comprensión de múltiples modalidades.
"""
import logging
import base64
import os
import json
import asyncio
import time
from typing import Dict, Any, Optional, Union, List
import aiohttp
from google.cloud import aiplatform
from google.cloud.aiplatform import VertexAI
from core.logging_config import get_logger
from core.telemetry import Telemetry

# Configurar logger
logger = get_logger(__name__)

class VertexAIMultimodalClient:
    """
    Cliente para interactuar con las APIs multimodales de Vertex AI.
    
    Proporciona métodos para procesar entradas combinadas de texto e imágenes,
    permitiendo realizar análisis que requieren comprensión de múltiples modalidades.
    """
    
    def __init__(self, model: str = "gemini-1.5-pro-vision", telemetry: Optional[Telemetry] = None):
        """
        Inicializa el cliente multimodal de Vertex AI.
        
        Args:
            model: Modelo de Vertex AI a utilizar para el procesamiento multimodal
            telemetry: Instancia de Telemetry para métricas y trazas (opcional)
        """
        self.model = model
        self.telemetry = telemetry
        self.vertex_ai_initialized = False
        
        # Inicializar Vertex AI
        try:
            gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
            gcp_region = os.getenv("GCP_REGION", "us-central1")
            
            logger.info(f"Inicializando Vertex AI para VertexAIMultimodalClient con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            self.vertex_ai_initialized = True
            logger.info("Vertex AI inicializado correctamente para VertexAIMultimodalClient")
        except Exception as e:
            logger.error(f"Error al inicializar Vertex AI para VertexAIMultimodalClient: {e}", exc_info=True)
    
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
        # Iniciar telemetría si está disponible
        span = None
        start_time = time.time()
        
        if self.telemetry:
            span = self.telemetry.start_span("vertex_ai_multimodal_process")
            self.telemetry.add_span_attribute(span, "model", self.model)
            self.telemetry.add_span_attribute(span, "temperature", temperature)
            self.telemetry.add_span_attribute(span, "max_output_tokens", max_output_tokens)
        
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
            
            # Registrar métricas de telemetría si está disponible
            if self.telemetry and span:
                duration = time.time() - start_time
                self.telemetry.add_span_attribute(span, "duration", duration)
                self.telemetry.add_span_attribute(span, "status", result["status"])
                self.telemetry.end_span(span)
                
                # Registrar métricas
                self.telemetry.record_metric("vertex_ai_multimodal_process_duration", duration)
                self.telemetry.record_metric("vertex_ai_multimodal_process_count", 1)
            
            return result
        except Exception as e:
            logger.error(f"Error en procesamiento multimodal: {e}", exc_info=True)
            
            # Registrar error en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
                self.telemetry.add_span_attribute(span, "status", "error")
                self.telemetry.end_span(span)
                
                # Registrar métricas de error
                self.telemetry.record_metric("vertex_ai_multimodal_process_error_count", 1)
            
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
        # Iniciar telemetría si está disponible
        span = None
        start_time = time.time()
        
        if self.telemetry:
            span = self.telemetry.start_span("vertex_ai_multimodal_compare_images")
            self.telemetry.add_span_attribute(span, "model", self.model)
            self.telemetry.add_span_attribute(span, "temperature", temperature)
            self.telemetry.add_span_attribute(span, "max_output_tokens", max_output_tokens)
        
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
            
            # Registrar métricas de telemetría si está disponible
            if self.telemetry and span:
                duration = time.time() - start_time
                self.telemetry.add_span_attribute(span, "duration", duration)
                self.telemetry.add_span_attribute(span, "status", result["status"])
                self.telemetry.end_span(span)
                
                # Registrar métricas
                self.telemetry.record_metric("vertex_ai_multimodal_compare_images_duration", duration)
                self.telemetry.record_metric("vertex_ai_multimodal_compare_images_count", 1)
            
            return result
        except Exception as e:
            logger.error(f"Error en comparación de imágenes: {e}", exc_info=True)
            
            # Registrar error en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
                self.telemetry.add_span_attribute(span, "status", "error")
                self.telemetry.end_span(span)
                
                # Registrar métricas de error
                self.telemetry.record_metric("vertex_ai_multimodal_compare_images_error_count", 1)
            
            return {
                "text": f"Error en comparación de imágenes: {str(e)}",
                "model": self.model,
                "status": "error",
                "error": str(e)
            }
    
    async def analyze_document(self, image_data: Union[str, Dict[str, Any]], 
                             prompt: Optional[str] = None,
                             temperature: float = 0.2,
                             max_output_tokens: int = 1024) -> Dict[str, Any]:
        """
        Analiza un documento (imagen de un documento) utilizando Vertex AI.
        
        Args:
            image_data: Datos de la imagen del documento (base64, URL o ruta de archivo)
            prompt: Texto del prompt para guiar el análisis (opcional)
            temperature: Temperatura para la generación (0.0-1.0)
            max_output_tokens: Número máximo de tokens a generar
            
        Returns:
            Dict[str, Any]: Resultados del análisis del documento
        """
        # Iniciar telemetría si está disponible
        span = None
        start_time = time.time()
        
        if self.telemetry:
            span = self.telemetry.start_span("vertex_ai_multimodal_analyze_document")
            self.telemetry.add_span_attribute(span, "model", self.model)
            self.telemetry.add_span_attribute(span, "temperature", temperature)
            self.telemetry.add_span_attribute(span, "max_output_tokens", max_output_tokens)
        
        try:
            # Procesar la imagen según el formato proporcionado
            processed_image = await self._process_image_input(image_data)
            
            # Construir el prompt para el análisis si no se proporciona
            if not prompt:
                prompt = """
                Analiza este documento y extrae la información clave.
                Incluye:
                - Tipo de documento
                - Fecha del documento
                - Remitente/emisor (si aplica)
                - Destinatario (si aplica)
                - Contenido principal
                - Datos numéricos importantes (valores, cantidades, etc.)
                - Cualquier otra información relevante
                
                Organiza la información de manera estructurada y clara.
                """
            
            # Llamar a Vertex AI para el análisis del documento
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
                logger.warning("Vertex AI no inicializado. Usando análisis de documento simulado.")
                result = {
                    "text": "Análisis de documento simulado. Vertex AI no está inicializado correctamente.",
                    "model": "simulado",
                    "status": "simulated"
                }
            
            # Registrar métricas de telemetría si está disponible
            if self.telemetry and span:
                duration = time.time() - start_time
                self.telemetry.add_span_attribute(span, "duration", duration)
                self.telemetry.add_span_attribute(span, "status", result["status"])
                self.telemetry.end_span(span)
                
                # Registrar métricas
                self.telemetry.record_metric("vertex_ai_multimodal_analyze_document_duration", duration)
                self.telemetry.record_metric("vertex_ai_multimodal_analyze_document_count", 1)
            
            return result
        except Exception as e:
            logger.error(f"Error al analizar documento: {e}", exc_info=True)
            
            # Registrar error en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
                self.telemetry.add_span_attribute(span, "status", "error")
                self.telemetry.end_span(span)
                
                # Registrar métricas de error
                self.telemetry.record_metric("vertex_ai_multimodal_analyze_document_error_count", 1)
            
            return {
                "text": f"Error al analizar documento: {str(e)}",
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