"""
Cliente para clasificación de documentos con Vertex AI Document AI.

Este módulo proporciona un cliente especializado para clasificar documentos
utilizando procesadores específicos de Document AI.
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple, Union

from google.api_core.exceptions import GoogleAPIError

from clients.base_client import BaseClient
from core.circuit_breaker import CircuitBreaker
from clients.vertex_ai.document.document_client import DocumentClient

class ClassifierClient(BaseClient):
    """Cliente para clasificación de documentos."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa el cliente de clasificación de documentos.

        Args:
            config: Configuración opcional para el cliente.
                Puede incluir:
                - project_id: ID del proyecto de Google Cloud
                - location: Ubicación de los procesadores (ej. 'us', 'eu')
                - classifier_processor_id: ID del procesador de clasificación predeterminado
                - timeout: Tiempo máximo de espera para operaciones (segundos)
                - mock_mode: Modo simulado para pruebas sin API real
                - circuit_breaker_config: Configuración del circuit breaker
                - document_client: Cliente de Document AI existente
        """
        super().__init__(name="ClassifierClient")
        self.config = config or {}
        
        # Configuración básica
        self.project_id = self.config.get("project_id") or os.environ.get(
            "GOOGLE_CLOUD_PROJECT"
        )
        self.location = self.config.get("location") or os.environ.get(
            "DOCUMENT_AI_LOCATION", "us"
        )
        self.classifier_processor_id = self.config.get("classifier_processor_id") or os.environ.get(
            "DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID"
        )
        self.timeout = self.config.get("timeout") or int(os.environ.get(
            "DOCUMENT_AI_TIMEOUT", "60"
        ))
        
        # Modo simulado para pruebas
        self.mock_mode = self.config.get("mock_mode", False)
        if not self.project_id or not self.classifier_processor_id:
            self.logger.warning(
                "No se encontró project_id o classifier_processor_id. Activando modo simulado."
            )
            self.mock_mode = True
        
        # Inicializar cliente de Document AI
        if "document_client" in self.config and self.config["document_client"]:
            self.document_client = self.config["document_client"]
            self.logger.info("Usando cliente Document AI proporcionado.")
        else:
            self.document_client = DocumentClient(
                {
                    "project_id": self.project_id,
                    "location": self.location,
                    "processor_id": self.classifier_processor_id,
                    "timeout": self.timeout,
                    "mock_mode": self.mock_mode,
                    "circuit_breaker_config": self.config.get("circuit_breaker_config", {})
                }
            )
            self.logger.info("Cliente Document AI inicializado para clasificación de documentos.")
        
        # Inicializar circuit breaker
        cb_config = self.config.get("circuit_breaker_config", {})
        self.circuit_breaker = CircuitBreaker(
            name="document_classifier",
            failure_threshold=cb_config.get("failure_threshold", 5),
            recovery_timeout=cb_config.get("recovery_timeout", 30),
            expected_exception=GoogleAPIError,
        )
        
        # Estadísticas
        self.stats = {
            "classify_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "total_latency_ms": 0,
            "mock_mode": self.mock_mode,
            "document_types": {},
        }
        
        # Mapeo de tipos de documentos a procesadores específicos
        self.document_type_processors = {
            "invoice": os.environ.get("DOCUMENT_AI_INVOICE_PROCESSOR_ID", ""),
            "receipt": os.environ.get("DOCUMENT_AI_RECEIPT_PROCESSOR_ID", ""),
            "id_document": os.environ.get("DOCUMENT_AI_ID_PROCESSOR_ID", ""),
            "form": os.environ.get("DOCUMENT_AI_FORM_PROCESSOR_ID", ""),
            "medical": os.environ.get("DOCUMENT_AI_MEDICAL_PROCESSOR_ID", ""),
            "tax": os.environ.get("DOCUMENT_AI_TAX_PROCESSOR_ID", ""),
        }

    async def classify_document(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf",
        processor_id: Optional[str] = None,
        confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Clasifica un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.
            processor_id: ID del procesador a utilizar.
            confidence_threshold: Umbral de confianza para incluir clasificaciones.

        Returns:
            Diccionario con las clasificaciones del documento.
        """
        start_time = time.time()
        processor_id = processor_id or self.classifier_processor_id
        
        try:
            # Verificar si el circuit breaker está abierto
            if self.circuit_breaker.is_open():
                self.logger.warning("Circuit breaker abierto. Usando respuesta simulada.")
                result = await self._mock_classify_document(document_data, mime_type)
                self.stats["errors"] += 1
                return result
            
            # Modo simulado
            if self.mock_mode:
                self.logger.info("Clasificando documento en modo simulado.")
                result = await self._mock_classify_document(document_data, mime_type)
                self._update_stats(start_time, result)
                return result
            
            # Procesar documento con Document AI
            with self.circuit_breaker:
                # Procesar documento
                self.logger.info(f"Clasificando documento con procesador {processor_id}")
                result = await self.document_client.process_document(
                    document_data, processor_id, mime_type
                )
                
                # Si hay error, devolver el resultado
                if "error" in result:
                    self.stats["errors"] += 1
                    return {
                        "error": result["error"],
                        "success": False,
                        "document_type": "unknown",
                        "classifications": [],
                        "confidence": 0.0,
                        "mime_type": mime_type
                    }
                
                # Extraer clasificaciones
                classifications = []
                for entity in result.get("entities", []):
                    if entity.get("type") == "classification" and entity.get("confidence", 0) >= confidence_threshold:
                        classifications.append({
                            "name": entity.get("mention_text", ""),
                            "confidence": entity.get("confidence", 0.0)
                        })
                
                # Ordenar clasificaciones por confianza
                classifications = sorted(
                    classifications,
                    key=lambda x: x.get("confidence", 0.0),
                    reverse=True
                )
                
                # Determinar el tipo de documento principal
                document_type = classifications[0]["name"] if classifications else "unknown"
                confidence = classifications[0]["confidence"] if classifications else 0.0
                
                # Actualizar estadísticas
                self._update_stats(start_time, {"document_type": document_type})
                
                # Construir resultado
                return {
                    "document_type": document_type,
                    "confidence": confidence,
                    "classifications": classifications,
                    "success": True,
                    "text": result.get("text", ""),
                    "mime_type": mime_type
                }
                
        except Exception as e:
            self.logger.error(f"Error al clasificar documento: {e}")
            self.stats["errors"] += 1
            
            # Respuesta de error
            return {
                "error": str(e),
                "success": False,
                "document_type": "unknown",
                "classifications": [],
                "confidence": 0.0,
                "mime_type": mime_type
            }
        finally:
            # Actualizar latencia incluso en caso de error
            elapsed_ms = (time.time() - start_time) * 1000
            self._update_latency_stats(elapsed_ms)

    async def batch_classify_documents(
        self,
        documents: List[Tuple[bytes, str]],
        processor_id: Optional[str] = None,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Clasifica múltiples documentos en batch.

        Args:
            documents: Lista de tuplas (document_data, mime_type).
            processor_id: ID del procesador a utilizar.
            confidence_threshold: Umbral de confianza para incluir clasificaciones.

        Returns:
            Lista de resultados de clasificación para cada documento.
        """
        processor_id = processor_id or self.classifier_processor_id
        
        # Clasificar documentos en paralelo
        tasks = []
        for doc_data, mime_type in documents:
            task = asyncio.create_task(
                self.classify_document(doc_data, mime_type, processor_id, confidence_threshold)
            )
            tasks.append(task)
        
        # Esperar a que todos los documentos se clasifiquen
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Manejar excepciones
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Error al clasificar documento {i}: {result}")
                processed_results.append({
                    "error": str(result),
                    "success": False,
                    "document_type": "unknown",
                    "classifications": [],
                    "confidence": 0.0,
                    "mime_type": documents[i][1]
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def get_document_processor(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Determina el procesador adecuado para un documento basado en su tipo.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con información del procesador recomendado.
        """
        # Clasificar el documento
        result = await self.classify_document(document_data, mime_type)
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return {
                "error": result["error"],
                "success": False,
                "processor_id": None,
                "document_type": "unknown"
            }
        
        # Obtener el tipo de documento
        document_type = result["document_type"].lower()
        
        # Buscar un procesador específico para el tipo de documento
        processor_id = None
        for doc_type, proc_id in self.document_type_processors.items():
            if doc_type in document_type and proc_id:
                processor_id = proc_id
                break
        
        # Si no se encuentra un procesador específico, usar el procesador general
        if not processor_id:
            processor_id = self.classifier_processor_id
        
        # Construir resultado
        return {
            "processor_id": processor_id,
            "document_type": document_type,
            "confidence": result["confidence"],
            "success": True,
            "classifications": result["classifications"]
        }

    async def classify_and_process(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Clasifica un documento y lo procesa con el procesador adecuado.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con los resultados del procesamiento.
        """
        # Determinar el procesador adecuado
        processor_result = await self.get_document_processor(document_data, mime_type)
        
        # Si hay error, devolver el resultado
        if "error" in processor_result:
            return processor_result
        
        # Obtener el procesador y el tipo de documento
        processor_id = processor_result["processor_id"]
        document_type = processor_result["document_type"]
        
        # Procesar el documento con el procesador adecuado
        result = await self.document_client.process_document(
            document_data, processor_id, mime_type
        )
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return result
        
        # Añadir información de clasificación al resultado
        result["document_type"] = document_type
        result["classification_confidence"] = processor_result["confidence"]
        result["classifications"] = processor_result["classifications"]
        
        return result

    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cliente.

        Returns:
            Diccionario con estadísticas de uso.
        """
        # Obtener estadísticas del cliente de Document AI
        document_client_stats = await self.document_client.get_stats()
        
        # Combinar estadísticas
        combined_stats = {
            **self.stats,
            "document_client_stats": document_client_stats
        }
        
        return combined_stats

    def _update_stats(self, start_time: float, result: Dict[str, Any] = None) -> None:
        """Actualiza las estadísticas después de una operación.

        Args:
            start_time: Tiempo de inicio de la operación.
            result: Resultado de la operación.
        """
        self.stats["classify_operations"] += 1
        elapsed_ms = (time.time() - start_time) * 1000
        self._update_latency_stats(elapsed_ms)
        
        # Actualizar estadísticas de tipos de documentos
        if result and "document_type" in result:
            document_type = result["document_type"]
            if document_type not in self.stats["document_types"]:
                self.stats["document_types"][document_type] = 0
            self.stats["document_types"][document_type] += 1

    def _update_latency_stats(self, elapsed_ms: float) -> None:
        """Actualiza las estadísticas de latencia.

        Args:
            elapsed_ms: Tiempo transcurrido en milisegundos.
        """
        self.stats["total_latency_ms"] += elapsed_ms
        if self.stats["classify_operations"] > 0:
            self.stats["avg_latency_ms"] = (
                self.stats["total_latency_ms"] / self.stats["classify_operations"]
            )

    async def _mock_classify_document(
        self,
        document_data: bytes,
        mime_type: str
    ) -> Dict[str, Any]:
        """Genera una respuesta simulada para clasificación de documentos.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Respuesta simulada.
        """
        # Determinar tipo de documento basado en el tipo MIME
        if "pdf" in mime_type:
            # Simular diferentes tipos de documentos para PDFs
            document_types = [
                {"name": "invoice", "confidence": 0.85},
                {"name": "form", "confidence": 0.10},
                {"name": "receipt", "confidence": 0.05}
            ]
        elif "image" in mime_type:
            # Simular diferentes tipos de documentos para imágenes
            document_types = [
                {"name": "id_document", "confidence": 0.90},
                {"name": "receipt", "confidence": 0.08},
                {"name": "form", "confidence": 0.02}
            ]
        else:
            # Tipo genérico para otros formatos
            document_types = [
                {"name": "document", "confidence": 0.95},
                {"name": "form", "confidence": 0.05}
            ]
        
        # Simular un pequeño retraso para ser realista
        await asyncio.sleep(0.2)
        
        # Construir resultado
        return {
            "document_type": document_types[0]["name"],
            "confidence": document_types[0]["confidence"],
            "classifications": document_types,
            "success": True,
            "text": "Este es un documento simulado para pruebas de clasificación.",
            "mime_type": mime_type,
            "mock": True
        }
