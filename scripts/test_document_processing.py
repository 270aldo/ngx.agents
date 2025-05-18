"""
Script para probar las capacidades de procesamiento de documentos.

Este script demuestra el uso del adaptador de documentos para procesar
diferentes tipos de documentos y extraer información de ellos.
"""

import asyncio
import argparse
import os
import sys
import json
from typing import Dict, Any, Optional, List

# Añadir el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.adapters.document_adapter import document_adapter

async def process_document(file_path: str, operation: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Procesa un documento con la operación especificada.

    Args:
        file_path: Ruta al archivo a procesar.
        operation: Operación a realizar (process, extract_text, classify, etc.).
        options: Opciones adicionales para el procesamiento.

    Returns:
        Resultado del procesamiento.
    """
    print(f"Procesando documento: {file_path}")
    print(f"Operación: {operation}")
    print(f"Opciones: {options}")
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        return {"error": f"El archivo {file_path} no existe", "success": False}
    
    # Inicializar el adaptador de documentos
    await document_adapter.initialize()
    
    # Realizar la operación correspondiente
    if operation == "process":
        result = await document_adapter.process_document(file_path, options)
    elif operation == "extract_text":
        result = await document_adapter.extract_text(file_path, options)
    elif operation == "classify":
        result = await document_adapter.classify_document(file_path, options)
    elif operation == "extract_entities":
        result = await document_adapter.extract_entities(file_path, options)
    elif operation == "process_form":
        result = await document_adapter.process_form(file_path, options)
    elif operation == "extract_personal":
        result = await document_adapter.extract_personal_information(file_path, options)
    elif operation == "extract_business":
        result = await document_adapter.extract_business_information(file_path, options)
    elif operation == "extract_medical":
        result = await document_adapter.extract_medical_information(file_path, options)
    elif operation == "extract_invoice":
        result = await document_adapter.extract_invoice_information(file_path, options)
    elif operation == "extract_id":
        result = await document_adapter.extract_id_document_information(file_path, options)
    elif operation == "analyze":
        result = await document_adapter.analyze_document(file_path, options)
    else:
        return {"error": f"Operación {operation} no soportada", "success": False}
    
    return result

async def batch_process_documents(file_paths: List[str], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Procesa múltiples documentos en batch.

    Args:
        file_paths: Lista de rutas a los archivos a procesar.
        options: Opciones adicionales para el procesamiento.

    Returns:
        Lista de resultados del procesamiento.
    """
    print(f"Procesando {len(file_paths)} documentos en batch")
    print(f"Opciones: {options}")
    
    # Verificar que los archivos existen
    documents = []
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"Advertencia: El archivo {file_path} no existe y será omitido")
        else:
            documents.append((file_path, {"mime_type": None}))
    
    if not documents:
        return [{"error": "No se encontraron archivos válidos", "success": False}]
    
    # Inicializar el adaptador de documentos
    await document_adapter.initialize()
    
    # Procesar documentos en batch
    return await document_adapter.batch_process_documents(documents, options)

async def get_available_processors() -> Dict[str, Any]:
    """Obtiene los procesadores disponibles.

    Returns:
        Información sobre los procesadores disponibles.
    """
    print("Obteniendo procesadores disponibles...")
    
    # Inicializar el adaptador de documentos
    await document_adapter.initialize()
    
    # Obtener procesadores disponibles
    return await document_adapter.get_available_processors()

async def get_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del adaptador de documentos.

    Returns:
        Estadísticas de uso.
    """
    print("Obteniendo estadísticas...")
    
    # Inicializar el adaptador de documentos
    await document_adapter.initialize()
    
    # Obtener estadísticas
    return await document_adapter.get_stats()

def print_result(result: Dict[str, Any], output_format: str = "pretty") -> None:
    """Imprime el resultado del procesamiento.

    Args:
        result: Resultado del procesamiento.
        output_format: Formato de salida (pretty, json).
    """
    if output_format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Formato pretty
        print("\n=== RESULTADO ===")
        
        # Verificar si hay error
        if "error" in result:
            print(f"ERROR: {result['error']}")
            return
        
        # Imprimir información básica
        print(f"Éxito: {result.get('success', False)}")
        
        # Imprimir tipo de documento si está disponible
        if "document_type" in result:
            print(f"Tipo de documento: {result['document_type']}")
            if "confidence" in result:
                print(f"Confianza: {result['confidence']:.2f}")
        
        # Imprimir texto si está disponible
        if "text" in result:
            text = result["text"]
            if len(text) > 500:
                text = text[:500] + "..."
            print(f"\nTexto: {text}")
        
        # Imprimir entidades si están disponibles
        if "entities" in result and result["entities"]:
            print("\nEntidades:")
            for i, entity in enumerate(result["entities"][:10]):  # Limitar a 10 entidades
                print(f"  {i+1}. Tipo: {entity.get('type', 'desconocido')}")
                print(f"     Texto: {entity.get('mention_text', '')}")
                print(f"     Confianza: {entity.get('confidence', 0):.2f}")
            
            if len(result["entities"]) > 10:
                print(f"  ... y {len(result['entities']) - 10} más")
        
        # Imprimir campos de formulario si están disponibles
        if "form_fields" in result and result["form_fields"]:
            print("\nCampos de formulario:")
            for key, value in result["form_fields"].items():
                print(f"  {key}: {value}")
        
        # Imprimir información específica según el tipo de documento
        if "invoice_info" in result:
            print("\nInformación de factura:")
            invoice_info = result["invoice_info"]
            if "supplier" in invoice_info and invoice_info["supplier"]:
                print(f"  Proveedor: {invoice_info['supplier'].get('name', '')}")
            if "customer" in invoice_info and invoice_info["customer"]:
                print(f"  Cliente: {invoice_info['customer'].get('name', '')}")
            if "totals" in invoice_info and invoice_info["totals"]:
                print(f"  Total: {invoice_info['totals'].get('total', '')}")
        
        elif "id_document_info" in result:
            print("\nInformación de documento de identidad:")
            id_info = result["id_document_info"]
            if "personal_details" in id_info and id_info["personal_details"]:
                personal = id_info["personal_details"]
                if "name" in personal:
                    print(f"  Nombre: {personal['name'].get('value', '')}")
                if "birth_date" in personal:
                    print(f"  Fecha de nacimiento: {personal['birth_date'].get('value', '')}")
            if "document_details" in id_info and id_info["document_details"]:
                doc_details = id_info["document_details"]
                if "number" in doc_details:
                    print(f"  Número: {doc_details['number'].get('value', '')}")
                if "expiration_date" in doc_details:
                    print(f"  Fecha de expiración: {doc_details['expiration_date'].get('value', '')}")
        
        elif "personal_info" in result:
            print("\nInformación personal:")
            for key, value in result["personal_info"].items():
                print(f"  {key}: {value.get('value', '')} (confianza: {value.get('confidence', 0):.2f})")
        
        elif "business_info" in result:
            print("\nInformación de negocios:")
            for key, value in result["business_info"].items():
                print(f"  {key}: {value.get('value', '')} (confianza: {value.get('confidence', 0):.2f})")
        
        elif "medical_info" in result:
            print("\nInformación médica:")
            for category, items in result["medical_info"].items():
                print(f"  {category}:")
                for item in items[:3]:  # Limitar a 3 items por categoría
                    print(f"    - {item.get('value', '')} (confianza: {item.get('confidence', 0):.2f})")
                if len(items) > 3:
                    print(f"    ... y {len(items) - 3} más")

def print_batch_results(results: List[Dict[str, Any]], output_format: str = "pretty") -> None:
    """Imprime los resultados del procesamiento en batch.

    Args:
        results: Lista de resultados del procesamiento.
        output_format: Formato de salida (pretty, json).
    """
    if output_format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        # Formato pretty
        print("\n=== RESULTADOS DEL BATCH ===")
        print(f"Total de documentos procesados: {len(results)}")
        
        # Contar éxitos y errores
        success_count = sum(1 for r in results if r.get("success", False))
        error_count = len(results) - success_count
        
        print(f"Éxitos: {success_count}")
        print(f"Errores: {error_count}")
        
        # Imprimir resumen de cada documento
        for i, result in enumerate(results):
            print(f"\n--- Documento {i+1} ---")
            
            # Verificar si hay error
            if "error" in result:
                print(f"ERROR: {result['error']}")
                continue
            
            # Imprimir información básica
            print(f"Éxito: {result.get('success', False)}")
            
            # Imprimir tipo de documento si está disponible
            if "document_type" in result:
                print(f"Tipo de documento: {result['document_type']}")
            
            # Imprimir texto truncado si está disponible
            if "text" in result:
                text = result["text"]
                if len(text) > 100:
                    text = text[:100] + "..."
                print(f"Texto: {text}")
            
            # Imprimir número de entidades si están disponibles
            if "entities" in result:
                print(f"Entidades: {len(result['entities'])}")

def print_processors(result: Dict[str, Any], output_format: str = "pretty") -> None:
    """Imprime la información de los procesadores disponibles.

    Args:
        result: Resultado de la consulta de procesadores.
        output_format: Formato de salida (pretty, json).
    """
    if output_format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Formato pretty
        print("\n=== PROCESADORES DISPONIBLES ===")
        
        # Verificar si hay error
        if "error" in result:
            print(f"ERROR: {result['error']}")
            return
        
        # Imprimir información básica
        print(f"Éxito: {result.get('success', False)}")
        print(f"Total de procesadores: {result.get('count', 0)}")
        
        # Imprimir procesadores
        if "processors" in result and result["processors"]:
            for i, processor in enumerate(result["processors"]):
                print(f"\n--- Procesador {i+1} ---")
                print(f"ID: {processor.get('processor_id', '')}")
                print(f"Nombre: {processor.get('display_name', '')}")
                print(f"Tipo: {processor.get('type', '')}")
                print(f"Estado: {processor.get('state', '')}")

def print_stats(result: Dict[str, Any], output_format: str = "pretty") -> None:
    """Imprime las estadísticas del adaptador de documentos.

    Args:
        result: Resultado de la consulta de estadísticas.
        output_format: Formato de salida (pretty, json).
    """
    if output_format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Formato pretty
        print("\n=== ESTADÍSTICAS ===")
        
        # Verificar si hay error
        if "error" in result:
            print(f"ERROR: {result['error']}")
            return
        
        # Imprimir estadísticas básicas
        print(f"Operaciones de procesamiento: {result.get('process_operations', 0)}")
        print(f"Operaciones de extracción: {result.get('extract_operations', 0)}")
        print(f"Operaciones de clasificación: {result.get('classify_operations', 0)}")
        print(f"Errores: {result.get('errors', 0)}")
        print(f"Latencia promedio: {result.get('avg_latency_ms', 0):.2f} ms")
        print(f"Modo simulado: {result.get('mock_mode', False)}")
        
        # Imprimir tipos de documentos procesados
        if "document_types" in result and result["document_types"]:
            print("\nTipos de documentos procesados:")
            for doc_type, count in result["document_types"].items():
                print(f"  {doc_type}: {count}")

async def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Prueba de procesamiento de documentos")
    
    # Argumentos generales
    parser.add_argument("--mock", action="store_true", help="Usar modo simulado")
    parser.add_argument("--format", choices=["pretty", "json"], default="pretty", help="Formato de salida")
    
    # Subparsers para diferentes comandos
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")
    
    # Comando process
    process_parser = subparsers.add_parser("process", help="Procesar un documento")
    process_parser.add_argument("file", help="Ruta al archivo a procesar")
    process_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    process_parser.add_argument("--processor-id", help="ID del procesador a utilizar")
    process_parser.add_argument("--document-type", help="Tipo de documento")
    process_parser.add_argument("--no-auto-classify", action="store_true", help="No clasificar automáticamente el documento")
    
    # Comando extract_text
    extract_text_parser = subparsers.add_parser("extract_text", help="Extraer texto de un documento")
    extract_text_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_text_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    extract_text_parser.add_argument("--processor-id", help="ID del procesador a utilizar")
    
    # Comando classify
    classify_parser = subparsers.add_parser("classify", help="Clasificar un documento")
    classify_parser.add_argument("file", help="Ruta al archivo a procesar")
    classify_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    classify_parser.add_argument("--processor-id", help="ID del procesador a utilizar")
    classify_parser.add_argument("--confidence-threshold", type=float, default=0.5, help="Umbral de confianza para incluir clasificaciones")
    
    # Comando extract_entities
    extract_entities_parser = subparsers.add_parser("extract_entities", help="Extraer entidades de un documento")
    extract_entities_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_entities_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    extract_entities_parser.add_argument("--processor-id", help="ID del procesador a utilizar")
    extract_entities_parser.add_argument("--document-type", help="Tipo de documento")
    extract_entities_parser.add_argument("--entity-types", nargs="+", help="Tipos de entidades a extraer")
    
    # Comando process_form
    process_form_parser = subparsers.add_parser("process_form", help="Procesar un formulario")
    process_form_parser.add_argument("file", help="Ruta al archivo a procesar")
    process_form_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    process_form_parser.add_argument("--processor-id", help="ID del procesador a utilizar")
    
    # Comando extract_personal
    extract_personal_parser = subparsers.add_parser("extract_personal", help="Extraer información personal")
    extract_personal_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_personal_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    
    # Comando extract_business
    extract_business_parser = subparsers.add_parser("extract_business", help="Extraer información de negocios")
    extract_business_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_business_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    
    # Comando extract_medical
    extract_medical_parser = subparsers.add_parser("extract_medical", help="Extraer información médica")
    extract_medical_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_medical_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    
    # Comando extract_invoice
    extract_invoice_parser = subparsers.add_parser("extract_invoice", help="Extraer información de facturas")
    extract_invoice_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_invoice_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    
    # Comando extract_id
    extract_id_parser = subparsers.add_parser("extract_id", help="Extraer información de documentos de identidad")
    extract_id_parser.add_argument("file", help="Ruta al archivo a procesar")
    extract_id_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    
    # Comando analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analizar un documento")
    analyze_parser.add_argument("file", help="Ruta al archivo a procesar")
    analyze_parser.add_argument("--mime-type", help="Tipo MIME del documento")
    
    # Comando batch
    batch_parser = subparsers.add_parser("batch", help="Procesar múltiples documentos en batch")
    batch_parser.add_argument("files", nargs="+", help="Rutas a los archivos a procesar")
    batch_parser.add_argument("--processor-id", help="ID del procesador a utilizar")
    batch_parser.add_argument("--no-auto-classify", action="store_true", help="No clasificar automáticamente los documentos")
    
    # Comando processors
    processors_parser = subparsers.add_parser("processors", help="Obtener procesadores disponibles")
    
    # Comando stats
    stats_parser = subparsers.add_parser("stats", help="Obtener estadísticas")
    
    args = parser.parse_args()
    
    # Configurar modo simulado
    if args.mock:
        document_adapter.mock_mode = True
    
    # Ejecutar el comando correspondiente
    if args.command == "process":
        options = {
            "mime_type": args.mime_type,
            "processor_id": args.processor_id,
            "document_type": args.document_type,
            "auto_classify": not args.no_auto_classify
        }
        result = await process_document(args.file, "process", options)
        print_result(result, args.format)
    
    elif args.command == "extract_text":
        options = {
            "mime_type": args.mime_type,
            "processor_id": args.processor_id
        }
        result = await process_document(args.file, "extract_text", options)
        print_result(result, args.format)
    
    elif args.command == "classify":
        options = {
            "mime_type": args.mime_type,
            "processor_id": args.processor_id,
            "confidence_threshold": args.confidence_threshold
        }
        result = await process_document(args.file, "classify", options)
        print_result(result, args.format)
    
    elif args.command == "extract_entities":
        options = {
            "mime_type": args.mime_type,
            "processor_id": args.processor_id,
            "document_type": args.document_type,
            "entity_types": args.entity_types
        }
        result = await process_document(args.file, "extract_entities", options)
        print_result(result, args.format)
    
    elif args.command == "process_form":
        options = {
            "mime_type": args.mime_type,
            "processor_id": args.processor_id
        }
        result = await process_document(args.file, "process_form", options)
        print_result(result, args.format)
    
    elif args.command == "extract_personal":
        options = {
            "mime_type": args.mime_type
        }
        result = await process_document(args.file, "extract_personal", options)
        print_result(result, args.format)
    
    elif args.command == "extract_business":
        options = {
            "mime_type": args.mime_type
        }
        result = await process_document(args.file, "extract_business", options)
        print_result(result, args.format)
    
    elif args.command == "extract_medical":
        options = {
            "mime_type": args.mime_type
        }
        result = await process_document(args.file, "extract_medical", options)
        print_result(result, args.format)
    
    elif args.command == "extract_invoice":
        options = {
            "mime_type": args.mime_type
        }
        result = await process_document(args.file, "extract_invoice", options)
        print_result(result, args.format)
    
    elif args.command == "extract_id":
        options = {
            "mime_type": args.mime_type
        }
        result = await process_document(args.file, "extract_id", options)
        print_result(result, args.format)
    
    elif args.command == "analyze":
        options = {
            "mime_type": args.mime_type
        }
        result = await process_document(args.file, "analyze", options)
        print_result(result, args.format)
    
    elif args.command == "batch":
        options = {
            "processor_id": args.processor_id,
            "auto_classify": not args.no_auto_classify
        }
        results = await batch_process_documents(args.files, options)
        print_batch_results(results, args.format)
    
    elif args.command == "processors":
        result = await get_available_processors()
        print_processors(result, args.format)
    
    elif args.command == "stats":
        result = await get_stats()
        print_stats(result, args.format)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
