"""
Procesador de documentos para NGX Agents.

Este módulo proporciona un procesador central para el análisis y procesamiento
de documentos utilizando Vertex AI Document AI.
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple, Union, BinaryIO

from clients.vertex_ai.document.document_client import DocumentClient
from clients.vertex_ai.document.entity_extractor_client import EntityExtractorClient
from clients.vertex_ai.document.classifier_client import ClassifierClient

class DocumentProcessor:
    """Procesador central para análisis y procesamiento de documentos."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa el procesador de documentos.

        Args:
            config: Configuración opcional para el procesador.
                Puede incluir:
                - project_id: ID del proyecto de Google Cloud
                - location: Ubicación de los procesadores (ej. 'us', 'eu')
                - timeout: Tiempo máximo de espera para operaciones (segundos)
                - mock_mode: Modo simulado para pruebas sin API real
                - circuit_breaker_config: Configuración del circuit breaker
                - document_client: Cliente de Document AI existente
                - entity_extractor_client: Cliente de extracción de entidades existente
                - classifier_client: Cliente de clasificación existente
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        
        # Configuración básica
        self.project_id = self.config.get("project_id") or os.environ.get(
            "GOOGLE_CLOUD_PROJECT"
        )
        self.location = self.config.get("location") or os.environ.get(
            "DOCUMENT_AI_LOCATION", "us"
        )
        self.timeout = self.config.get("timeout") or int(os.environ.get(
            "DOCUMENT_AI_TIMEOUT", "60"
        ))
        
        # Modo simulado para pruebas
        self.mock_mode = self.config.get("mock_mode", False)
        if not self.project_id:
            self.logger.warning(
                "No se encontró project_id. Activando modo simulado."
            )
            self.mock_mode = True
        
        # Inicializar clientes
        self._initialize_clients()
        
        # Estadísticas
        self.stats = {
            "process_operations": 0,
            "extract_operations": 0,
            "classify_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "total_latency_ms": 0,
            "mock_mode": self.mock_mode,
            "document_types": {},
        }

    def _initialize_clients(self) -> None:
        """Inicializa los clientes necesarios para el procesamiento de documentos."""
        # Configuración común para los clientes
        client_config = {
            "project_id": self.project_id,
            "location": self.location,
            "timeout": self.timeout,
            "mock_mode": self.mock_mode,
            "circuit_breaker_config": self.config.get("circuit_breaker_config", {})
        }
        
        # Inicializar cliente de Document AI
        if "document_client" in self.config and self.config["document_client"]:
            self.document_client = self.config["document_client"]
            self.logger.info("Usando cliente Document AI proporcionado.")
        else:
            self.document_client = DocumentClient(client_config)
            self.logger.info("Cliente Document AI inicializado.")
        
        # Inicializar cliente de extracción de entidades
        if "entity_extractor_client" in self.config and self.config["entity_extractor_client"]:
            self.entity_extractor = self.config["entity_extractor_client"]
            self.logger.info("Usando cliente de extracción de entidades proporcionado.")
        else:
            entity_config = {**client_config, "document_client": self.document_client}
            self.entity_extractor = EntityExtractorClient(entity_config)
            self.logger.info("Cliente de extracción de entidades inicializado.")
        
        # Inicializar cliente de clasificación
        if "classifier_client" in self.config and self.config["classifier_client"]:
            self.classifier = self.config["classifier_client"]
            self.logger.info("Usando cliente de clasificación proporcionado.")
        else:
            classifier_config = {**client_config, "document_client": self.document_client}
            self.classifier = ClassifierClient(classifier_config)
            self.logger.info("Cliente de clasificación inicializado.")

    async def process_document(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None,
        processor_id: Optional[str] = None,
        document_type: Optional[str] = None,
        auto_classify: bool = False
    ) -> Dict[str, Any]:
        """Procesa un documento utilizando Document AI.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.
            processor_id: ID del procesador a utilizar.
            document_type: Tipo de documento para seleccionar el procesador adecuado.
            auto_classify: Si es True, clasifica automáticamente el documento y usa el procesador adecuado.

        Returns:
            Diccionario con los resultados del procesamiento.
        """
        start_time = time.time()
        
        try:
            # Preparar datos del documento
            document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
            mime_type = mime_type or detected_mime_type
            
            # Clasificar documento si es necesario
            if auto_classify and not processor_id and not document_type:
                self.logger.info("Clasificando documento automáticamente...")
                classifier_result = await self.classifier.get_document_processor(document_bytes, mime_type)
                
                if "error" in classifier_result:
                    self.logger.warning(f"Error al clasificar documento: {classifier_result['error']}")
                else:
                    processor_id = classifier_result["processor_id"]
                    document_type = classifier_result["document_type"]
                    self.logger.info(f"Documento clasificado como: {document_type}")
                    self.logger.info(f"Usando procesador: {processor_id}")
            
            # Procesar documento
            self.logger.info(f"Procesando documento de tipo {mime_type}...")
            result = await self.document_client.process_document(
                document_bytes, processor_id, mime_type
            )
            
            # Actualizar estadísticas
            self.stats["process_operations"] += 1
            if "error" not in result and document_type:
                if document_type not in self.stats["document_types"]:
                    self.stats["document_types"][document_type] = 0
                self.stats["document_types"][document_type] += 1
            
            # Añadir información de tipo de documento si está disponible
            if document_type:
                result["document_type"] = document_type
            
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
                "mime_type": mime_type or "unknown"
            }
        finally:
            # Actualizar latencia incluso en caso de error
            elapsed_ms = (time.time() - start_time) * 1000
            self._update_latency_stats(elapsed_ms)

    async def extract_text(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None,
        processor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae texto de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.
            processor_id: ID del procesador a utilizar.

        Returns:
            Diccionario con el texto extraído y metadatos.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Extraer texto
        return await self.document_client.extract_text(
            document_bytes, mime_type, processor_id
        )

    async def classify_document(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None,
        processor_id: Optional[str] = None,
        confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Clasifica un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.
            processor_id: ID del procesador a utilizar.
            confidence_threshold: Umbral de confianza para incluir clasificaciones.

        Returns:
            Diccionario con las clasificaciones del documento.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Actualizar estadísticas
        self.stats["classify_operations"] += 1
        
        # Clasificar documento
        return await self.classifier.classify_document(
            document_bytes, mime_type, processor_id, confidence_threshold
        )

    async def extract_entities(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None,
        processor_id: Optional[str] = None,
        document_type: Optional[str] = None,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extrae entidades de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.
            processor_id: ID del procesador a utilizar.
            document_type: Tipo de documento para seleccionar el procesador adecuado.
            entity_types: Lista de tipos de entidades a extraer (si se especifica).

        Returns:
            Diccionario con las entidades extraídas.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Actualizar estadísticas
        self.stats["extract_operations"] += 1
        
        # Extraer entidades
        return await self.entity_extractor.extract_entities(
            document_bytes, mime_type, processor_id, document_type, entity_types
        )

    async def process_form(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None,
        processor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Procesa un formulario para extraer campos clave-valor.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.
            processor_id: ID del procesador de formularios a utilizar.

        Returns:
            Diccionario con los campos del formulario extraídos.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Procesar formulario
        return await self.document_client.process_form(
            document_bytes, mime_type, processor_id
        )

    async def extract_personal_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae información personal de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.

        Returns:
            Diccionario con la información personal extraída.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Extraer información personal
        return await self.entity_extractor.extract_personal_information(
            document_bytes, mime_type
        )

    async def extract_business_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae información de negocios de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.

        Returns:
            Diccionario con la información de negocios extraída.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Extraer información de negocios
        return await self.entity_extractor.extract_business_information(
            document_bytes, mime_type
        )

    async def extract_medical_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae información médica de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.

        Returns:
            Diccionario con la información médica extraída.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Extraer información médica
        return await self.entity_extractor.extract_medical_information(
            document_bytes, mime_type
        )

    async def extract_invoice_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae información de facturas.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.

        Returns:
            Diccionario con la información de la factura extraída.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Extraer información de factura
        return await self.entity_extractor.extract_invoice_information(
            document_bytes, mime_type
        )

    async def extract_id_document_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extrae información de documentos de identidad.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.

        Returns:
            Diccionario con la información del documento de identidad extraída.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Extraer información de documento de identidad
        return await self.entity_extractor.extract_id_document_information(
            document_bytes, mime_type
        )

    async def analyze_document(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Realiza un análisis completo de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento. Si no se proporciona, se intentará detectar.

        Returns:
            Diccionario con los resultados del análisis completo.
        """
        # Preparar datos del documento
        document_bytes, detected_mime_type = await self._prepare_document_data(document_data, mime_type)
        mime_type = mime_type or detected_mime_type
        
        # Clasificar documento
        classify_result = await self.classifier.classify_document(document_bytes, mime_type)
        
        # Si hay error en la clasificación, devolver el resultado
        if "error" in classify_result:
            return classify_result
        
        # Obtener tipo de documento y procesador adecuado
        document_type = classify_result["document_type"]
        processor_result = await self.classifier.get_document_processor(document_bytes, mime_type)
        processor_id = processor_result.get("processor_id")
        
        # Extraer entidades según el tipo de documento
        if "invoice" in document_type.lower():
            entity_result = await self.entity_extractor.extract_invoice_information(document_bytes, mime_type)
        elif "id" in document_type.lower():
            entity_result = await self.entity_extractor.extract_id_document_information(document_bytes, mime_type)
        elif "medical" in document_type.lower():
            entity_result = await self.entity_extractor.extract_medical_information(document_bytes, mime_type)
        elif "form" in document_type.lower():
            entity_result = await self.document_client.process_form(document_bytes, mime_type, processor_id)
        else:
            # Para otros tipos, extraer entidades generales
            entity_result = await self.entity_extractor.extract_entities(document_bytes, mime_type, processor_id, document_type)
        
        # Combinar resultados
        result = {
            "document_type": document_type,
            "confidence": classify_result["confidence"],
            "classifications": classify_result["classifications"],
            "entities": entity_result.get("entities", []),
            "entities_by_type": entity_result.get("entities_by_type", {}),
            "text": entity_result.get("text", ""),
            "success": True,
            "mime_type": mime_type
        }
        
        # Añadir información específica según el tipo de documento
        if "invoice_info" in entity_result:
            result["invoice_info"] = entity_result["invoice_info"]
        elif "id_document_info" in entity_result:
            result["id_document_info"] = entity_result["id_document_info"]
        elif "medical_info" in entity_result:
            result["medical_info"] = entity_result["medical_info"]
        elif "form_fields" in entity_result:
            result["form_fields"] = entity_result["form_fields"]
        
        return result

    async def batch_process_documents(
        self,
        documents: List[Tuple[Union[bytes, BinaryIO, str], Optional[str]]],
        processor_id: Optional[str] = None,
        auto_classify: bool = False
    ) -> List[Dict[str, Any]]:
        """Procesa múltiples documentos en batch.

        Args:
            documents: Lista de tuplas (document_data, mime_type).
            processor_id: ID del procesador a utilizar.
            auto_classify: Si es True, clasifica automáticamente cada documento.

        Returns:
            Lista de resultados de procesamiento para cada documento.
        """
        # Preparar tareas para procesar documentos en paralelo
        tasks = []
        for doc_data, mime_type in documents:
            task = asyncio.create_task(
                self.process_document(doc_data, mime_type, processor_id, None, auto_classify)
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
                    "mime_type": documents[i][1] or "unknown"
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def get_available_processors(self) -> Dict[str, Any]:
        """Obtiene los procesadores disponibles en el proyecto.

        Returns:
            Diccionario con información sobre los procesadores disponibles.
        """
        return await self.document_client.get_available_processors()

    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del procesador de documentos.

        Returns:
            Diccionario con estadísticas de uso.
        """
        # Obtener estadísticas de los clientes
        document_client_stats = await self.document_client.get_stats()
        entity_extractor_stats = await self.entity_extractor.get_stats()
        classifier_stats = await self.classifier.get_stats()
        
        # Combinar estadísticas
        combined_stats = {
            **self.stats,
            "document_client_stats": document_client_stats,
            "entity_extractor_stats": entity_extractor_stats,
            "classifier_stats": classifier_stats
        }
        
        return combined_stats

    async def _prepare_document_data(
        self,
        document_data: Union[bytes, BinaryIO, str],
        mime_type: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """Prepara los datos del documento para su procesamiento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            mime_type: Tipo MIME del documento.

        Returns:
            Tupla con los datos binarios del documento y el tipo MIME detectado.
        """
        # Convertir a bytes si es necesario
        if isinstance(document_data, str):
            # Si es una ruta de archivo
            try:
                with open(document_data, 'rb') as f:
                    document_bytes = f.read()
                
                # Detectar tipo MIME si no se proporciona
                if not mime_type:
                    mime_type = self._detect_mime_type(document_data)
                
            except Exception as e:
                self.logger.error(f"Error al leer archivo: {e}")
                raise ValueError(f"No se pudo leer el archivo: {e}")
        
        elif hasattr(document_data, 'read') and callable(document_data.read):
            # Si es un objeto de archivo
            try:
                document_bytes = document_data.read()
                if hasattr(document_data, 'name'):
                    # Detectar tipo MIME si no se proporciona
                    if not mime_type:
                        mime_type = self._detect_mime_type(document_data.name)
                
            except Exception as e:
                self.logger.error(f"Error al leer archivo: {e}")
                raise ValueError(f"No se pudo leer el archivo: {e}")
        
        elif isinstance(document_data, bytes):
            # Si ya son bytes
            document_bytes = document_data
        
        else:
            raise ValueError("Formato de documento no soportado. Debe ser bytes, archivo o ruta.")
        
        # Si no se pudo detectar el tipo MIME, usar un valor predeterminado
        if not mime_type:
            # Intentar detectar por contenido
            mime_type = self._detect_mime_type_from_content(document_bytes)
        
        return document_bytes, mime_type

    def _detect_mime_type(self, file_path: str) -> str:
        """Detecta el tipo MIME basado en la extensión del archivo.

        Args:
            file_path: Ruta del archivo.

        Returns:
            Tipo MIME detectado.
        """
        import mimetypes
        
        # Asegurar que mimetypes está inicializado
        mimetypes.init()
        
        # Detectar tipo MIME
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Si no se pudo detectar, usar un valor predeterminado
        if not mime_type:
            # Verificar extensión
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.pdf']:
                mime_type = 'application/pdf'
            elif ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext in ['.png']:
                mime_type = 'image/png'
            elif ext in ['.tif', '.tiff']:
                mime_type = 'image/tiff'
            elif ext in ['.doc']:
                mime_type = 'application/msword'
            elif ext in ['.docx']:
                mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                mime_type = 'application/octet-stream'
        
        return mime_type

    def _detect_mime_type_from_content(self, content: bytes) -> str:
        """Detecta el tipo MIME basado en el contenido del archivo.

        Args:
            content: Contenido binario del archivo.

        Returns:
            Tipo MIME detectado.
        """
        # Verificar firmas de archivo comunes
        if content.startswith(b'%PDF'):
            return 'application/pdf'
        elif content.startswith(b'\xFF\xD8\xFF'):
            return 'image/jpeg'
        elif content.startswith(b'\x89PNG\r\n\x1A\n'):
            return 'image/png'
        elif content.startswith(b'II*\x00') or content.startswith(b'MM\x00*'):
            return 'image/tiff'
        elif content.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
            # Archivo de Office, pero no podemos determinar exactamente cuál
            return 'application/msword'
        else:
            # Tipo genérico
            return 'application/octet-stream'

    def _update_latency_stats(self, elapsed_ms: float) -> None:
        """Actualiza las estadísticas de latencia.

        Args:
            elapsed_ms: Tiempo transcurrido en milisegundos.
        """
        self.stats["total_latency_ms"] += elapsed_ms
        total_ops = (
            self.stats["process_operations"] +
            self.stats["extract_operations"] +
            self.stats["classify_operations"]
        )
        if total_ops > 0:
            self.stats["avg_latency_ms"] = (
                self.stats["total_latency_ms"] / total_ops
            )
