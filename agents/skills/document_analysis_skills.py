"""
Skills para análisis de documentos y reconocimiento de objetos.

Este módulo proporciona skills que permiten a los agentes utilizar las capacidades
de procesamiento de documentos estructurados y reconocimiento de objetos específicos.
"""

import asyncio
from typing import Any, Dict, List, Union

from core.logging_config import get_logger
from infrastructure.adapters.document_adapter import document_adapter
from infrastructure.adapters.telemetry_adapter import measure_execution_time

# Configurar logger
logger = get_logger(__name__)


@measure_execution_time("skills.extract_tables_from_document")
async def extract_tables_from_document(
    image_data: Union[str, bytes, Dict[str, Any]],
    language_code: str = "es-ES",
    agent_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Extrae tablas de un documento o imagen.

    Args:
        image_data: Datos de la imagen (base64, bytes o dict con url o path)
        language_code: Código de idioma para el OCR
        agent_id: ID del agente que realiza la solicitud

    Returns:
        Dict[str, Any]: Tablas extraídas y metadatos
    """
    try:
        # Asegurar que el adaptador esté inicializado
        if not document_adapter.is_initialized:
            await document_adapter.initialize()

        # Llamar al adaptador para extraer tablas
        result = await document_adapter.extract_tables(
            image_data=image_data, language_code=language_code, agent_id=agent_id
        )

        # Procesar el resultado para el agente
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "tables": [],
                "message": f"Error al extraer tablas: {result['error']}",
            }

        # Formatear tablas para presentación
        tables_info = []
        for i, table in enumerate(result.get("tables", [])):
            table_info = {
                "id": table.get("table_id", f"tabla_{i+1}"),
                "rows": len(table.get("rows", [])),
                "columns": len(table.get("headers", [])),
                "headers": table.get("headers", []),
                "data": table.get("rows", []),
                "confidence": table.get("confidence", 0.0),
            }
            tables_info.append(table_info)

        return {
            "success": True,
            "tables": tables_info,
            "count": len(tables_info),
            "metadata": result.get("metadata", {}),
            "message": f"Se encontraron {len(tables_info)} tablas en el documento.",
        }

    except Exception as e:
        logger.error(f"Error en skill extract_tables_from_document: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "tables": [],
            "message": f"Error al procesar el documento: {str(e)}",
        }


@measure_execution_time("skills.extract_forms_from_document")
async def extract_forms_from_document(
    image_data: Union[str, bytes, Dict[str, Any]],
    language_code: str = "es-ES",
    agent_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Extrae datos de formularios de un documento o imagen.

    Args:
        image_data: Datos de la imagen (base64, bytes o dict con url o path)
        language_code: Código de idioma para el OCR
        agent_id: ID del agente que realiza la solicitud

    Returns:
        Dict[str, Any]: Datos de formularios extraídos y metadatos
    """
    try:
        # Asegurar que el adaptador esté inicializado
        if not document_adapter.is_initialized:
            await document_adapter.initialize()

        # Llamar al adaptador para extraer formularios
        result = await document_adapter.extract_forms(
            image_data=image_data, language_code=language_code, agent_id=agent_id
        )

        # Procesar el resultado para el agente
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "form_fields": [],
                "message": f"Error al extraer formularios: {result['error']}",
            }

        # Formatear campos para presentación
        fields_info = []
        for field in result.get("form_fields", []):
            field_info = {
                "id": field.get("field_id", ""),
                "label": field.get("label", ""),
                "type": field.get("type", ""),
                "value": field.get("value", ""),
                "confidence": field.get("confidence", 0.0),
            }
            fields_info.append(field_info)

        # Organizar campos por tipo
        fields_by_type = {}
        for field in fields_info:
            field_type = field["type"]
            if field_type not in fields_by_type:
                fields_by_type[field_type] = []
            fields_by_type[field_type].append(field)

        return {
            "success": True,
            "form_fields": fields_info,
            "fields_by_type": fields_by_type,
            "count": len(fields_info),
            "metadata": result.get("metadata", {}),
            "message": f"Se encontraron {len(fields_info)} campos en el formulario.",
        }

    except Exception as e:
        logger.error(f"Error en skill extract_forms_from_document: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "form_fields": [],
            "message": f"Error al procesar el formulario: {str(e)}",
        }


@measure_execution_time("skills.recognize_objects_in_image")
async def recognize_objects_in_image(
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
        agent_id: ID del agente que realiza la solicitud

    Returns:
        Dict[str, Any]: Objetos reconocidos y metadatos
    """
    try:
        # Asegurar que el adaptador esté inicializado
        if not document_adapter.is_initialized:
            await document_adapter.initialize()

        # Llamar al adaptador para reconocer objetos
        result = await document_adapter.recognize_objects(
            image_data=image_data,
            domain=domain,
            confidence_threshold=confidence_threshold,
            agent_id=agent_id,
        )

        # Procesar el resultado para el agente
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "objects": [],
                "message": f"Error al reconocer objetos: {result['error']}",
            }

        # Formatear detecciones para presentación
        objects_info = []
        for detection in result.get("detections", []):
            object_info = {
                "id": detection.get("object_id", ""),
                "label": detection.get("label", ""),
                "confidence": detection.get("confidence", 0.0),
                "position": detection.get("bounding_box", {}),
            }
            objects_info.append(object_info)

        # Agrupar objetos por etiqueta
        objects_by_label = {}
        for obj in objects_info:
            label = obj["label"]
            if label not in objects_by_label:
                objects_by_label[label] = []
            objects_by_label[label].append(obj)

        # Contar objetos por etiqueta
        label_counts = {label: len(objs) for label, objs in objects_by_label.items()}

        return {
            "success": True,
            "objects": objects_info,
            "objects_by_label": objects_by_label,
            "label_counts": label_counts,
            "count": len(objects_info),
            "domain": domain,
            "domain_info": result.get("domain_info", {}),
            "metadata": result.get("metadata", {}),
            "message": f"Se encontraron {len(objects_info)} objetos en la imagen del dominio '{domain}'.",
        }

    except Exception as e:
        logger.error(f"Error en skill recognize_objects_in_image: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "objects": [],
            "message": f"Error al reconocer objetos en la imagen: {str(e)}",
        }


@measure_execution_time("skills.register_custom_recognition_domain")
async def register_custom_recognition_domain(
    domain_name: str,
    objects: List[str],
    description: str = "",
    agent_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Registra un dominio personalizado con objetos específicos para reconocimiento.

    Args:
        domain_name: Nombre del dominio personalizado
        objects: Lista de objetos a reconocer en este dominio
        description: Descripción del dominio
        agent_id: ID del agente que realiza la solicitud

    Returns:
        Dict[str, Any]: Información del dominio registrado
    """
    try:
        # Asegurar que el adaptador esté inicializado
        if not document_adapter.is_initialized:
            await document_adapter.initialize()

        # Validar entrada
        if not domain_name or not objects:
            return {
                "success": False,
                "error": "Se requiere un nombre de dominio y al menos un objeto",
                "message": "No se pudo registrar el dominio: faltan datos requeridos.",
            }

        # Llamar al adaptador para registrar dominio
        result = await document_adapter.register_custom_domain(
            domain_name=domain_name,
            objects=objects,
            description=description,
            agent_id=agent_id,
        )

        # Procesar el resultado para el agente
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "message": f"Error al registrar dominio: {result['error']}",
            }

        return {
            "success": True,
            "domain_key": result.get("domain_key", ""),
            "name": result.get("name", ""),
            "description": result.get("description", ""),
            "objects": result.get("objects", []),
            "object_count": len(result.get("objects", [])),
            "message": f"Dominio '{domain_name}' registrado con éxito con {len(objects)} objetos.",
        }

    except Exception as e:
        logger.error(
            f"Error en skill register_custom_recognition_domain: {e}", exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "message": f"Error al registrar dominio personalizado: {str(e)}",
        }


@measure_execution_time("skills.get_available_recognition_domains")
async def get_available_recognition_domains() -> Dict[str, Any]:
    """
    Obtiene la lista de dominios disponibles para reconocimiento de objetos.

    Returns:
        Dict[str, Any]: Información de dominios disponibles
    """
    try:
        # Asegurar que el adaptador esté inicializado
        if not document_adapter.is_initialized:
            await document_adapter.initialize()

        # Llamar al adaptador para obtener dominios
        result = await document_adapter.get_available_domains()

        # Procesar el resultado para el agente
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "domains": [],
                "message": f"Error al obtener dominios: {result['error']}",
            }

        # Formatear dominios para presentación
        domains_info = []
        for domain_key, domain_data in result.get("domains", {}).items():
            domain_info = {
                "key": domain_key,
                "name": domain_data.get("name", ""),
                "description": domain_data.get("description", ""),
                "object_count": len(domain_data.get("objects", [])),
                "objects": domain_data.get("objects", []),
                "custom": domain_data.get("custom", False),
            }
            domains_info.append(domain_info)

        # Separar dominios predefinidos y personalizados
        predefined_domains = [d for d in domains_info if not d.get("custom")]
        custom_domains = [d for d in domains_info if d.get("custom")]

        return {
            "success": True,
            "domains": domains_info,
            "predefined_domains": predefined_domains,
            "custom_domains": custom_domains,
            "count": len(domains_info),
            "message": f"Se encontraron {len(domains_info)} dominios disponibles.",
        }

    except Exception as e:
        logger.error(
            f"Error en skill get_available_recognition_domains: {e}", exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "domains": [],
            "message": f"Error al obtener dominios disponibles: {str(e)}",
        }


@measure_execution_time("skills.process_document_with_image")
async def process_document_with_image(
    image_data: Union[str, bytes, Dict[str, Any]],
    extract_tables: bool = True,
    extract_forms: bool = True,
    recognize_objects: bool = True,
    domain: str = "general",
    language_code: str = "es-ES",
    confidence_threshold: float = 0.5,
    agent_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Procesa un documento o imagen aplicando múltiples análisis en paralelo.

    Args:
        image_data: Datos de la imagen (base64, bytes o dict con url o path)
        extract_tables: Si se deben extraer tablas
        extract_forms: Si se deben extraer formularios
        recognize_objects: Si se deben reconocer objetos
        domain: Dominio para reconocimiento de objetos
        language_code: Código de idioma para OCR
        confidence_threshold: Umbral de confianza para detecciones
        agent_id: ID del agente que realiza la solicitud

    Returns:
        Dict[str, Any]: Resultados combinados de todos los análisis solicitados
    """
    try:
        # Asegurar que el adaptador esté inicializado
        if not document_adapter.is_initialized:
            await document_adapter.initialize()

        # Preparar tareas a ejecutar en paralelo
        tasks = []

        if extract_tables:
            tasks.append(
                extract_tables_from_document(image_data, language_code, agent_id)
            )

        if extract_forms:
            tasks.append(
                extract_forms_from_document(image_data, language_code, agent_id)
            )

        if recognize_objects:
            tasks.append(
                recognize_objects_in_image(
                    image_data, domain, confidence_threshold, agent_id
                )
            )

        # Ejecutar tareas en paralelo
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            return {
                "success": False,
                "error": "No se seleccionó ningún tipo de análisis",
                "message": "Debe seleccionar al menos un tipo de análisis (tablas, formularios u objetos).",
            }

        # Procesar resultados
        combined_result = {
            "success": True,
            "analyses_requested": 0,
            "analyses_completed": 0,
            "analyses_failed": 0,
        }

        for i, result in enumerate(results):
            # Manejar excepciones
            if isinstance(result, Exception):
                analysis_type = (
                    ["tables", "forms", "objects"][i] if i < 3 else f"analysis_{i}"
                )
                combined_result[analysis_type] = {
                    "success": False,
                    "error": str(result),
                    "message": f"Error en análisis de {analysis_type}: {str(result)}",
                }
                combined_result["analyses_failed"] += 1
                continue

            # Agregar resultado al combinado
            if extract_tables and "tables" in result:
                combined_result["tables"] = result
                if result.get("success", False):
                    combined_result["analyses_completed"] += 1
                else:
                    combined_result["analyses_failed"] += 1
                combined_result["analyses_requested"] += 1

            if extract_forms and "form_fields" in result:
                combined_result["forms"] = result
                if result.get("success", False):
                    combined_result["analyses_completed"] += 1
                else:
                    combined_result["analyses_failed"] += 1
                combined_result["analyses_requested"] += 1

            if recognize_objects and "objects" in result:
                combined_result["objects"] = result
                if result.get("success", False):
                    combined_result["analyses_completed"] += 1
                else:
                    combined_result["analyses_failed"] += 1
                combined_result["analyses_requested"] += 1

        # Generar mensaje resumen
        message_parts = []

        if "tables" in combined_result and combined_result["tables"].get(
            "success", False
        ):
            table_count = combined_result["tables"].get("count", 0)
            message_parts.append(f"{table_count} tablas")

        if "forms" in combined_result and combined_result["forms"].get(
            "success", False
        ):
            field_count = combined_result["forms"].get("count", 0)
            message_parts.append(f"{field_count} campos de formulario")

        if "objects" in combined_result and combined_result["objects"].get(
            "success", False
        ):
            object_count = combined_result["objects"].get("count", 0)
            message_parts.append(f"{object_count} objetos")

        if message_parts:
            combined_result["message"] = (
                f"Análisis completado. Se encontraron: {', '.join(message_parts)}."
            )
        else:
            combined_result["message"] = (
                "Análisis completado, pero no se encontraron elementos."
            )

        # Actualizar estado general
        combined_result["success"] = (
            combined_result["analyses_failed"] < combined_result["analyses_requested"]
        )

        return combined_result

    except Exception as e:
        logger.error(f"Error en skill process_document_with_image: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error al procesar documento con imagen: {str(e)}",
        }
