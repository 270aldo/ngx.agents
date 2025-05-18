"""
Cliente para procesamiento de documentos con Vertex AI Document AI.

Este módulo proporciona un cliente para procesar documentos utilizando
Vertex AI Document AI, con capacidades para extraer texto, clasificar documentos
y procesar formularios.
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple, Union

from google.cloud import documentai_v1 as documentai
from google.api_core.exceptions import GoogleAPIError

from clients.base_client import BaseClient
from core.circuit_breaker import CircuitBreaker

class DocumentClient(BaseClient):
    """Cliente para procesamiento de documentos con Vertex AI Document AI."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa el cliente de procesamiento de documentos.

        Args:
            config: Configuración opcional para el cliente.
                Puede incluir:
                - project_id: ID del proyecto de Google Cloud
                - location: Ubicación de los procesadores (ej. 'us', 'eu')
                - processor_id: ID del procesador de documentos predeterminado
                - timeout: Tiempo máximo de espera para operaciones (segundos)
                - mock_mode: Modo simulado para pruebas sin API real
                - circuit_breaker_config: Configuración del circuit breaker
        """
        super().__init__(name="DocumentClient")
        self.config = config or {}
        
        # Configuración básica
        self.project_id = self.config.get("project_id") or os.environ.get(
            "GOOGLE_CLOUD_PROJECT"
        )
        self.location = self.config.get("location") or os.environ.get(
            "DOCUMENT_AI_LOCATION", "us"
        )
        self.processor_id = self.config.get("processor_id") or os.environ.get(
            "DOCUMENT_AI_PROCESSOR_ID"
        )
        self.timeout = self.config.get("timeout") or int(os.environ.get(
            "DOCUMENT_AI_TIMEOUT", "60"
        ))
        
        # Modo simulado para pruebas
        self.mock_mode = self.config.get("mock_mode", False)
        if not self.project_id or not self.processor_id:
            self.logger.warning(
                "No se encontró project_id o processor_id. Activando modo simulado."
            )
            self.mock_mode = True
        
        # Inicializar cliente de Document AI
        if not self.mock_mode:
            try:
                self.client = documentai.DocumentProcessorServiceClient()
                self.logger.info("Cliente Document AI inicializado correctamente.")
            except Exception as e:
                self.logger.error(f"Error al inicializar cliente Document AI: {e}")
                self.mock_mode = True
                self.client = None
        else:
            self.logger.info("Inicializando en modo simulado.")
            self.client = None
        
        # Inicializar circuit breaker
        cb_config = self.config.get("circuit_breaker_config", {})
        self.circuit_breaker = CircuitBreaker(
            name="document_ai",
            failure_threshold=cb_config.get("failure_threshold", 5),
            recovery_timeout=cb_config.get("recovery_timeout", 30),
            expected_exception=GoogleAPIError,
        )
        
        # Estadísticas
        self.stats = {
            "process_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "total_latency_ms": 0,
            "mock_mode": self.mock_mode,
            "processor_types": {},
        }

    async def process_document(
        self, 
        document_data: bytes, 
        processor_id: Optional[str] = None,
        mime_type: str = "application/pdf",
        process_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Procesa un documento utilizando Document AI.

        Args:
            document_data: Datos binarios del documento a procesar.
            processor_id: ID del procesador a utilizar. Si no se proporciona,
                se utilizará el procesador predeterminado.
            mime_type: Tipo MIME del documento (ej. 'application/pdf', 'image/jpeg').
            process_options: Opciones adicionales para el procesamiento.

        Returns:
            Diccionario con los resultados del procesamiento.
        """
        start_time = time.time()
        processor_id = processor_id or self.processor_id
        process_options = process_options or {}
        
        try:
            # Verificar si el circuit breaker está abierto
            if self.circuit_breaker.is_open():
                self.logger.warning("Circuit breaker abierto. Usando respuesta simulada.")
                result = await self._mock_process_document(document_data, mime_type)
                self.stats["errors"] += 1
                return result
            
            # Modo simulado
            if self.mock_mode:
                self.logger.info("Procesando documento en modo simulado.")
                result = await self._mock_process_document(document_data, mime_type)
                self._update_stats(start_time)
                return result
            
            # Procesar documento con Document AI
            with self.circuit_breaker:
                # Preparar solicitud
                name = f"projects/{self.project_id}/locations/{self.location}/processors/{processor_id}"
                document = documentai.Document(
                    content=document_data,
                    mime_type=mime_type
                )
                
                # Configurar opciones de procesamiento
                request = documentai.ProcessRequest(
                    name=name,
                    raw_document=documentai.RawDocument(
                        content=document_data,
                        mime_type=mime_type
                    )
                )
                
                # Procesar documento
                self.logger.info(f"Procesando documento con procesador {processor_id}")
                response = self.client.process_document(request=request)
                
                # Convertir respuesta a diccionario
                result = self._convert_document_to_dict(response.document)
                
                # Actualizar estadísticas
                self._update_stats(start_time)
                
                # Registrar tipo de procesador
                processor_type = self._get_processor_type(processor_id)
                if processor_type not in self.stats["processor_types"]:
                    self.stats["processor_types"][processor_type] = 0
                self.stats["processor_types"][processor_type] += 1
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error al procesar documento: {e}")
            self.stats["errors"] += 1
            
            # Respuesta de error
            return {
                "error": str(e),
                "success": False,
                "text": "",
                "pages": [],
                "entities": [],
                "mime_type": mime_type
            }
        finally:
            # Actualizar latencia incluso en caso de error
            elapsed_ms = (time.time() - start_time) * 1000
            self._update_latency_stats(elapsed_ms)

    async def batch_process_documents(
        self,
        documents: List[Tuple[bytes, str]],
        processor_id: Optional[str] = None,
        process_options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Procesa múltiples documentos en batch.

        Args:
            documents: Lista de tuplas (document_data, mime_type).
            processor_id: ID del procesador a utilizar.
            process_options: Opciones adicionales para el procesamiento.

        Returns:
            Lista de resultados de procesamiento para cada documento.
        """
        processor_id = processor_id or self.processor_id
        process_options = process_options or {}
        
        # Procesar documentos en paralelo
        tasks = []
        for doc_data, mime_type in documents:
            task = asyncio.create_task(
                self.process_document(doc_data, processor_id, mime_type, process_options)
            )
            tasks.append(task)
        
        # Esperar a que todos los documentos se procesen
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Manejar excepciones
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error al procesar documento {i}: {result}")
                processed_results.append({
                    "error": str(result),
                    "success": False,
                    "text": "",
                    "pages": [],
                    "entities": [],
                    "mime_type": documents[i][1]
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def extract_text(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf",
        processor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae texto de un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.
            processor_id: ID del procesador a utilizar.

        Returns:
            Diccionario con el texto extraído y metadatos.
        """
        # Usar procesador de OCR o general
        processor_id = processor_id or os.environ.get(
            "DOCUMENT_AI_OCR_PROCESSOR_ID", self.processor_id
        )
        
        # Procesar documento
        result = await self.process_document(
            document_data, processor_id, mime_type
        )
        
        # Extraer solo la información de texto
        if "error" in result:
            return result
        
        return {
            "text": result.get("text", ""),
            "pages": result.get("pages", []),
            "success": True,
            "mime_type": mime_type
        }

    async def classify_document(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf",
        processor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clasifica un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.
            processor_id: ID del procesador de clasificación a utilizar.

        Returns:
            Diccionario con las clases detectadas y confianza.
        """
        # Usar procesador de clasificación
        processor_id = processor_id or os.environ.get(
            "DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID", self.processor_id
        )
        
        # Procesar documento
        result = await self.process_document(
            document_data, processor_id, mime_type
        )
        
        # Extraer información de clasificación
        if "error" in result:
            return result
        
        # Extraer clases de las entidades
        classifications = []
        if "entities" in result:
            for entity in result.get("entities", []):
                if entity.get("type") == "classification":
                    classifications.append({
                        "name": entity.get("mention_text", ""),
                        "confidence": entity.get("confidence", 0.0)
                    })
        
        return {
            "classifications": classifications,
            "document_type": self._determine_document_type(classifications),
            "confidence": self._get_max_confidence(classifications),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def extract_entities(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf",
        processor_id: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae entidades de un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.
            processor_id: ID del procesador de entidades a utilizar.
            document_type: Tipo de documento para seleccionar el procesador adecuado.

        Returns:
            Diccionario con las entidades extraídas.
        """
        # Seleccionar procesador basado en el tipo de documento
        if document_type:
            processor_id = self._get_processor_for_document_type(document_type)
        
        processor_id = processor_id or os.environ.get(
            "DOCUMENT_AI_ENTITY_PROCESSOR_ID", self.processor_id
        )
        
        # Procesar documento
        result = await self.process_document(
            document_data, processor_id, mime_type
        )
        
        # Extraer solo la información de entidades
        if "error" in result:
            return result
        
        # Organizar entidades por tipo
        entities_by_type = {}
        for entity in result.get("entities", []):
            entity_type = entity.get("type", "unknown")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        return {
            "entities": result.get("entities", []),
            "entities_by_type": entities_by_type,
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def process_form(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf",
        processor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Procesa un formulario para extraer campos clave-valor.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.
            processor_id: ID del procesador de formularios a utilizar.

        Returns:
            Diccionario con los campos del formulario extraídos.
        """
        # Usar procesador de formularios
        processor_id = processor_id or os.environ.get(
            "DOCUMENT_AI_FORM_PROCESSOR_ID", self.processor_id
        )
        
        # Procesar documento
        result = await self.process_document(
            document_data, processor_id, mime_type
        )
        
        # Extraer información de formulario
        if "error" in result:
            return result
        
        # Extraer pares clave-valor
        form_fields = {}
        for entity in result.get("entities", []):
            if entity.get("type") == "form_field":
                key = entity.get("properties", {}).get("key", {}).get("mention_text", "")
                value = entity.get("properties", {}).get("value", {}).get("mention_text", "")
                if key:
                    form_fields[key] = value
        
        return {
            "form_fields": form_fields,
            "entities": result.get("entities", []),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def get_available_processors(self) -> Dict[str, Any]:
        """Obtiene los procesadores disponibles en el proyecto.

        Returns:
            Diccionario con información sobre los procesadores disponibles.
        """
        if self.mock_mode:
            return self._mock_available_processors()
        
        try:
            with self.circuit_breaker:
                parent = f"projects/{self.project_id}/locations/{self.location}"
                response = self.client.list_processors(parent=parent)
                
                processors = []
                for processor in response:
                    processors.append({
                        "name": processor.name,
                        "display_name": processor.display_name,
                        "type": processor.type_,
                        "state": processor.state.name,
                        "processor_id": processor.name.split("/")[-1]
                    })
                
                return {
                    "processors": processors,
                    "success": True,
                    "count": len(processors)
                }
        except Exception as e:
            self.logger.error(f"Error al obtener procesadores disponibles: {e}")
            self.stats["errors"] += 1
            return {
                "error": str(e),
                "success": False,
                "processors": [],
                "count": 0
            }

    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cliente.

        Returns:
            Diccionario con estadísticas de uso.
        """
        return self.stats

    def _update_stats(self, start_time: float) -> None:
        """Actualiza las estadísticas después de una operación.

        Args:
            start_time: Tiempo de inicio de la operación.
        """
        self.stats["process_operations"] += 1
        elapsed_ms = (time.time() - start_time) * 1000
        self._update_latency_stats(elapsed_ms)

    def _update_latency_stats(self, elapsed_ms: float) -> None:
        """Actualiza las estadísticas de latencia.

        Args:
            elapsed_ms: Tiempo transcurrido en milisegundos.
        """
        self.stats["total_latency_ms"] += elapsed_ms
        if self.stats["process_operations"] > 0:
            self.stats["avg_latency_ms"] = (
                self.stats["total_latency_ms"] / self.stats["process_operations"]
            )

    def _convert_document_to_dict(self, document: Any) -> Dict[str, Any]:
        """Convierte un objeto Document de Document AI a un diccionario.

        Args:
            document: Objeto Document de Document AI.

        Returns:
            Diccionario con la información del documento.
        """
        # Extraer texto
        text = document.text
        
        # Extraer páginas
        pages = []
        for page in document.pages:
            page_dict = {
                "page_number": page.page_number,
                "width": page.dimension.width,
                "height": page.dimension.height,
                "blocks": [],
                "paragraphs": [],
                "lines": [],
                "tokens": []
            }
            
            # Extraer bloques
            for block in page.blocks:
                block_dict = {
                    "layout": self._convert_layout_to_dict(block.layout),
                    "text": text[block.layout.text_anchor.text_segments[0].start_index:
                               block.layout.text_anchor.text_segments[0].end_index]
                    if block.layout.text_anchor.text_segments else ""
                }
                page_dict["blocks"].append(block_dict)
            
            # Extraer párrafos
            for paragraph in page.paragraphs:
                para_dict = {
                    "layout": self._convert_layout_to_dict(paragraph.layout),
                    "text": text[paragraph.layout.text_anchor.text_segments[0].start_index:
                                paragraph.layout.text_anchor.text_segments[0].end_index]
                    if paragraph.layout.text_anchor.text_segments else ""
                }
                page_dict["paragraphs"].append(para_dict)
            
            # Extraer líneas
            for line in page.lines:
                line_dict = {
                    "layout": self._convert_layout_to_dict(line.layout),
                    "text": text[line.layout.text_anchor.text_segments[0].start_index:
                              line.layout.text_anchor.text_segments[0].end_index]
                    if line.layout.text_anchor.text_segments else ""
                }
                page_dict["lines"].append(line_dict)
            
            # Extraer tokens
            for token in page.tokens:
                token_dict = {
                    "layout": self._convert_layout_to_dict(token.layout),
                    "text": text[token.layout.text_anchor.text_segments[0].start_index:
                               token.layout.text_anchor.text_segments[0].end_index]
                    if token.layout.text_anchor.text_segments else "",
                    "confidence": token.confidence
                }
                page_dict["tokens"].append(token_dict)
            
            pages.append(page_dict)
        
        # Extraer entidades
        entities = []
        for entity in document.entities:
            entity_dict = {
                "type": entity.type_,
                "mention_text": text[entity.text_anchor.text_segments[0].start_index:
                                    entity.text_anchor.text_segments[0].end_index]
                if entity.text_anchor.text_segments else "",
                "confidence": entity.confidence,
                "page_anchor": [page.page_ref for page in entity.page_anchor.page_refs] if entity.page_anchor else [],
                "properties": []
            }
            
            # Extraer propiedades de la entidad
            if hasattr(entity, "properties") and entity.properties:
                properties = {}
                for prop in entity.properties:
                    prop_dict = {
                        "type": prop.type_,
                        "mention_text": text[prop.text_anchor.text_segments[0].start_index:
                                            prop.text_anchor.text_segments[0].end_index]
                        if prop.text_anchor.text_segments else "",
                        "confidence": prop.confidence
                    }
                    properties[prop.type_] = prop_dict
                
                entity_dict["properties"] = properties
            
            entities.append(entity_dict)
        
        # Construir resultado
        result = {
            "text": text,
            "pages": pages,
            "entities": entities,
            "mime_type": document.mime_type,
            "success": True
        }
        
        return result

    def _convert_layout_to_dict(self, layout: Any) -> Dict[str, Any]:
        """Convierte un objeto Layout a un diccionario.

        Args:
            layout: Objeto Layout de Document AI.

        Returns:
            Diccionario con la información del layout.
        """
        if not layout:
            return {}
        
        # Extraer bounding box
        bounding_poly = {}
        if hasattr(layout, "bounding_poly") and layout.bounding_poly:
            vertices = []
            for vertex in layout.bounding_poly.vertices:
                vertices.append({"x": vertex.x, "y": vertex.y})
            bounding_poly = {"vertices": vertices}
        
        # Extraer text anchor
        text_anchor = {}
        if hasattr(layout, "text_anchor") and layout.text_anchor:
            segments = []
            for segment in layout.text_anchor.text_segments:
                segments.append({
                    "start_index": segment.start_index,
                    "end_index": segment.end_index
                })
            text_anchor = {"text_segments": segments}
        
        return {
            "bounding_poly": bounding_poly,
            "text_anchor": text_anchor,
            "orientation": layout.orientation.name if hasattr(layout, "orientation") else "ORIENTATION_UNSPECIFIED",
            "confidence": layout.confidence if hasattr(layout, "confidence") else 0.0
        }

    def _get_processor_type(self, processor_id: str) -> str:
        """Obtiene el tipo de un procesador.

        Args:
            processor_id: ID del procesador.

        Returns:
            Tipo del procesador.
        """
        # Mapeo de IDs a tipos
        processor_types = {
            "form-parser": "FORM_PARSER",
            "ocr": "OCR",
            "document-classifier": "DOCUMENT_CLASSIFIER",
            "entity-extraction": "ENTITY_EXTRACTION",
            "invoice-parser": "INVOICE_PARSER",
            "id-proofing": "ID_PROOFING"
        }
        
        # Intentar determinar el tipo por el ID
        for key, value in processor_types.items():
            if key in processor_id.lower():
                return value
        
        return "GENERAL"

    def _get_processor_for_document_type(self, document_type: str) -> Optional[str]:
        """Obtiene el ID del procesador adecuado para un tipo de documento.

        Args:
            document_type: Tipo de documento.

        Returns:
            ID del procesador o None si no se encuentra.
        """
        # Mapeo de tipos de documento a variables de entorno
        processor_env_vars = {
            "invoice": "DOCUMENT_AI_INVOICE_PROCESSOR_ID",
            "receipt": "DOCUMENT_AI_RECEIPT_PROCESSOR_ID",
            "id": "DOCUMENT_AI_ID_PROCESSOR_ID",
            "form": "DOCUMENT_AI_FORM_PROCESSOR_ID",
            "medical": "DOCUMENT_AI_MEDICAL_PROCESSOR_ID",
            "tax": "DOCUMENT_AI_TAX_PROCESSOR_ID"
        }
        
        # Buscar el tipo de documento
        for key, env_var in processor_env_vars.items():
            if key in document_type.lower():
                return os.environ.get(env_var, self.processor_id)
        
        return self.processor_id

    def _determine_document_type(self, classifications: List[Dict[str, Any]]) -> str:
        """Determina el tipo de documento basado en las clasificaciones.

        Args:
            classifications: Lista de clasificaciones.

        Returns:
            Tipo de documento determinado.
        """
        if not classifications:
            return "unknown"
        
        # Ordenar por confianza
        sorted_classes = sorted(
            classifications, 
            key=lambda x: x.get("confidence", 0.0),
            reverse=True
        )
        
        # Devolver la clase con mayor confianza
        return sorted_classes[0].get("name", "unknown")

    def _get_max_confidence(self, classifications: List[Dict[str, Any]]) -> float:
        """Obtiene la confianza máxima de las clasificaciones.

        Args:
            classifications: Lista de clasificaciones.

        Returns:
            Valor de confianza máximo.
        """
        if not classifications:
            return 0.0
        
        confidences = [c.get("confidence", 0.0) for c in classifications]
        return max(confidences) if confidences else 0.0

    async def _mock_process_document(
        self, 
        document_data: bytes, 
        mime_type: str
    ) -> Dict[str, Any]:
        """Genera una respuesta simulada para procesamiento de documentos.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Respuesta simulada.
        """
        # Generar texto simulado basado en el tipo MIME
        if "pdf" in mime_type:
            mock_text = "Este es un documento PDF simulado. Contiene texto de ejemplo para pruebas."
        elif "image" in mime_type:
            mock_text = "Esta es una imagen con texto simulado para pruebas de OCR."
        else:
            mock_text = "Este es un documento simulado para pruebas."
        
        # Generar entidades simuladas
        mock_entities = [
            {
                "type": "person_name",
                "mention_text": "Juan Pérez",
                "confidence": 0.95,
                "page_anchor": [1],
                "properties": {}
            },
            {
                "type": "email_address",
                "mention_text": "juan.perez@ejemplo.com",
                "confidence": 0.92,
                "page_anchor": [1],
                "properties": {}
            },
            {
                "type": "phone_number",
                "mention_text": "+34 612 345 678",
                "confidence": 0.89,
                "page_anchor": [1],
                "properties": {}
            }
        ]
        
        # Generar páginas simuladas
        mock_pages = [
            {
                "page_number": 1,
                "width": 612,
                "height": 792,
                "blocks": [
                    {
                        "layout": {
                            "bounding_poly": {
                                "vertices": [
                                    {"x": 50, "y": 50},
                                    {"x": 550, "y": 50},
                                    {"x": 550, "y": 100},
                                    {"x": 50, "y": 100}
                                ]
                            },
                            "text_anchor": {
                                "text_segments": [
                                    {"start_index": 0, "end_index": len(mock_text)}
                                ]
                            },
                            "orientation": "PAGE_UP",
                            "confidence": 0.98
                        },
                        "text": mock_text
                    }
                ],
                "paragraphs": [
                    {
                        "layout": {
                            "bounding_poly": {
                                "vertices": [
                                    {"x": 50, "y": 50},
                                    {"x": 550, "y": 50},
                                    {"x": 550, "y": 100},
                                    {"x": 50, "y": 100}
                                ]
                            },
                            "text_anchor": {
                                "text_segments": [
                                    {"start_index": 0, "end_index": len(mock_text)}
                                ]
                            },
                            "orientation": "PAGE_UP",
                            "confidence": 0.98
                        },
                        "text": mock_text
                    }
                ],
                "lines": [],
                "tokens": []
            }
        ]
        
        # Simular un pequeño retraso para ser realista
        await asyncio.sleep(0.2)
        
        return {
            "text": mock_text,
            "pages": mock_pages,
            "entities": mock_entities,
            "mime_type": mime_type,
            "success": True,
            "mock": True
        }

    def _mock_available_processors(self) -> Dict[str, Any]:
        """Genera una respuesta simulada para procesadores disponibles.

        Returns:
            Respuesta simulada con procesadores.
        """
        mock_processors = [
            {
                "name": f"projects/{self.project_id}/locations/{self.location}/processors/mock-form-parser",
                "display_name": "Mock Form Parser",
                "type": "FORM_PARSER",
                "state": "ENABLED",
                "processor_id": "mock-form-parser"
            },
            {
                "name": f"projects/{self.project_id}/locations/{self.location}/processors/mock-ocr",
                "display_name": "Mock OCR Processor",
                "type": "OCR",
                "state": "ENABLED",
                "processor_id": "mock-ocr"
            },
            {
                "name": f"projects/{self.project_id}/locations/{self.location}/processors/mock-document-classifier",
                "display_name": "Mock Document Classifier",
                "type": "DOCUMENT_CLASSIFIER",
                "state": "ENABLED",
                "processor_id": "mock-document-classifier"
            },
            {
                "name": f"projects/{self.project_id}/locations/{self.location}/processors/mock-entity-extraction",
                "display_name": "Mock Entity Extraction",
                "type": "ENTITY_EXTRACTION",
                "state": "ENABLED",
                "processor_id": "mock-entity-extraction"
            },
            {
                "name": f"projects/{self.project_id}/locations/{self.location}/processors/mock-invoice-parser",
                "display_name": "Mock Invoice Parser",
                "type": "INVOICE_PARSER",
                "state": "ENABLED",
                "processor_id": "mock-invoice-parser"
            }
        ]
        
        return {
            "processors": mock_processors,
            "success": True,
            "count": len(mock_processors),
            "mock": True
        }
