"""
Cliente para extracción de entidades con Vertex AI Document AI.

Este módulo proporciona un cliente especializado para extraer entidades
de documentos utilizando procesadores específicos de Document AI.
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Tuple, Union

from google.api_core.exceptions import GoogleAPIError

from clients.base_client import BaseClient
from core.circuit_breaker import CircuitBreaker
from clients.vertex_ai.document.document_client import DocumentClient

class EntityExtractorClient(BaseClient):
    """Cliente para extracción de entidades de documentos."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializa el cliente de extracción de entidades.

        Args:
            config: Configuración opcional para el cliente.
                Puede incluir:
                - project_id: ID del proyecto de Google Cloud
                - location: Ubicación de los procesadores (ej. 'us', 'eu')
                - entity_processor_id: ID del procesador de entidades predeterminado
                - timeout: Tiempo máximo de espera para operaciones (segundos)
                - mock_mode: Modo simulado para pruebas sin API real
                - circuit_breaker_config: Configuración del circuit breaker
                - document_client: Cliente de Document AI existente
        """
        super().__init__(name="EntityExtractorClient")
        self.config = config or {}
        
        # Configuración básica
        self.project_id = self.config.get("project_id") or os.environ.get(
            "GOOGLE_CLOUD_PROJECT"
        )
        self.location = self.config.get("location") or os.environ.get(
            "DOCUMENT_AI_LOCATION", "us"
        )
        self.entity_processor_id = self.config.get("entity_processor_id") or os.environ.get(
            "DOCUMENT_AI_ENTITY_PROCESSOR_ID"
        )
        self.timeout = self.config.get("timeout") or int(os.environ.get(
            "DOCUMENT_AI_TIMEOUT", "60"
        ))
        
        # Modo simulado para pruebas
        self.mock_mode = self.config.get("mock_mode", False)
        if not self.project_id or not self.entity_processor_id:
            self.logger.warning(
                "No se encontró project_id o entity_processor_id. Activando modo simulado."
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
                    "processor_id": self.entity_processor_id,
                    "timeout": self.timeout,
                    "mock_mode": self.mock_mode,
                    "circuit_breaker_config": self.config.get("circuit_breaker_config", {})
                }
            )
            self.logger.info("Cliente Document AI inicializado para extracción de entidades.")
        
        # Inicializar circuit breaker
        cb_config = self.config.get("circuit_breaker_config", {})
        self.circuit_breaker = CircuitBreaker(
            name="entity_extractor",
            failure_threshold=cb_config.get("failure_threshold", 5),
            recovery_timeout=cb_config.get("recovery_timeout", 30),
            expected_exception=GoogleAPIError,
        )
        
        # Estadísticas
        self.stats = {
            "extract_operations": 0,
            "errors": 0,
            "avg_latency_ms": 0,
            "total_latency_ms": 0,
            "mock_mode": self.mock_mode,
            "entity_types": {},
        }
        
        # Mapeo de tipos de documentos a procesadores
        self.document_type_processors = {
            "invoice": os.environ.get("DOCUMENT_AI_INVOICE_PROCESSOR_ID", ""),
            "receipt": os.environ.get("DOCUMENT_AI_RECEIPT_PROCESSOR_ID", ""),
            "id_document": os.environ.get("DOCUMENT_AI_ID_PROCESSOR_ID", ""),
            "form": os.environ.get("DOCUMENT_AI_FORM_PROCESSOR_ID", ""),
            "medical": os.environ.get("DOCUMENT_AI_MEDICAL_PROCESSOR_ID", ""),
            "tax": os.environ.get("DOCUMENT_AI_TAX_PROCESSOR_ID", ""),
        }

    async def extract_entities(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf",
        processor_id: Optional[str] = None,
        document_type: Optional[str] = None,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Extrae entidades de un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.
            processor_id: ID del procesador a utilizar.
            document_type: Tipo de documento para seleccionar el procesador adecuado.
            entity_types: Lista de tipos de entidades a extraer (si se especifica).

        Returns:
            Diccionario con las entidades extraídas.
        """
        # Seleccionar procesador basado en el tipo de documento
        if document_type and document_type in self.document_type_processors:
            processor_id = self.document_type_processors[document_type] or processor_id
        
        processor_id = processor_id or self.entity_processor_id
        
        # Procesar documento para extraer entidades
        result = await self.document_client.process_document(
            document_data, processor_id, mime_type
        )
        
        # Actualizar estadísticas
        self.stats["extract_operations"] += 1
        if "error" in result:
            self.stats["errors"] += 1
            return result
        
        # Filtrar por tipos de entidades si se especifica
        entities = result.get("entities", [])
        if entity_types:
            entities = [e for e in entities if e.get("type") in entity_types]
            result["entities"] = entities
        
        # Organizar entidades por tipo
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
            
            # Actualizar estadísticas de tipos de entidades
            if entity_type not in self.stats["entity_types"]:
                self.stats["entity_types"][entity_type] = 0
            self.stats["entity_types"][entity_type] += 1
        
        # Construir resultado
        return {
            "entities": entities,
            "entities_by_type": entities_by_type,
            "entity_count": len(entities),
            "document_type": document_type or "unknown",
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def extract_personal_information(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Extrae información personal de un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información personal extraída.
        """
        # Tipos de entidades personales comunes
        personal_entity_types = [
            "person_name", "email_address", "phone_number", "address",
            "date_of_birth", "gender", "nationality", "id_number"
        ]
        
        # Usar procesador de entidades personales o general
        processor_id = os.environ.get("DOCUMENT_AI_PERSONAL_PROCESSOR_ID", self.entity_processor_id)
        
        # Extraer entidades
        result = await self.extract_entities(
            document_data, mime_type, processor_id, None, personal_entity_types
        )
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return result
        
        # Organizar información personal
        personal_info = {}
        for entity_type, entities in result.get("entities_by_type", {}).items():
            if entity_type in personal_entity_types and entities:
                # Usar la entidad con mayor confianza
                best_entity = max(entities, key=lambda e: e.get("confidence", 0))
                personal_info[entity_type] = {
                    "value": best_entity.get("mention_text", ""),
                    "confidence": best_entity.get("confidence", 0.0)
                }
        
        # Construir resultado
        return {
            "personal_info": personal_info,
            "entities": result.get("entities", []),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def extract_business_information(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Extrae información de negocios de un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información de negocios extraída.
        """
        # Tipos de entidades de negocios comunes
        business_entity_types = [
            "company_name", "address", "phone_number", "email_address",
            "website", "tax_id", "registration_number", "industry"
        ]
        
        # Usar procesador de entidades de negocios o general
        processor_id = os.environ.get("DOCUMENT_AI_BUSINESS_PROCESSOR_ID", self.entity_processor_id)
        
        # Extraer entidades
        result = await self.extract_entities(
            document_data, mime_type, processor_id, None, business_entity_types
        )
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return result
        
        # Organizar información de negocios
        business_info = {}
        for entity_type, entities in result.get("entities_by_type", {}).items():
            if entity_type in business_entity_types and entities:
                # Usar la entidad con mayor confianza
                best_entity = max(entities, key=lambda e: e.get("confidence", 0))
                business_info[entity_type] = {
                    "value": best_entity.get("mention_text", ""),
                    "confidence": best_entity.get("confidence", 0.0)
                }
        
        # Construir resultado
        return {
            "business_info": business_info,
            "entities": result.get("entities", []),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def extract_medical_information(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Extrae información médica de un documento.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información médica extraída.
        """
        # Tipos de entidades médicas comunes
        medical_entity_types = [
            "condition", "medication", "procedure", "lab_result",
            "vital_sign", "allergy", "immunization", "diagnosis"
        ]
        
        # Usar procesador de entidades médicas o general
        processor_id = os.environ.get("DOCUMENT_AI_MEDICAL_PROCESSOR_ID", self.entity_processor_id)
        
        # Extraer entidades
        result = await self.extract_entities(
            document_data, mime_type, processor_id, "medical", medical_entity_types
        )
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return result
        
        # Organizar información médica por categorías
        medical_info = {}
        for entity_type, entities in result.get("entities_by_type", {}).items():
            if entity_type in medical_entity_types and entities:
                medical_info[entity_type] = []
                for entity in entities:
                    medical_info[entity_type].append({
                        "value": entity.get("mention_text", ""),
                        "confidence": entity.get("confidence", 0.0)
                    })
        
        # Construir resultado
        return {
            "medical_info": medical_info,
            "entities": result.get("entities", []),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def extract_invoice_information(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Extrae información de facturas.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información de la factura extraída.
        """
        # Usar procesador de facturas
        processor_id = os.environ.get("DOCUMENT_AI_INVOICE_PROCESSOR_ID", self.entity_processor_id)
        
        # Extraer entidades
        result = await self.extract_entities(
            document_data, mime_type, processor_id, "invoice"
        )
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return result
        
        # Organizar información de factura
        invoice_info = {
            "supplier": {},
            "customer": {},
            "invoice_details": {},
            "line_items": [],
            "payment_info": {},
            "totals": {}
        }
        
        # Extraer información específica de facturas
        entities_by_type = result.get("entities_by_type", {})
        
        # Extraer información del proveedor
        if "supplier_name" in entities_by_type and entities_by_type["supplier_name"]:
            invoice_info["supplier"]["name"] = entities_by_type["supplier_name"][0].get("mention_text", "")
        if "supplier_address" in entities_by_type and entities_by_type["supplier_address"]:
            invoice_info["supplier"]["address"] = entities_by_type["supplier_address"][0].get("mention_text", "")
        
        # Extraer información del cliente
        if "customer_name" in entities_by_type and entities_by_type["customer_name"]:
            invoice_info["customer"]["name"] = entities_by_type["customer_name"][0].get("mention_text", "")
        if "customer_address" in entities_by_type and entities_by_type["customer_address"]:
            invoice_info["customer"]["address"] = entities_by_type["customer_address"][0].get("mention_text", "")
        
        # Extraer detalles de la factura
        if "invoice_id" in entities_by_type and entities_by_type["invoice_id"]:
            invoice_info["invoice_details"]["id"] = entities_by_type["invoice_id"][0].get("mention_text", "")
        if "invoice_date" in entities_by_type and entities_by_type["invoice_date"]:
            invoice_info["invoice_details"]["date"] = entities_by_type["invoice_date"][0].get("mention_text", "")
        if "due_date" in entities_by_type and entities_by_type["due_date"]:
            invoice_info["invoice_details"]["due_date"] = entities_by_type["due_date"][0].get("mention_text", "")
        
        # Extraer totales
        if "total_amount" in entities_by_type and entities_by_type["total_amount"]:
            invoice_info["totals"]["total"] = entities_by_type["total_amount"][0].get("mention_text", "")
        if "tax_amount" in entities_by_type and entities_by_type["tax_amount"]:
            invoice_info["totals"]["tax"] = entities_by_type["tax_amount"][0].get("mention_text", "")
        if "subtotal_amount" in entities_by_type and entities_by_type["subtotal_amount"]:
            invoice_info["totals"]["subtotal"] = entities_by_type["subtotal_amount"][0].get("mention_text", "")
        
        # Extraer elementos de línea
        if "line_item" in entities_by_type:
            for item in entities_by_type["line_item"]:
                properties = item.get("properties", {})
                line_item = {
                    "description": properties.get("description", {}).get("mention_text", "") if "description" in properties else "",
                    "quantity": properties.get("quantity", {}).get("mention_text", "") if "quantity" in properties else "",
                    "unit_price": properties.get("unit_price", {}).get("mention_text", "") if "unit_price" in properties else "",
                    "amount": properties.get("amount", {}).get("mention_text", "") if "amount" in properties else ""
                }
                invoice_info["line_items"].append(line_item)
        
        # Construir resultado
        return {
            "invoice_info": invoice_info,
            "entities": result.get("entities", []),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

    async def extract_id_document_information(
        self,
        document_data: bytes,
        mime_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """Extrae información de documentos de identidad.

        Args:
            document_data: Datos binarios del documento.
            mime_type: Tipo MIME del documento.

        Returns:
            Diccionario con la información del documento de identidad extraída.
        """
        # Usar procesador de documentos de identidad
        processor_id = os.environ.get("DOCUMENT_AI_ID_PROCESSOR_ID", self.entity_processor_id)
        
        # Extraer entidades
        result = await self.extract_entities(
            document_data, mime_type, processor_id, "id_document"
        )
        
        # Si hay error, devolver el resultado
        if "error" in result:
            return result
        
        # Organizar información del documento de identidad
        id_info = {
            "personal_details": {},
            "document_details": {}
        }
        
        # Extraer información específica de documentos de identidad
        entities_by_type = result.get("entities_by_type", {})
        
        # Mapeo de tipos de entidades a campos en el resultado
        personal_fields = {
            "person_name": "name",
            "date_of_birth": "birth_date",
            "gender": "gender",
            "nationality": "nationality",
            "address": "address"
        }
        
        document_fields = {
            "id_number": "number",
            "document_type": "type",
            "issue_date": "issue_date",
            "expiration_date": "expiration_date",
            "issuing_authority": "issuing_authority"
        }
        
        # Extraer información personal
        for entity_type, field_name in personal_fields.items():
            if entity_type in entities_by_type and entities_by_type[entity_type]:
                best_entity = max(entities_by_type[entity_type], key=lambda e: e.get("confidence", 0))
                id_info["personal_details"][field_name] = {
                    "value": best_entity.get("mention_text", ""),
                    "confidence": best_entity.get("confidence", 0.0)
                }
        
        # Extraer información del documento
        for entity_type, field_name in document_fields.items():
            if entity_type in entities_by_type and entities_by_type[entity_type]:
                best_entity = max(entities_by_type[entity_type], key=lambda e: e.get("confidence", 0))
                id_info["document_details"][field_name] = {
                    "value": best_entity.get("mention_text", ""),
                    "confidence": best_entity.get("confidence", 0.0)
                }
        
        # Construir resultado
        return {
            "id_document_info": id_info,
            "entities": result.get("entities", []),
            "success": True,
            "text": result.get("text", ""),
            "mime_type": mime_type
        }

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
