"""
Sistema de reconocimiento de objetos específicos.

Este módulo proporciona funcionalidades para reconocer objetos específicos
en imágenes, permitiendo la identificación y etiquetado de elementos relevantes
para dominios particulares.
"""

import asyncio
import base64
import io
import os
import time
from typing import Dict, Any, Optional, Union, List, Tuple

from PIL import Image

from core.logging_config import get_logger
from core.telemetry import Telemetry
from core.image_cache import image_cache
from core.vision_metrics import vision_metrics

# Configurar logger
logger = get_logger(__name__)


class ObjectRecognition:
    """
    Sistema de reconocimiento de objetos específicos.

    Proporciona métodos para detectar y etiquetar objetos específicos en imágenes,
    con soporte para dominios personalizados y entrenamiento de modelos.
    """

    def __init__(self, telemetry: Optional[Telemetry] = None):
        """
        Inicializa el sistema de reconocimiento de objetos.

        Args:
            telemetry: Instancia de Telemetry para métricas y trazas (opcional)
        """
        self.telemetry = telemetry
        self.lock = asyncio.Lock()

        # Dominios disponibles
        self.domains = {
            "general": {
                "name": "Objetos generales",
                "description": "Reconocimiento de objetos comunes como personas, vehículos, animales, etc.",
                "objects": [
                    "persona",
                    "coche",
                    "bicicleta",
                    "moto",
                    "avión",
                    "autobús",
                    "tren",
                    "camión",
                    "barco",
                    "semáforo",
                    "hidrante",
                    "señal de stop",
                    "parquímetro",
                    "banco",
                    "pájaro",
                    "gato",
                    "perro",
                    "caballo",
                    "oveja",
                    "vaca",
                    "elefante",
                    "oso",
                    "cebra",
                    "jirafa",
                    "mochila",
                    "paraguas",
                    "bolso",
                    "corbata",
                    "maleta",
                    "frisbee",
                    "esquís",
                    "tabla de snowboard",
                    "pelota",
                    "cometa",
                    "bate",
                    "guante",
                    "patineta",
                    "tabla de surf",
                    "raqueta",
                    "botella",
                    "copa",
                    "taza",
                    "tenedor",
                    "cuchillo",
                    "cuchara",
                    "cuenco",
                    "plátano",
                    "manzana",
                    "sándwich",
                    "naranja",
                    "brócoli",
                    "zanahoria",
                    "perrito caliente",
                    "pizza",
                    "dona",
                    "pastel",
                    "silla",
                    "sofá",
                    "planta",
                    "cama",
                    "mesa",
                    "inodoro",
                    "televisión",
                    "portátil",
                    "ratón",
                    "control remoto",
                    "teclado",
                    "teléfono",
                    "microondas",
                    "horno",
                    "tostadora",
                    "fregadero",
                    "refrigerador",
                    "libro",
                    "reloj",
                    "florero",
                    "tijeras",
                    "oso de peluche",
                    "secador de pelo",
                    "cepillo de dientes",
                ],
            },
            "medical": {
                "name": "Imágenes médicas",
                "description": "Reconocimiento de elementos en imágenes médicas como radiografías, resonancias, etc.",
                "objects": [
                    "fractura",
                    "tumor",
                    "quiste",
                    "nódulo",
                    "hemorragia",
                    "edema",
                    "inflamación",
                    "calcificación",
                    "estenosis",
                    "aneurisma",
                    "atrofia",
                    "hipertrofia",
                    "metástasis",
                    "neumotórax",
                    "derrame pleural",
                    "consolidación",
                    "enfisema",
                    "fibrosis",
                    "cardiomegalia",
                    "osteoporosis",
                    "artritis",
                    "escoliosis",
                    "hernia discal",
                ],
            },
            "industrial": {
                "name": "Inspección industrial",
                "description": "Reconocimiento de elementos en entornos industriales y de manufactura",
                "objects": [
                    "grieta",
                    "corrosión",
                    "desgaste",
                    "deformación",
                    "rotura",
                    "soldadura defectuosa",
                    "tornillo suelto",
                    "fuga",
                    "sobrecalentamiento",
                    "desalineación",
                    "vibración excesiva",
                    "contaminación",
                    "obstrucción",
                    "falta de componente",
                    "componente incorrecto",
                    "etiqueta faltante",
                    "código de barras ilegible",
                    "embalaje dañado",
                ],
            },
            "retail": {
                "name": "Comercio minorista",
                "description": "Reconocimiento de productos y elementos en entornos de retail",
                "objects": [
                    "producto",
                    "estantería",
                    "etiqueta de precio",
                    "código de barras",
                    "caja registradora",
                    "carrito de compra",
                    "cesta",
                    "cliente",
                    "vendedor",
                    "probador",
                    "escaparate",
                    "promoción",
                    "descuento",
                    "oferta",
                    "pago",
                    "recibo",
                    "bolsa",
                    "seguridad",
                    "cámara",
                ],
            },
            "custom": {
                "name": "Dominio personalizado",
                "description": "Dominio personalizado para objetos específicos",
                "objects": [],
            },
        }

        # Estadísticas
        self.stats = {
            "images_processed": 0,
            "objects_detected": 0,
            "by_domain": {},
            "errors": 0,
            "processing_time_ms": 0,
        }

        # Inicializar estadísticas por dominio
        for domain in self.domains:
            self.stats["by_domain"][domain] = {
                "images_processed": 0,
                "objects_detected": 0,
            }

        logger.info("ObjectRecognition inicializado")

    async def recognize_objects(
        self,
        image_data: Union[str, bytes, Dict[str, Any]],
        domain: str = "general",
        confidence_threshold: float = 0.5,
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Reconoce objetos en una imagen para un dominio específico.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            domain: Dominio de objetos a reconocer (general, medical, industrial, retail, custom)
            confidence_threshold: Umbral de confianza para incluir detecciones (0.0-1.0)
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Objetos reconocidos y metadatos
        """
        span = None
        start_time = time.time()

        if self.telemetry:
            span = self.telemetry.start_span("object_recognition.recognize_objects")
            self.telemetry.add_span_attribute(span, "domain", domain)
            self.telemetry.add_span_attribute(
                span, "confidence_threshold", confidence_threshold
            )
            self.telemetry.add_span_attribute(span, "agent_id", agent_id)

        try:
            # Verificar que el dominio existe
            if domain not in self.domains:
                raise ValueError(
                    f"Dominio no válido: {domain}. Dominios disponibles: {', '.join(self.domains.keys())}"
                )

            # Procesar la entrada de imagen
            processed_image, image_format, image_size = await self._process_image_input(
                image_data
            )

            # Generar clave para caché
            cache_key = await image_cache.generate_key(
                processed_image,
                {
                    "operation": "recognize_objects",
                    "domain": domain,
                    "confidence_threshold": confidence_threshold,
                },
            )

            # Verificar caché
            cached_result = await image_cache.get(cache_key, "recognize_objects")
            if cached_result:
                # Registrar métricas de caché hit
                await vision_metrics.record_cache_operation(hit=True)

                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "cache_hit", True)
                    self.telemetry.record_metric("object_recognition.cache_hits", 1)

                logger.debug(f"Caché hit para recognize_objects con clave: {cache_key}")
                return cached_result

            # Registrar métricas de caché miss
            await vision_metrics.record_cache_operation(hit=False)

            if self.telemetry:
                self.telemetry.add_span_attribute(span, "cache_hit", False)
                self.telemetry.record_metric("object_recognition.cache_misses", 1)

            # Implementar el reconocimiento de objetos
            # Aquí se implementaría la lógica para detectar objetos específicos
            # usando modelos de ML entrenados para cada dominio

            # Simulación de reconocimiento de objetos para este ejemplo
            detections = await self._detect_objects(
                processed_image, domain, confidence_threshold
            )

            # Preparar resultado
            result = {
                "domain": domain,
                "domain_info": self.domains[domain],
                "detections": detections,
                "metadata": {
                    "object_count": len(detections),
                    "confidence_threshold": confidence_threshold,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }

            # Guardar en caché
            await image_cache.set(cache_key, result, image_size, "recognize_objects")

            # Actualizar estadísticas
            async with self.lock:
                self.stats["images_processed"] += 1
                self.stats["objects_detected"] += len(detections)
                self.stats["processing_time_ms"] += (time.time() - start_time) * 1000

                # Estadísticas por dominio
                self.stats["by_domain"][domain]["images_processed"] += 1
                self.stats["by_domain"][domain]["objects_detected"] += len(detections)

            # Registrar métricas
            latency_ms = (time.time() - start_time) * 1000
            await vision_metrics.record_api_call(
                operation="recognize_objects",
                agent_id=agent_id,
                success=True,
                latency_ms=latency_ms,
            )

            if self.telemetry:
                self.telemetry.add_span_attribute(span, "object_count", len(detections))
                self.telemetry.add_span_attribute(
                    span, "processing_time_ms", latency_ms
                )
                self.telemetry.record_metric(
                    "object_recognition.objects_detected",
                    len(detections),
                    {"domain": domain},
                )

            return result

        except Exception as e:
            # Actualizar estadísticas de error
            async with self.lock:
                self.stats["errors"] += 1

            # Registrar error
            logger.error(f"Error al reconocer objetos: {e}", exc_info=True)

            # Registrar métricas de error
            latency_ms = (time.time() - start_time) * 1000
            await vision_metrics.record_api_call(
                operation="recognize_objects",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=type(e).__name__,
            )

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)

            return {
                "error": str(e),
                "detections": [],
                "metadata": {
                    "error_type": type(e).__name__,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def register_custom_domain(
        self,
        domain_name: str,
        objects: List[str],
        description: str = "",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Registra un dominio personalizado con objetos específicos.

        Args:
            domain_name: Nombre del dominio personalizado
            objects: Lista de objetos a reconocer en este dominio
            description: Descripción del dominio
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Información del dominio registrado
        """
        span = None

        if self.telemetry:
            span = self.telemetry.start_span(
                "object_recognition.register_custom_domain"
            )
            self.telemetry.add_span_attribute(span, "domain_name", domain_name)
            self.telemetry.add_span_attribute(span, "object_count", len(objects))
            self.telemetry.add_span_attribute(span, "agent_id", agent_id)

        try:
            # Validar entrada
            if not domain_name or not objects:
                raise ValueError(
                    "Se requiere un nombre de dominio y al menos un objeto"
                )

            # Normalizar nombre de dominio
            domain_key = domain_name.lower().replace(" ", "_")

            # Registrar dominio
            async with self.lock:
                self.domains[domain_key] = {
                    "name": domain_name,
                    "description": description
                    or f"Dominio personalizado: {domain_name}",
                    "objects": objects,
                    "custom": True,
                }

                # Inicializar estadísticas para el nuevo dominio
                self.stats["by_domain"][domain_key] = {
                    "images_processed": 0,
                    "objects_detected": 0,
                }

            logger.info(
                f"Dominio personalizado registrado: {domain_name} con {len(objects)} objetos"
            )

            if self.telemetry:
                self.telemetry.record_metric(
                    "object_recognition.custom_domains_registered", 1
                )

            return {
                "domain_key": domain_key,
                "name": domain_name,
                "description": description,
                "objects": objects,
                "status": "registered",
            }

        except Exception as e:
            # Registrar error
            logger.error(
                f"Error al registrar dominio personalizado: {e}", exc_info=True
            )

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)

            return {"error": str(e), "status": "error"}
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def _process_image_input(
        self, image_data: Union[str, bytes, Dict[str, Any]]
    ) -> Tuple[bytes, str, int]:
        """
        Procesa la entrada de imagen en diferentes formatos.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)

        Returns:
            Tuple[bytes, str, int]: Bytes de la imagen, formato detectado y tamaño
        """
        # Si ya es bytes, devolver directamente
        if isinstance(image_data, bytes):
            return image_data, "unknown", len(image_data)

        # Si es una cadena base64, decodificar
        if isinstance(image_data, str) and image_data.startswith(
            ("data:image", "base64:")
        ):
            # Extraer la parte base64 si tiene prefijo
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            elif image_data.startswith("base64:"):
                image_data = image_data[7:]

            # Decodificar
            image_bytes = base64.b64decode(image_data)
            return image_bytes, "unknown", len(image_bytes)

        # Si es un diccionario, procesar según las claves
        if isinstance(image_data, dict):
            # Si tiene URL, descargar la imagen
            if "url" in image_data:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get(image_data["url"]) as response:
                        if response.status == 200:
                            data = await response.read()
                            format_detected = (
                                os.path.splitext(image_data["url"])[1]
                                .lower()
                                .replace(".", "")
                            )
                            if not format_detected:
                                format_detected = "jpeg"  # Asumir JPEG
                            return data, format_detected, len(data)
                        else:
                            raise ValueError(
                                f"Error al descargar imagen de URL: {response.status}"
                            )

            # Si tiene path, leer el archivo
            elif "path" in image_data:
                path = image_data["path"]
                if not os.path.exists(path):
                    raise FileNotFoundError(
                        f"No se encontró el archivo de imagen: {path}"
                    )

                with open(path, "rb") as f:
                    data = f.read()
                format_detected = os.path.splitext(path)[1].lower().replace(".", "")
                if not format_detected:
                    format_detected = "jpeg"  # Asumir JPEG
                return data, format_detected, len(data)

            # Si tiene base64, extraer
            elif "base64" in image_data:
                base64_data = image_data["base64"]
                format_detected = image_data.get(
                    "format", "jpeg"
                )  # Usar formato proporcionado o asumir JPEG
                image_bytes = base64.b64decode(base64_data)
                return image_bytes, format_detected, len(image_bytes)

        # Si es una cadena que no es base64, asumir que es una ruta de archivo
        if isinstance(image_data, str):
            if not os.path.exists(image_data):
                raise FileNotFoundError(
                    f"No se encontró el archivo de imagen: {image_data}"
                )

            with open(image_data, "rb") as f:
                data = f.read()
            format_detected = os.path.splitext(image_data)[1].lower().replace(".", "")
            if not format_detected:
                format_detected = "jpeg"  # Asumir JPEG
            return data, format_detected, len(data)

        raise ValueError("Formato de imagen no soportado")

    async def _detect_objects(
        self, image_bytes: bytes, domain: str, confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Detecta objetos en una imagen para un dominio específico.

        Args:
            image_bytes: Bytes de la imagen
            domain: Dominio de objetos a reconocer
            confidence_threshold: Umbral de confianza para incluir detecciones

        Returns:
            List[Dict[str, Any]]: Lista de objetos detectados
        """
        # Implementación simulada para este ejemplo
        # En una implementación real, se utilizaría un modelo de ML para detectar objetos

        # Abrir la imagen con PIL
        img = Image.open(io.BytesIO(image_bytes))

        # Obtener lista de objetos posibles para este dominio
        possible_objects = self.domains[domain]["objects"]

        # Simulación de detección de objetos
        # En una implementación real, aquí se utilizaría un modelo de visión por computadora

        # Simulamos la detección de 1-5 objetos
        import random

        num_objects = random.randint(1, min(5, len(possible_objects)))

        detections = []
        used_objects = set()

        for i in range(num_objects):
            # Seleccionar objeto no utilizado
            available_objects = [
                obj for obj in possible_objects if obj not in used_objects
            ]
            if not available_objects:
                break

            object_name = random.choice(available_objects)
            used_objects.add(object_name)

            # Generar posición aleatoria en la imagen
            x = random.randint(0, img.width - 100)
            y = random.randint(0, img.height - 100)
            width = random.randint(50, min(200, img.width - x))
            height = random.randint(50, min(200, img.height - y))

            # Generar confianza aleatoria por encima del umbral
            confidence = random.uniform(confidence_threshold, 1.0)

            # Crear detección
            detection = {
                "object_id": f"obj_{i+1}",
                "label": object_name,
                "confidence": round(confidence, 3),
                "bounding_box": {"x": x, "y": y, "width": width, "height": height},
            }

            detections.append(detection)

        # Ordenar por confianza descendente
        detections.sort(key=lambda x: x["confidence"], reverse=True)

        return detections

    async def get_available_domains(self) -> Dict[str, Any]:
        """
        Obtiene la lista de dominios disponibles para reconocimiento de objetos.

        Returns:
            Dict[str, Any]: Información de dominios disponibles
        """
        async with self.lock:
            return {"domains": self.domains, "count": len(self.domains)}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de reconocimiento de objetos.

        Returns:
            Dict[str, Any]: Estadísticas del sistema
        """
        async with self.lock:
            avg_processing_time = (
                self.stats["processing_time_ms"] / self.stats["images_processed"]
                if self.stats["images_processed"] > 0
                else 0
            )

            return {**self.stats, "avg_processing_time_ms": avg_processing_time}


# Instancia global del sistema de reconocimiento de objetos
object_recognition = ObjectRecognition()
