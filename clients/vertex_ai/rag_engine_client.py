"""
Cliente para Vertex AI RAG Engine.

Este módulo proporciona un cliente para interactuar con Vertex AI RAG Engine,
permitiendo la creación y gestión de aplicaciones RAG, así como la generación
de respuestas basadas en documentos.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any

from google.cloud import aiplatform
from google.cloud import storage
from google.oauth2 import service_account

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class RAGEngineClient:
    """Cliente para Vertex AI RAG Engine."""
    
    def __init__(self, config=None):
        """Inicializa el cliente de Vertex AI RAG Engine."""
        self.config = config or self._load_default_config()
        self.credentials = self._initialize_credentials()
        self.client = self._initialize_client()
        self.storage_client = self._initialize_storage_client()
        
        # Estadísticas
        self.stats = {
            "corpus_operations": 0,
            "query_operations": 0,
            "errors": 0,
            "latency_ms": []
        }
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Carga la configuración por defecto."""
        import os
        
        # Función auxiliar para leer variables de entorno enteras
        def get_env_int(var_name: str, default_value: int) -> int:
            val_str = os.environ.get(var_name)
            if val_str is None:
                return default_value
            try:
                return int(val_str)
            except ValueError:
                logger.warning(f"Valor inválido para la variable de entorno {var_name}: '{val_str}'. Usando el valor por defecto: {default_value}")
                return default_value
        
        return {
            "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
            "credentials_path": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "rag_bucket": os.environ.get("VERTEX_RAG_BUCKET"),
            "rag_corpus_directory": os.environ.get("VERTEX_RAG_CORPUS_DIRECTORY", "corpus"),
            "rag_application_id": os.environ.get("VERTEX_RAG_APPLICATION_ID", "ngx-rag-application"),
            "chunk_size": get_env_int("VERTEX_RAG_CHUNK_SIZE", 1024),
            "chunk_overlap": get_env_int("VERTEX_RAG_CHUNK_OVERLAP", 256),
            "embedding_model": os.environ.get("VERTEX_EMBEDDING_MODEL", "text-embedding-large-exp-03-07"),
            "orchestrator_model": os.environ.get("VERTEX_ORCHESTRATOR_MODEL", "gemini-2.5-pro"),
            "agent_model": os.environ.get("VERTEX_AGENT_MODEL", "gemini-2.5-flash")
        }
        
    def _initialize_credentials(self) -> Optional[service_account.Credentials]:
        """Inicializa las credenciales de Google Cloud."""
        try:
            if self.config.get("credentials_path"):
                return service_account.Credentials.from_service_account_file(
                    self.config["credentials_path"]
                )
            return None  # Usar credenciales por defecto
        except Exception as e:
            logger.error(f"Error al inicializar credenciales: {e}")
            return None
        
    def _initialize_client(self) -> Any:
        """Inicializa el cliente de Vertex AI."""
        try:
            # Intentar importar bibliotecas de Vertex AI
            try:
                from google.cloud import aiplatform
                VERTEX_AI_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudieron importar las bibliotecas de Vertex AI. Usando modo mock.")
                VERTEX_AI_AVAILABLE = False
                
            if not VERTEX_AI_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            if self.credentials:
                aiplatform.init(
                    project=self.config.get("project_id"),
                    location=self.config.get("location"),
                    credentials=self.credentials
                )
            else:
                aiplatform.init(
                    project=self.config.get("project_id"),
                    location=self.config.get("location")
                )
                
            return {
                "aiplatform": aiplatform,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Vertex AI: {e}")
            return {"mock": True}
    
    def _initialize_storage_client(self) -> Any:
        """Inicializa el cliente de Cloud Storage."""
        try:
            # Intentar importar bibliotecas de Cloud Storage
            try:
                from google.cloud import storage
                STORAGE_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudieron importar las bibliotecas de Cloud Storage. Usando modo mock.")
                STORAGE_AVAILABLE = False
                
            if not STORAGE_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            if self.credentials:
                storage_client = storage.Client(
                    project=self.config.get("project_id"),
                    credentials=self.credentials
                )
            else:
                storage_client = storage.Client(
                    project=self.config.get("project_id")
                )
                
            return {
                "storage_client": storage_client,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Cloud Storage: {e}")
            return {"mock": True}
    
    async def upload_document(self, file_path: str, destination_blob_name: Optional[str] = None) -> str:
        """
        Sube un documento al bucket de Cloud Storage para RAG Engine.
        
        Args:
            file_path: Ruta local del archivo a subir
            destination_blob_name: Nombre del blob en Cloud Storage (opcional)
            
        Returns:
            str: URI del documento en Cloud Storage
        """
        span = telemetry_adapter.start_span("RAGEngineClient.upload_document", {
            "file_path": file_path
        })
        
        try:
            # Verificar si estamos en modo mock
            if self.storage_client.get("mock", False):
                await asyncio.sleep(0.5)  # Simular latencia
                blob_name = destination_blob_name or f"mock_document_{int(time.time())}.pdf"
                uri = f"gs://{self.config.get('rag_bucket')}/{self.config.get('rag_corpus_directory')}/{blob_name}"
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                telemetry_adapter.set_span_attribute(span, "document.uri", uri)
                return uri
            
            # Obtener nombre del blob si no se proporciona
            if not destination_blob_name:
                import os
                destination_blob_name = f"{self.config.get('rag_corpus_directory')}/{os.path.basename(file_path)}"
            else:
                destination_blob_name = f"{self.config.get('rag_corpus_directory')}/{destination_blob_name}"
            
            # Subir archivo
            bucket = self.storage_client["storage_client"].bucket(self.config.get("rag_bucket"))
            blob = bucket.blob(destination_blob_name)
            
            # Convertir a operación asíncrona
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: blob.upload_from_filename(file_path)
            )
            
            # Construir URI
            uri = f"gs://{self.config.get('rag_bucket')}/{destination_blob_name}"
            
            telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            telemetry_adapter.set_span_attribute(span, "document.uri", uri)
            return uri
            
        except Exception as e:
            logger.error(f"Error al subir documento: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def create_corpus(self, corpus_name: str, document_uris: List[str]) -> str:
        """
        Crea un corpus para RAG Engine.
        
        Args:
            corpus_name: Nombre del corpus
            document_uris: Lista de URIs de documentos en Cloud Storage
            
        Returns:
            str: ID del corpus creado
        """
        span = telemetry_adapter.start_span("RAGEngineClient.create_corpus", {
            "corpus_name": corpus_name,
            "documents_count": len(document_uris)
        })
        
        try:
            # Actualizar estadísticas
            self.stats["corpus_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(1.0)  # Simular latencia
                corpus_id = f"mock_corpus_{int(time.time())}"
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                telemetry_adapter.set_span_attribute(span, "corpus.id", corpus_id)
                return corpus_id
            
            # Crear corpus
            aiplatform = self.client["aiplatform"]
            
            # Convertir a operación asíncrona
            loop = asyncio.get_event_loop()
            
            # Crear el corpus
            corpus_resource = await loop.run_in_executor(
                None,
                lambda: aiplatform.VertexRagDataService.create_corpus(
                    display_name=corpus_name,
                    description=f"Corpus para {corpus_name}",
                    location=self.config.get("location"),
                    project=self.config.get("project_id")
                )
            )
            
            # Obtener ID del corpus
            corpus_id = corpus_resource.name.split("/")[-1]
            
            # Añadir documentos al corpus
            for uri in document_uris:
                await loop.run_in_executor(
                    None,
                    lambda: aiplatform.VertexRagDataService.import_rag_files(
                        corpus=corpus_resource.name,
                        rag_files=[
                            {
                                "gcs_uri": uri,
                                "display_name": uri.split("/")[-1]
                            }
                        ]
                    )
                )
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            telemetry_adapter.set_span_attribute(span, "corpus.id", corpus_id)
            telemetry_adapter.record_metric("rag_engine_client.latency", latency_ms, {"operation": "create_corpus"})
            
            return corpus_id
            
        except Exception as e:
            logger.error(f"Error al crear corpus: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def create_rag_application(self, corpus_id: str, application_name: Optional[str] = None) -> str:
        """
        Crea una aplicación RAG.
        
        Args:
            corpus_id: ID del corpus a utilizar
            application_name: Nombre de la aplicación (opcional)
            
        Returns:
            str: ID de la aplicación RAG creada
        """
        span = telemetry_adapter.start_span("RAGEngineClient.create_rag_application", {
            "corpus_id": corpus_id
        })
        
        try:
            # Actualizar estadísticas
            self.stats["corpus_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(1.0)  # Simular latencia
                app_id = f"mock_app_{int(time.time())}"
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                telemetry_adapter.set_span_attribute(span, "application.id", app_id)
                return app_id
            
            # Crear aplicación RAG
            aiplatform = self.client["aiplatform"]
            
            # Usar nombre de aplicación proporcionado o el configurado
            app_name = application_name or self.config.get("rag_application_id")
            
            # Convertir a operación asíncrona
            loop = asyncio.get_event_loop()
            
            # Crear la aplicación RAG
            app_resource = await loop.run_in_executor(
                None,
                lambda: aiplatform.VertexRagService.create_rag_application(
                    display_name=app_name,
                    description=f"Aplicación RAG para {app_name}",
                    corpus=f"projects/{self.config.get('project_id')}/locations/{self.config.get('location')}/corpora/{corpus_id}",
                    retrieval_model=self.config.get("embedding_model"),
                    generation_model=self.config.get("orchestrator_model"),
                    location=self.config.get("location"),
                    project=self.config.get("project_id"),
                    chunk_size=self.config.get("chunk_size"),
                    chunk_overlap=self.config.get("chunk_overlap")
                )
            )
            
            # Obtener ID de la aplicación
            app_id = app_resource.name.split("/")[-1]
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            telemetry_adapter.set_span_attribute(span, "application.id", app_id)
            telemetry_adapter.record_metric("rag_engine_client.latency", latency_ms, {"operation": "create_rag_application"})
            
            return app_id
            
        except Exception as e:
            logger.error(f"Error al crear aplicación RAG: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def query_rag(self, query: str, application_id: Optional[str] = None, 
                      top_k: int = 5, temperature: float = 0.2, 
                      max_output_tokens: int = 1024) -> Dict[str, Any]:
        """
        Consulta una aplicación RAG.
        
        Args:
            query: Consulta a realizar
            application_id: ID de la aplicación RAG (opcional)
            top_k: Número de fragmentos a recuperar
            temperature: Temperatura para la generación
            max_output_tokens: Número máximo de tokens de salida
            
        Returns:
            Dict: Resultado de la consulta
        """
        span = telemetry_adapter.start_span("RAGEngineClient.query_rag", {
            "query_length": len(query),
            "top_k": top_k,
            "temperature": temperature
        })
        
        try:
            # Actualizar estadísticas
            self.stats["query_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.5)  # Simular latencia
                
                # Generar respuesta mock
                response = {
                    "answer": f"Respuesta simulada para: {query}",
                    "citations": [
                        {"text": "Fragmento de ejemplo 1", "uri": "gs://bucket/doc1.pdf", "page": 1},
                        {"text": "Fragmento de ejemplo 2", "uri": "gs://bucket/doc2.pdf", "page": 3}
                    ],
                    "latency_ms": 500
                }
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                return response
            
            # Usar ID de aplicación proporcionado o el configurado
            app_id = application_id or self.config.get("rag_application_id")
            
            # Consultar aplicación RAG
            aiplatform = self.client["aiplatform"]
            
            # Convertir a operación asíncrona
            loop = asyncio.get_event_loop()
            
            # Realizar la consulta
            response = await loop.run_in_executor(
                None,
                lambda: aiplatform.VertexRagService.query_rag_application(
                    rag_application=f"projects/{self.config.get('project_id')}/locations/{self.config.get('location')}/ragApplications/{app_id}",
                    query=query,
                    top_k=top_k,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )
            )
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Procesar respuesta
            result = {
                "answer": response.answer,
                "citations": [],
                "latency_ms": latency_ms
            }
            
            # Procesar citas
            for citation in response.citations:
                result["citations"].append({
                    "text": citation.chunk_content,
                    "uri": citation.uri,
                    "page": citation.page_number
                })
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            telemetry_adapter.set_span_attribute(span, "citations_count", len(result["citations"]))
            telemetry_adapter.record_metric("rag_engine_client.latency", latency_ms, {"operation": "query_rag"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al consultar aplicación RAG: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {
                "answer": "",
                "citations": [],
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.
        
        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Calcular promedio de latencia
        avg_latency = sum(self.stats["latency_ms"]) / len(self.stats["latency_ms"]) if self.stats["latency_ms"] else 0
        
        return {
            "corpus_operations": self.stats["corpus_operations"],
            "query_operations": self.stats["query_operations"],
            "errors": self.stats["errors"],
            "avg_latency_ms": avg_latency,
            "embedding_model": self.config.get("embedding_model"),
            "orchestrator_model": self.config.get("orchestrator_model"),
            "agent_model": self.config.get("agent_model"),
            "chunk_size": self.config.get("chunk_size"),
            "chunk_overlap": self.config.get("chunk_overlap"),
            "mock_mode": self.client.get("mock", False)
        }
