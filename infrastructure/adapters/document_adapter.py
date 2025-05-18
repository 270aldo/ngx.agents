"""
Adaptador para procesamiento de documentos.

Este módulo proporciona un adaptador que simplifica el acceso a las capacidades
de procesamiento de documentos para otros componentes del sistema.
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Tuple, Union, BinaryIO
from datetime import datetime

from core.document_processor import DocumentProcessor
from core.logging_config import get_logger
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter

# Configurar logger
logger = get_logger(__name__)

# Singleton para el adaptador de documentos
document_adapter = None

class DocumentAdapter(BaseAgentAdapter):
    """Adaptador para capacidades de procesamiento de documentos."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa el adaptador de documentos.

        Args:
            config: Configuración opcional para el adaptador.
                Puede incluir:
                - project_id: ID del proyecto de Google Cloud
                - location: Ubicación de los procesadores (ej. 'us', 'eu')
                - timeout: Tiempo máximo de espera para operaciones (segundos)
                - mock_mode: Modo simulado para pruebas sin API real
                - circuit_breaker_config: Configuración del circuit breaker
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        self._initialized = False
        self._initializing = False
        self.document_processor = None
        
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

    async def initialize(self) -> None:
        """Inicializa el adaptador de documentos.

        Esta función debe ser llamada antes de usar cualquier otra función del adaptador.
        """
        if self._initialized or self._initializing:
            return
        
        self._initializing = True
        
        try:
            self.logger.info("Inicializando adaptador de documentos...")
            
            # Inicializar procesador de documentos
            self.document_processor = DocumentProcessor({
                "project_id": self.project_id,
                "location": self.location,
                "timeout": self.timeout,
                "mock_mode": self.mock_mode,
                "circuit_breaker_config": self.config.get("circuit_breaker_config", {})
            })
            
            self._initialized = True
            self.logger.info("Adaptador de documentos inicializado correctamente.")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar adaptador de documentos: {e}")
            self._initialized = False
            raise
        finally:
            self._initializing = False

    async def _ensure_initialized(self) -> None:
        """Asegura que el adaptador esté inicializado antes de usarlo."""
        if not self._initialized:
            await self.initialize()

    async def process_document(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Procesa un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para el procesamiento.
                Puede incluir:
                - mime_type: Tipo MIME del documento.
                - processor_id: ID del procesador a utilizar.
                - document_type: Tipo de documento para seleccionar el procesador adecuado.
                - auto_classify: Si es True, clasifica automáticamente el documento.

        Returns:
            Diccionario con los resultados del procesamiento.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            processor_id = context.get("processor_id")
            document_type = context.get("document_type")
            auto_classify = context.get("auto_classify", True)
            
            # Procesar documento
            return await self.document_processor.process_document(
                document_data, mime_type, processor_id, document_type, auto_classify
            )
            
        except Exception as e:
            self.logger.error(f"Error al procesar documento: {e}")
            return {
                "error": str(e),
                "success": False,
                "text": "",
                "pages": [],
                "entities": []
            }

    async def extract_text(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae texto de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.
                - processor_id: ID del procesador a utilizar.

        Returns:
            Diccionario con el texto extraído y metadatos.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            processor_id = context.get("processor_id")
            
            # Extraer texto
            return await self.document_processor.extract_text(
                document_data, mime_type, processor_id
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer texto: {e}")
            return {
                "error": str(e),
                "success": False,
                "text": ""
            }

    async def classify_document(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Clasifica un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la clasificación.
                Puede incluir:
                - mime_type: Tipo MIME del documento.
                - processor_id: ID del procesador a utilizar.
                - confidence_threshold: Umbral de confianza para incluir clasificaciones.

        Returns:
            Diccionario con las clasificaciones del documento.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            processor_id = context.get("processor_id")
            confidence_threshold = context.get("confidence_threshold", 0.5)
            
            # Clasificar documento
            return await self.document_processor.classify_document(
                document_data, mime_type, processor_id, confidence_threshold
            )
            
        except Exception as e:
            self.logger.error(f"Error al clasificar documento: {e}")
            return {
                "error": str(e),
                "success": False,
                "document_type": "unknown",
                "classifications": [],
                "confidence": 0.0
            }

    async def extract_entities(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae entidades de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.
                - processor_id: ID del procesador a utilizar.
                - document_type: Tipo de documento para seleccionar el procesador adecuado.
                - entity_types: Lista de tipos de entidades a extraer.

        Returns:
            Diccionario con las entidades extraídas.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            processor_id = context.get("processor_id")
            document_type = context.get("document_type")
            entity_types = context.get("entity_types")
            
            # Extraer entidades
            return await self.document_processor.extract_entities(
                document_data, mime_type, processor_id, document_type, entity_types
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer entidades: {e}")
            return {
                "error": str(e),
                "success": False,
                "entities": [],
                "entities_by_type": {}
            }

    async def process_form(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Procesa un formulario para extraer campos clave-valor.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para el procesamiento.
                Puede incluir:
                - mime_type: Tipo MIME del documento.
                - processor_id: ID del procesador a utilizar.

        Returns:
            Diccionario con los campos del formulario extraídos.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            processor_id = context.get("processor_id")
            
            # Procesar formulario
            return await self.document_processor.process_form(
                document_data, mime_type, processor_id
            )
            
        except Exception as e:
            self.logger.error(f"Error al procesar formulario: {e}")
            return {
                "error": str(e),
                "success": False,
                "form_fields": {},
                "entities": []
            }

    async def extract_personal_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae información personal de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información personal extraída.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            
            # Extraer información personal
            return await self.document_processor.extract_personal_information(
                document_data, mime_type
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer información personal: {e}")
            return {
                "error": str(e),
                "success": False,
                "personal_info": {},
                "entities": []
            }

    async def extract_business_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae información de negocios de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información de negocios extraída.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            
            # Extraer información de negocios
            return await self.document_processor.extract_business_information(
                document_data, mime_type
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer información de negocios: {e}")
            return {
                "error": str(e),
                "success": False,
                "business_info": {},
                "entities": []
            }

    async def extract_medical_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae información médica de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información médica extraída.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            
            # Extraer información médica
            return await self.document_processor.extract_medical_information(
                document_data, mime_type
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer información médica: {e}")
            return {
                "error": str(e),
                "success": False,
                "medical_info": {},
                "entities": []
            }

    async def extract_invoice_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae información de facturas.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información de la factura extraída.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            
            # Extraer información de factura
            return await self.document_processor.extract_invoice_information(
                document_data, mime_type
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer información de factura: {e}")
            return {
                "error": str(e),
                "success": False,
                "invoice_info": {
                    "supplier": {},
                    "customer": {},
                    "invoice_details": {},
                    "line_items": [],
                    "payment_info": {},
                    "totals": {}
                },
                "entities": []
            }

    async def extract_id_document_information(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extrae información de documentos de identidad.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para la extracción.
                Puede incluir:
                - mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información del documento de identidad extraída.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            
            # Extraer información de documento de identidad
            return await self.document_processor.extract_id_document_information(
                document_data, mime_type
            )
            
        except Exception as e:
            self.logger.error(f"Error al extraer información de documento de identidad: {e}")
            return {
                "error": str(e),
                "success": False,
                "id_document_info": {
                    "personal_details": {},
                    "document_details": {}
                },
                "entities": []
            }

    async def analyze_document(
        self,
        document_data: Union[bytes, BinaryIO, str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Realiza un análisis completo de un documento.

        Args:
            document_data: Datos del documento (bytes, archivo o ruta).
            context: Contexto adicional para el análisis.
                Puede incluir:
                - mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con los resultados del análisis completo.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto
            mime_type = context.get("mime_type")
            
            # Analizar documento
            return await self.document_processor.analyze_document(
                document_data, mime_type
            )
            
        except Exception as e:
            self.logger.error(f"Error al analizar documento: {e}")
            return {
                "error": str(e),
                "success": False,
                "document_type": "unknown",
                "confidence": 0.0,
                "classifications": [],
                "entities": [],
                "entities_by_type": {},
                "text": ""
            }

    async def batch_process_documents(
        self,
        documents: List[Tuple[Union[bytes, BinaryIO, str], Optional[Dict[str, Any]]]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Procesa múltiples documentos en batch.

        Args:
            documents: Lista de tuplas (document_data, document_context).
            context: Contexto global para el procesamiento.
                Puede incluir:
                - processor_id: ID del procesador a utilizar.
                - auto_classify: Si es True, clasifica automáticamente cada documento.

        Returns:
            Lista de resultados de procesamiento para cada documento.
        """
        await self._ensure_initialized()
        
        try:
            context = context or {}
            
            # Extraer parámetros del contexto global
            processor_id = context.get("processor_id")
            auto_classify = context.get("auto_classify", True)
            
            # Preparar documentos para procesamiento
            prepared_documents = []
            for doc_data, doc_context in documents:
                doc_context = doc_context or {}
                mime_type = doc_context.get("mime_type")
                prepared_documents.append((doc_data, mime_type))
            
            # Procesar documentos en batch
            return await self.document_processor.batch_process_documents(
                prepared_documents, processor_id, auto_classify
            )
            
        except Exception as e:
            self.logger.error(f"Error al procesar documentos en batch: {e}")
            return [
                {
                    "error": str(e),
                    "success": False,
                    "text": "",
                    "pages": [],
                    "entities": []
                }
                for _ in documents
            ]

    async def get_available_processors(self) -> Dict[str, Any]:
        """Obtiene los procesadores disponibles en el proyecto.

        Returns:
            Diccionario con información sobre los procesadores disponibles.
        """
        await self._ensure_initialized()
        
        try:
            return await self.document_processor.get_available_processors()
        except Exception as e:
            self.logger.error(f"Error al obtener procesadores disponibles: {e}")
            return {
                "error": str(e),
                "success": False,
                "processors": [],
                "count": 0
            }

    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del adaptador de documentos.

        Returns:
            Diccionario con estadísticas de uso.
        """
        await self._ensure_initialized()
        
        try:
            return await self.document_processor.get_stats()
        except Exception as e:
            self.logger.error(f"Error al obtener estadísticas: {e}")
            return {
                "error": str(e),
                "success": False,
                "process_operations": 0,
                "extract_operations": 0,
                "classify_operations": 0,
                "errors": 0,
                "avg_latency_ms": 0,
                "mock_mode": self.mock_mode
            }


    async def _process_query(self, query: str, user_id: str = None, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario relacionada con documentos.
        
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
            
            # Verificar si hay un documento en los kwargs
            document_data = kwargs.get('document_data')
            context = kwargs.get('context', {})
            
            if not document_data:
                return {
                    "success": False,
                    "error": "No se proporcionaron datos de documento para procesar",
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Determinar la operación a realizar según el tipo de consulta
            result = None
            if query_type == "text_extraction":
                result = await self.extract_text(document_data, context)
            elif query_type == "document_classification":
                result = await self.classify_document(document_data, context)
            elif query_type == "entity_extraction":
                result = await self.extract_entities(document_data, context)
            elif query_type == "form_processing":
                result = await self.process_form(document_data, context)
            elif query_type == "personal_info_extraction":
                result = await self.extract_personal_information(document_data, context)
            elif query_type == "business_info_extraction":
                result = await self.extract_business_information(document_data, context)
            elif query_type == "medical_info_extraction":
                result = await self.extract_medical_information(document_data, context)
            else:
                # Procesamiento general por defecto
                result = await self.process_document(document_data, context)
            
            return {
                "success": True,
                "output": "Procesamiento de documento completado",
                "query_type": query_type,
                "result": result,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error al procesar consulta de documento: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para DocumentAdapter.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "extraer texto": "text_extraction",
            "clasificar": "document_classification",
            "entidades": "entity_extraction",
            "formulario": "form_processing",
            "información personal": "personal_info_extraction",
            "información de negocio": "business_info_extraction",
            "información médica": "medical_info_extraction",
            "procesar": "general_processing",
            "analizar": "general_processing"
        }

# Inicializar el singleton
document_adapter = DocumentAdapter()
