"""
Ejemplo de uso del adaptador de documentos.

Este script muestra cómo utilizar el adaptador de documentos para procesar
diferentes tipos de documentos y extraer información de ellos.
"""

import asyncio
import os
import sys
import json
from typing import Dict, Any

# Añadir el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.adapters.document_adapter import document_adapter

async def main():
    """Función principal del ejemplo."""
    print("=== Ejemplo de Procesamiento de Documentos ===")
    
    # Inicializar el adaptador de documentos en modo simulado
    document_adapter.mock_mode = True
    await document_adapter.initialize()
    print("Adaptador de documentos inicializado en modo simulado")
    
    # Ejemplo 1: Clasificar un documento
    print("\n--- Ejemplo 1: Clasificar un documento ---")
    # En un caso real, usaríamos un archivo real
    # Aquí simulamos un documento PDF
    mock_document = b"%PDF-1.5\nMock PDF document for testing"
    
    result = await document_adapter.classify_document(
        mock_document,
        {"mime_type": "application/pdf"}
    )
    
    print("Resultado de la clasificación:")
    print(f"Tipo de documento: {result.get('document_type', 'desconocido')}")
    print(f"Confianza: {result.get('confidence', 0):.2f}")
    print("Clasificaciones:")
    for classification in result.get("classifications", []):
        print(f"  - {classification.get('name', '')}: {classification.get('confidence', 0):.2f}")
    
    # Ejemplo 2: Extraer texto de un documento
    print("\n--- Ejemplo 2: Extraer texto de un documento ---")
    # Simulamos un documento de imagen
    mock_image = b"\xFF\xD8\xFFMock JPEG image for testing"
    
    result = await document_adapter.extract_text(
        mock_image,
        {"mime_type": "image/jpeg"}
    )
    
    print("Resultado de la extracción de texto:")
    print(f"Éxito: {result.get('success', False)}")
    print(f"Texto: {result.get('text', '')[:100]}...")
    
    # Ejemplo 3: Extraer entidades de un documento
    print("\n--- Ejemplo 3: Extraer entidades de un documento ---")
    # Simulamos un documento de factura
    mock_invoice = b"%PDF-1.5\nMock invoice document for testing"
    
    result = await document_adapter.extract_entities(
        mock_invoice,
        {
            "mime_type": "application/pdf",
            "document_type": "invoice",
            "entity_types": ["supplier_name", "customer_name", "total_amount"]
        }
    )
    
    print("Resultado de la extracción de entidades:")
    print(f"Éxito: {result.get('success', False)}")
    print(f"Total de entidades: {len(result.get('entities', []))}")
    print("Entidades por tipo:")
    for entity_type, entities in result.get("entities_by_type", {}).items():
        print(f"  {entity_type}: {len(entities)} entidades")
        for entity in entities[:2]:  # Mostrar solo las primeras 2 entidades
            print(f"    - {entity.get('mention_text', '')} (confianza: {entity.get('confidence', 0):.2f})")
    
    # Ejemplo 4: Procesar un formulario
    print("\n--- Ejemplo 4: Procesar un formulario ---")
    # Simulamos un documento de formulario
    mock_form = b"%PDF-1.5\nMock form document for testing"
    
    result = await document_adapter.process_form(
        mock_form,
        {"mime_type": "application/pdf"}
    )
    
    print("Resultado del procesamiento de formulario:")
    print(f"Éxito: {result.get('success', False)}")
    print("Campos del formulario:")
    for key, value in result.get("form_fields", {}).items():
        print(f"  {key}: {value}")
    
    # Ejemplo 5: Análisis completo de un documento
    print("\n--- Ejemplo 5: Análisis completo de un documento ---")
    # Simulamos un documento de identidad
    mock_id = b"%PDF-1.5\nMock ID document for testing"
    
    result = await document_adapter.analyze_document(
        mock_id,
        {"mime_type": "application/pdf"}
    )
    
    print("Resultado del análisis completo:")
    print(f"Éxito: {result.get('success', False)}")
    print(f"Tipo de documento: {result.get('document_type', 'desconocido')}")
    print(f"Confianza: {result.get('confidence', 0):.2f}")
    
    # Si es un documento de identidad, mostrar información específica
    if "id_document_info" in result:
        id_info = result["id_document_info"]
        print("\nInformación del documento de identidad:")
        
        if "personal_details" in id_info:
            personal = id_info["personal_details"]
            print("  Detalles personales:")
            for key, value in personal.items():
                print(f"    {key}: {value.get('value', '')} (confianza: {value.get('confidence', 0):.2f})")
        
        if "document_details" in id_info:
            doc_details = id_info["document_details"]
            print("  Detalles del documento:")
            for key, value in doc_details.items():
                print(f"    {key}: {value.get('value', '')} (confianza: {value.get('confidence', 0):.2f})")
    
    # Ejemplo 6: Procesamiento en batch
    print("\n--- Ejemplo 6: Procesamiento en batch ---")
    # Simulamos varios documentos
    mock_documents = [
        (b"%PDF-1.5\nMock invoice document for testing", {"mime_type": "application/pdf"}),
        (b"%PDF-1.5\nMock form document for testing", {"mime_type": "application/pdf"}),
        (b"\xFF\xD8\xFFMock JPEG image for testing", {"mime_type": "image/jpeg"})
    ]
    
    results = await document_adapter.batch_process_documents(
        mock_documents,
        {"auto_classify": True}
    )
    
    print("Resultado del procesamiento en batch:")
    print(f"Total de documentos procesados: {len(results)}")
    
    for i, result in enumerate(results):
        print(f"\nDocumento {i+1}:")
        print(f"  Éxito: {result.get('success', False)}")
        print(f"  Tipo de documento: {result.get('document_type', 'desconocido')}")
        text = result.get("text", "")
        print(f"  Texto: {text[:50]}..." if text else "  Texto: N/A")
    
    # Ejemplo 7: Obtener procesadores disponibles
    print("\n--- Ejemplo 7: Obtener procesadores disponibles ---")
    
    result = await document_adapter.get_available_processors()
    
    print("Procesadores disponibles:")
    print(f"Total de procesadores: {result.get('count', 0)}")
    
    for i, processor in enumerate(result.get("processors", [])[:3]):  # Mostrar solo los primeros 3 procesadores
        print(f"  {i+1}. {processor.get('display_name', '')} ({processor.get('type', '')})")
    
    # Ejemplo 8: Obtener estadísticas
    print("\n--- Ejemplo 8: Obtener estadísticas ---")
    
    result = await document_adapter.get_stats()
    
    print("Estadísticas del adaptador de documentos:")
    print(f"Operaciones de procesamiento: {result.get('process_operations', 0)}")
    print(f"Operaciones de extracción: {result.get('extract_operations', 0)}")
    print(f"Operaciones de clasificación: {result.get('classify_operations', 0)}")
    print(f"Errores: {result.get('errors', 0)}")
    print(f"Latencia promedio: {result.get('avg_latency_ms', 0):.2f} ms")
    print(f"Modo simulado: {result.get('mock_mode', False)}")

if __name__ == "__main__":
    asyncio.run(main())
