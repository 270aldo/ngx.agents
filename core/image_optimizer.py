"""
Optimizador de imágenes para reducir el tamaño y la resolución.

Este módulo proporciona funciones para optimizar imágenes antes de enviarlas
a las APIs de visión, reduciendo el consumo de ancho de banda y acelerando
el procesamiento.
"""

import asyncio
import base64
import io
import logging
import os
from typing import Dict, Any, Optional, Union, Tuple
from PIL import Image, ImageOps

from core.logging_config import get_logger
from core.telemetry import Telemetry

# Configurar logger
logger = get_logger(__name__)

class ImageOptimizer:
    """
    Optimizador de imágenes para reducir el tamaño y la resolución.
    
    Proporciona métodos para redimensionar, comprimir y optimizar imágenes
    antes de enviarlas a las APIs de visión.
    """
    
    def __init__(self, max_width: int = 1024, max_height: int = 1024, 
                quality: int = 85, telemetry: Optional[Telemetry] = None):
        """
        Inicializa el optimizador de imágenes.
        
        Args:
            max_width: Ancho máximo de la imagen optimizada
            max_height: Alto máximo de la imagen optimizada
            quality: Calidad de compresión JPEG (0-100)
            telemetry: Instancia de Telemetry para métricas y trazas (opcional)
        """
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality
        self.telemetry = telemetry
        
        # Estadísticas
        self.stats = {
            "images_processed": 0,
            "bytes_before": 0,
            "bytes_after": 0,
            "bytes_saved": 0,
            "errors": 0
        }
        
        logger.info(f"ImageOptimizer inicializado con max_width={max_width}, max_height={max_height}, quality={quality}")
    
    async def optimize_image(self, image_data: Union[str, bytes, Dict[str, Any]], 
                           force_format: Optional[str] = None,
                           preserve_text_quality: bool = True) -> Tuple[Union[str, bytes], Dict[str, Any]]:
        """
        Optimiza una imagen para reducir su tamaño.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            force_format: Formato forzado para la salida (jpg, png, webp)
            preserve_text_quality: Si es True, preserva la calidad para imágenes con texto
            
        Returns:
            Tuple[Union[str, bytes], Dict[str, Any]]: Imagen optimizada y metadatos
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("image_optimizer.optimize")
            self.telemetry.add_span_attribute(span, "preserve_text_quality", preserve_text_quality)
            if force_format:
                self.telemetry.add_span_attribute(span, "force_format", force_format)
        
        try:
            # Procesar la entrada de imagen
            image_bytes, input_format = await self._process_input(image_data)
            original_size = len(image_bytes)
            
            # Registrar tamaño original
            self.stats["bytes_before"] += original_size
            
            if self.telemetry:
                self.telemetry.add_span_attribute(span, "original_size", original_size)
                self.telemetry.add_span_attribute(span, "input_format", input_format)
            
            # Abrir la imagen con PIL
            img = Image.open(io.BytesIO(image_bytes))
            original_width, original_height = img.size
            
            # Determinar si la imagen contiene texto (heurística simple)
            contains_text = False
            if preserve_text_quality:
                # Implementar una heurística simple para detectar texto
                # Esta es una aproximación básica, se podría mejorar con ML
                contains_text = await self._detect_text_heuristic(img)
            
            # Ajustar parámetros de optimización si contiene texto
            max_width = self.max_width
            max_height = self.max_height
            quality = self.quality
            
            if contains_text:
                # Preservar más calidad para imágenes con texto
                max_width = min(1600, original_width)
                max_height = min(1600, original_height)
                quality = min(92, self.quality + 7)
                
                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "contains_text", True)
            
            # Determinar el formato de salida
            output_format = force_format if force_format else input_format
            if output_format.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
                output_format = 'jpeg'  # Formato por defecto
            
            # Normalizar formato
            if output_format.lower() in ['jpg', 'jpeg']:
                output_format = 'JPEG'
            elif output_format.lower() == 'png':
                output_format = 'PNG'
            elif output_format.lower() == 'webp':
                output_format = 'WEBP'
            
            # Redimensionar si es necesario
            if original_width > max_width or original_height > max_height:
                # Calcular nueva dimensión manteniendo la relación de aspecto
                ratio = min(max_width / original_width, max_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                
                # Redimensionar
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "resized", True)
                    self.telemetry.add_span_attribute(span, "new_width", new_width)
                    self.telemetry.add_span_attribute(span, "new_height", new_height)
            
            # Convertir a RGB si es necesario para JPEG
            if output_format == 'JPEG' and img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Guardar la imagen optimizada
            output_buffer = io.BytesIO()
            
            # Ajustar parámetros según el formato
            save_params = {}
            if output_format == 'JPEG':
                save_params = {'quality': quality, 'optimize': True}
            elif output_format == 'PNG':
                save_params = {'optimize': True}
            elif output_format == 'WEBP':
                save_params = {'quality': quality}
            
            img.save(output_buffer, format=output_format, **save_params)
            optimized_bytes = output_buffer.getvalue()
            optimized_size = len(optimized_bytes)
            
            # Si la imagen optimizada es más grande, usar la original
            if optimized_size >= original_size:
                logger.debug("La imagen optimizada es más grande que la original, usando la original")
                optimized_bytes = image_bytes
                optimized_size = original_size
                
                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "optimization_reverted", True)
            
            # Actualizar estadísticas
            self.stats["images_processed"] += 1
            self.stats["bytes_after"] += optimized_size
            bytes_saved = original_size - optimized_size
            self.stats["bytes_saved"] += bytes_saved
            
            # Preparar metadatos
            metadata = {
                "original_size": original_size,
                "optimized_size": optimized_size,
                "bytes_saved": bytes_saved,
                "compression_ratio": original_size / optimized_size if optimized_size > 0 else 1.0,
                "original_width": original_width,
                "original_height": original_height,
                "new_width": img.width,
                "new_height": img.height,
                "format": output_format,
                "contains_text": contains_text
            }
            
            if self.telemetry:
                self.telemetry.add_span_attribute(span, "optimized_size", optimized_size)
                self.telemetry.add_span_attribute(span, "bytes_saved", bytes_saved)
                self.telemetry.add_span_attribute(span, "compression_ratio", metadata["compression_ratio"])
                self.telemetry.record_metric("image_optimizer.bytes_saved", bytes_saved)
                self.telemetry.record_metric("image_optimizer.compression_ratio", metadata["compression_ratio"])
            
            logger.debug(f"Imagen optimizada: {original_size} -> {optimized_size} bytes ({bytes_saved} bytes ahorrados)")
            
            # Devolver en el mismo formato que se recibió
            if isinstance(image_data, str) and "base64" in image_data:
                # Devolver como base64
                result = base64.b64encode(optimized_bytes).decode('utf-8')
                if image_data.startswith("data:image"):
                    # Mantener el formato data URI
                    mime_type = f"image/{output_format.lower()}"
                    result = f"data:{mime_type};base64,{result}"
            else:
                # Devolver como bytes
                result = optimized_bytes
            
            return result, metadata
            
        except Exception as e:
            logger.error(f"Error al optimizar imagen: {e}", exc_info=True)
            self.stats["errors"] += 1
            
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
            
            # Devolver la imagen original en caso de error
            if isinstance(image_data, (str, bytes)):
                return image_data, {"error": str(e)}
            else:
                return image_data, {"error": str(e)}
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)
    
    async def _process_input(self, image_data: Union[str, bytes, Dict[str, Any]]) -> Tuple[bytes, str]:
        """
        Procesa la entrada de imagen en diferentes formatos.
        
        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            
        Returns:
            Tuple[bytes, str]: Bytes de la imagen y formato detectado
        """
        # Si ya es bytes, devolver directamente
        if isinstance(image_data, bytes):
            # Intentar detectar el formato
            format_detected = "jpeg"  # Por defecto
            if image_data.startswith(b'\x89PNG'):
                format_detected = "png"
            elif image_data.startswith(b'\xff\xd8'):
                format_detected = "jpeg"
            elif image_data[0:4] == b'RIFF' and image_data[8:12] == b'WEBP':
                format_detected = "webp"
            
            return image_data, format_detected
        
        # Si es un string base64
        if isinstance(image_data, str):
            if image_data.startswith("data:image"):
                # Es un data URI
                mime_type = image_data.split(";")[0].split(":")[1]
                format_detected = mime_type.split("/")[1]
                base64_data = image_data.split(",")[1]
                return base64.b64decode(base64_data), format_detected
            elif "," in image_data:
                # Posible data URI sin prefijo
                base64_data = image_data.split(",")[1]
                return base64.b64decode(base64_data), "jpeg"  # Asumir JPEG
            else:
                # Asumir que es directamente base64
                try:
                    return base64.b64decode(image_data), "jpeg"  # Asumir JPEG
                except:
                    # Si falla, podría ser una ruta de archivo
                    if os.path.exists(image_data):
                        with open(image_data, "rb") as f:
                            data = f.read()
                        format_detected = os.path.splitext(image_data)[1].lower().replace(".", "")
                        if not format_detected:
                            format_detected = "jpeg"  # Asumir JPEG
                        return data, format_detected
                    else:
                        raise ValueError(f"No se pudo procesar la entrada de imagen: {image_data[:30]}...")
        
        # Si es un diccionario
        if isinstance(image_data, dict):
            # Si tiene URL, descargar la imagen
            if "url" in image_data:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_data["url"]) as response:
                        if response.status == 200:
                            data = await response.read()
                            # Detectar formato desde la URL
                            url_path = image_data["url"].split("?")[0]  # Eliminar parámetros de consulta
                            format_detected = os.path.splitext(url_path)[1].lower().replace(".", "")
                            if not format_detected:
                                format_detected = "jpeg"  # Asumir JPEG
                            return data, format_detected
                        else:
                            raise ValueError(f"Error al descargar imagen de URL: {response.status}")
            
            # Si tiene path, leer el archivo
            elif "path" in image_data:
                path = image_data["path"]
                if not os.path.exists(path):
                    raise FileNotFoundError(f"No se encontró el archivo de imagen: {path}")
                
                with open(path, "rb") as f:
                    data = f.read()
                format_detected = os.path.splitext(path)[1].lower().replace(".", "")
                if not format_detected:
                    format_detected = "jpeg"  # Asumir JPEG
                return data, format_detected
            
            # Si tiene base64, extraer
            elif "base64" in image_data:
                base64_data = image_data["base64"]
                format_detected = image_data.get("format", "jpeg")  # Usar formato proporcionado o asumir JPEG
                return base64.b64decode(base64_data), format_detected
        
        raise ValueError("Formato de imagen no soportado")
    
    async def _detect_text_heuristic(self, img: Image.Image) -> bool:
        """
        Aplica una heurística simple para detectar si una imagen contiene texto.
        
        Args:
            img: Imagen PIL
            
        Returns:
            bool: True si se detecta que la imagen probablemente contiene texto
        """
        # Convertir a escala de grises
        gray_img = img.convert('L')
        
        # Redimensionar para análisis más rápido si es necesario
        if gray_img.width > 1000 or gray_img.height > 1000:
            ratio = min(1000 / gray_img.width, 1000 / gray_img.height)
            analysis_img = gray_img.resize((int(gray_img.width * ratio), int(gray_img.height * ratio)), Image.LANCZOS)
        else:
            analysis_img = gray_img
        
        # Aplicar detección de bordes
        edges = ImageOps.equalize(analysis_img)
        
        # Convertir a array para análisis
        import numpy as np
        img_array = np.array(edges)
        
        # Calcular varianza local (alta en áreas con texto)
        from scipy.ndimage import uniform_filter, uniform_filter1d
        
        # Calcular media local
        mean = uniform_filter(img_array, size=3)
        
        # Calcular varianza local
        var = uniform_filter(img_array**2, size=3) - mean**2
        
        # Umbral para considerar que hay texto
        text_threshold = np.percentile(var, 95)  # Ajustar según necesidad
        high_var_ratio = np.sum(var > text_threshold) / var.size
        
        # Detección de líneas horizontales (común en texto)
        h_edges = np.abs(np.diff(img_array, axis=1))
        h_lines = np.sum(h_edges > np.percentile(h_edges, 90), axis=1)
        h_line_pattern = np.sum(np.diff(h_lines > np.percentile(h_lines, 75)) != 0)
        
        # Heurística combinada
        has_text = high_var_ratio > 0.15 or h_line_pattern > img_array.shape[0] * 0.1
        
        return has_text
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del optimizador.
        
        Returns:
            Dict[str, Any]: Estadísticas del optimizador
        """
        return {
            **self.stats,
            "compression_ratio": self.stats["bytes_before"] / self.stats["bytes_after"] 
                if self.stats["bytes_after"] > 0 else 1.0,
            "average_saving_per_image": self.stats["bytes_saved"] / self.stats["images_processed"] 
                if self.stats["images_processed"] > 0 else 0
        }


# Instancia global del optimizador
image_optimizer = ImageOptimizer()
