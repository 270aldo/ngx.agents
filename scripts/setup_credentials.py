#!/usr/bin/env python3
"""
Script para configurar las credenciales y variables de entorno necesarias para NGX Agents.

Este script ayuda a configurar un archivo .env con las credenciales y configuraciones
necesarias para comenzar a hacer pruebas con los diferentes servicios utilizados en
el proyecto NGX Agents.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Plantilla de configuración con valores predeterminados
DEFAULT_CONFIG = {
    # Google Cloud / Vertex AI
    "GOOGLE_APPLICATION_CREDENTIALS": "",
    "GOOGLE_CLOUD_PROJECT": "",

    # Vertex AI - General
    "VERTEX_AI_LOCATION": "us-central1",
    "VERTEX_AI_MODEL": "text-bison@001",
    "VERTEX_AI_EMBEDDING_MODEL": "textembedding-gecko@001",
    "VERTEX_AI_VISION_MODEL": "imagetext@001",
    "VERTEX_AI_MULTIMODAL_MODEL": "gemini-pro-vision",
    "VERTEX_AI_MAX_OUTPUT_TOKENS": "1024",
    "VERTEX_AI_TEMPERATURE": "0.2",
    "VERTEX_AI_TOP_P": "0.95",
    "VERTEX_AI_TOP_K": "40",

    # Document AI
    "DOCUMENT_AI_LOCATION": "us",
    "DOCUMENT_AI_PROCESSOR_ID": "",
    "DOCUMENT_AI_OCR_PROCESSOR_ID": "",
    "DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID": "",
    "DOCUMENT_AI_ENTITY_PROCESSOR_ID": "",
    "DOCUMENT_AI_FORM_PROCESSOR_ID": "",
    "DOCUMENT_AI_INVOICE_PROCESSOR_ID": "",
    "DOCUMENT_AI_RECEIPT_PROCESSOR_ID": "",
    "DOCUMENT_AI_ID_PROCESSOR_ID": "",
    "DOCUMENT_AI_MEDICAL_PROCESSOR_ID": "",
    "DOCUMENT_AI_TAX_PROCESSOR_ID": "",
    "DOCUMENT_AI_TIMEOUT": "60",

    # Speech-to-Text
    "SPEECH_TO_TEXT_LOCATION": "global",
    "SPEECH_TO_TEXT_MODEL": "latest_long",
    "SPEECH_TO_TEXT_LANGUAGE_CODE": "es-MX",

    # Text-to-Speech
    "TEXT_TO_SPEECH_LOCATION": "global",
    "TEXT_TO_SPEECH_VOICE_NAME": "es-ES-Standard-A",
    "TEXT_TO_SPEECH_LANGUAGE_CODE": "es-ES",

    # Pinecone
    "PINECONE_API_KEY": "",
    "PINECONE_ENVIRONMENT": "us-west1-gcp",
    "PINECONE_INDEX_NAME": "",
    "PINECONE_NAMESPACE": "",
    "PINECONE_DIMENSION": "768",
    "PINECONE_METRIC": "cosine",

    # Supabase
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "SUPABASE_JWT_SECRET": "",
    "SUPABASE_STORAGE_BUCKET": "",
    "SUPABASE_REALTIME_ENABLED": "true",

    # Google Cloud Storage
    "GCS_BUCKET_NAME": "",
    "GCS_LOCATION": "us-central1",

    # Redis
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_PASSWORD": "",
    "REDIS_DB": "0",
    "REDIS_SSL": "false",
    "REDIS_TIMEOUT": "5",

    # Telemetría
    "TELEMETRY_ENABLED": "true",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    "OTEL_SERVICE_NAME": "ngx-agents",

    # Configuraciones Generales
    "ENVIRONMENT": "development",
    "LOG_LEVEL": "INFO",
    "MOCK_EXTERNAL_SERVICES": "false",

    # Circuit Breaker
    "CIRCUIT_BREAKER_FAILURE_THRESHOLD": "5",
    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "30",
}

# Categorías de configuración para una mejor organización
CONFIG_CATEGORIES = {
    "Google Cloud / Vertex AI": [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
    ],
    "Vertex AI - General": [
        "VERTEX_AI_LOCATION",
        "VERTEX_AI_MODEL",
        "VERTEX_AI_EMBEDDING_MODEL",
        "VERTEX_AI_VISION_MODEL",
        "VERTEX_AI_MULTIMODAL_MODEL",
        "VERTEX_AI_MAX_OUTPUT_TOKENS",
        "VERTEX_AI_TEMPERATURE",
        "VERTEX_AI_TOP_P",
        "VERTEX_AI_TOP_K",
    ],
    "Document AI": [
        "DOCUMENT_AI_LOCATION",
        "DOCUMENT_AI_PROCESSOR_ID",
        "DOCUMENT_AI_OCR_PROCESSOR_ID",
        "DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID",
        "DOCUMENT_AI_ENTITY_PROCESSOR_ID",
        "DOCUMENT_AI_FORM_PROCESSOR_ID",
        "DOCUMENT_AI_INVOICE_PROCESSOR_ID",
        "DOCUMENT_AI_RECEIPT_PROCESSOR_ID",
        "DOCUMENT_AI_ID_PROCESSOR_ID",
        "DOCUMENT_AI_MEDICAL_PROCESSOR_ID",
        "DOCUMENT_AI_TAX_PROCESSOR_ID",
        "DOCUMENT_AI_TIMEOUT",
    ],
    "Speech-to-Text": [
        "SPEECH_TO_TEXT_LOCATION",
        "SPEECH_TO_TEXT_MODEL",
        "SPEECH_TO_TEXT_LANGUAGE_CODE",
    ],
    "Text-to-Speech": [
        "TEXT_TO_SPEECH_LOCATION",
        "TEXT_TO_SPEECH_VOICE_NAME",
        "TEXT_TO_SPEECH_LANGUAGE_CODE",
    ],
    "Pinecone": [
        "PINECONE_API_KEY",
        "PINECONE_ENVIRONMENT",
        "PINECONE_INDEX_NAME",
        "PINECONE_NAMESPACE",
        "PINECONE_DIMENSION",
        "PINECONE_METRIC",
    ],
    "Supabase": [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_STORAGE_BUCKET",
        "SUPABASE_REALTIME_ENABLED",
    ],
    "Google Cloud Storage": [
        "GCS_BUCKET_NAME",
        "GCS_LOCATION",
    ],
    "Redis": [
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
        "REDIS_DB",
        "REDIS_SSL",
        "REDIS_TIMEOUT",
    ],
    "Telemetría": [
        "TELEMETRY_ENABLED",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAME",
    ],
    "Configuraciones Generales": [
        "ENVIRONMENT",
        "LOG_LEVEL",
        "MOCK_EXTERNAL_SERVICES",
    ],
    "Circuit Breaker": [
        "CIRCUIT_BREAKER_FAILURE_THRESHOLD",
        "CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
    ],
}

# Variables requeridas para cada servicio
REQUIRED_VARS = {
    "vertex_ai": [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "VERTEX_AI_LOCATION",
        "VERTEX_AI_MODEL",
    ],
    "document_ai": [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "DOCUMENT_AI_LOCATION",
        "DOCUMENT_AI_PROCESSOR_ID",
    ],
    "speech_to_text": [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "SPEECH_TO_TEXT_LOCATION",
        "SPEECH_TO_TEXT_MODEL",
        "SPEECH_TO_TEXT_LANGUAGE_CODE",
    ],
    "text_to_speech": [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "TEXT_TO_SPEECH_LOCATION",
        "TEXT_TO_SPEECH_VOICE_NAME",
        "TEXT_TO_SPEECH_LANGUAGE_CODE",
    ],
    "pinecone": [
        "PINECONE_API_KEY",
        "PINECONE_ENVIRONMENT",
        "PINECONE_INDEX_NAME",
        "PINECONE_DIMENSION",
    ],
    "supabase": [
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ],
    "gcs": [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "GCS_BUCKET_NAME",
    ],
    "redis": [
        "REDIS_HOST",
        "REDIS_PORT",
    ],
}

def load_existing_env(env_file: Path) -> Dict[str, str]:
    """Carga un archivo .env existente.

    Args:
        env_file: Ruta al archivo .env.

    Returns:
        Diccionario con las variables de entorno.
    """
    if not env_file.exists():
        return {}

    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars

def load_json_credentials(json_file: Path) -> Dict[str, Any]:
    """Carga credenciales desde un archivo JSON.

    Args:
        json_file: Ruta al archivo JSON.

    Returns:
        Diccionario con las credenciales.
    """
    if not json_file.exists():
        print(f"Error: El archivo {json_file} no existe.")
        return {}

    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: El archivo {json_file} no es un JSON válido.")
        return {}

def save_env_file(env_file: Path, env_vars: Dict[str, str]) -> None:
    """Guarda las variables de entorno en un archivo .env.

    Args:
        env_file: Ruta al archivo .env.
        env_vars: Diccionario con las variables de entorno.
    """
    # Crear directorio si no existe
    env_file.parent.mkdir(parents=True, exist_ok=True)

    # Organizar las variables por categoría
    content = []
    for category, vars_list in CONFIG_CATEGORIES.items():
        content.append(f"\n# {category}")
        for var in vars_list:
            if var in env_vars:
                content.append(f"{var}={env_vars[var]}")

    # Guardar el archivo
    with open(env_file, "w") as f:
        f.write("\n".join(content))

def check_required_vars(env_vars: Dict[str, str], service: str) -> bool:
    """Verifica si todas las variables requeridas para un servicio están configuradas.

    Args:
        env_vars: Diccionario con las variables de entorno.
        service: Nombre del servicio.

    Returns:
        True si todas las variables requeridas están configuradas, False en caso contrario.
    """
    if service not in REQUIRED_VARS:
        print(f"Error: Servicio {service} no reconocido.")
        return False

    missing_vars = []
    for var in REQUIRED_VARS[service]:
        if not env_vars.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"Faltan las siguientes variables requeridas para {service}:")
        for var in missing_vars:
            print(f"  - {var}")
        return False

    return True

def interactive_setup(env_file: Path) -> None:
    """Configura las variables de entorno de forma interactiva.

    Args:
        env_file: Ruta al archivo .env.
    """
    # Cargar configuración existente si existe
    env_vars = load_existing_env(env_file)
    
    # Completar con valores predeterminados para variables no configuradas
    for key, value in DEFAULT_CONFIG.items():
        if key not in env_vars:
            env_vars[key] = value

    print(f"\nConfiguración interactiva para {env_file}")
    print("Presiona Enter para mantener el valor actual o ingresa un nuevo valor.")
    print("Ingresa 'skip' para omitir una sección completa.\n")

    # Recorrer categorías
    for category, vars_list in CONFIG_CATEGORIES.items():
        print(f"\n=== {category} ===")
        
        # Preguntar si se quiere omitir la sección
        skip_input = input(f"¿Omitir configuración de {category}? (s/N): ").strip().lower()
        if skip_input in ["s", "si", "sí", "y", "yes"]:
            continue
        
        # Configurar variables de la categoría
        for var in vars_list:
            current_value = env_vars.get(var, "")
            # Ocultar valores sensibles
            display_value = "********" if any(sensitive in var for sensitive in ["KEY", "SECRET", "PASSWORD", "CREDENTIALS"]) and current_value else current_value
            
            prompt = f"{var} [{display_value}]: "
            new_value = input(prompt).strip()
            
            # Actualizar solo si se ingresó un nuevo valor
            if new_value and new_value != "skip":
                env_vars[var] = new_value

    # Guardar configuración
    save_env_file(env_file, env_vars)
    print(f"\nConfiguración guardada en {env_file}")

def setup_from_json(env_file: Path, json_file: Path) -> None:
    """Configura las variables de entorno a partir de un archivo JSON.

    Args:
        env_file: Ruta al archivo .env.
        json_file: Ruta al archivo JSON.
    """
    # Cargar configuración existente si existe
    env_vars = load_existing_env(env_file)
    
    # Completar con valores predeterminados para variables no configuradas
    for key, value in DEFAULT_CONFIG.items():
        if key not in env_vars:
            env_vars[key] = value
    
    # Cargar credenciales desde JSON
    credentials = load_json_credentials(json_file)
    if not credentials:
        print("No se pudieron cargar las credenciales desde el archivo JSON.")
        return
    
    # Actualizar variables con credenciales del JSON
    for key, value in credentials.items():
        if key in env_vars:
            env_vars[key] = value
    
    # Guardar configuración
    save_env_file(env_file, env_vars)
    print(f"\nConfiguración actualizada con credenciales de {json_file}")
    print(f"Configuración guardada en {env_file}")

def check_services(env_file: Path, services: list) -> None:
    """Verifica si las variables requeridas para los servicios están configuradas.

    Args:
        env_file: Ruta al archivo .env.
        services: Lista de servicios a verificar.
    """
    # Cargar configuración existente
    env_vars = load_existing_env(env_file)
    
    print(f"\nVerificando configuración en {env_file}")
    
    all_valid = True
    for service in services:
        print(f"\n=== Verificando {service} ===")
        if check_required_vars(env_vars, service):
            print(f"✅ Configuración válida para {service}")
        else:
            print(f"❌ Configuración incompleta para {service}")
            all_valid = False
    
    if all_valid:
        print("\n✅ Todos los servicios están correctamente configurados")
    else:
        print("\n❌ Algunos servicios tienen configuración incompleta")

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Configuración de credenciales para NGX Agents")
    parser.add_argument("--env", type=str, default=".env", help="Archivo .env a configurar")
    parser.add_argument("--json", type=str, help="Archivo JSON con credenciales")
    parser.add_argument("--check", action="store_true", help="Verificar configuración")
    parser.add_argument("--services", type=str, nargs="+", 
                        choices=["vertex_ai", "document_ai", "speech_to_text", "text_to_speech", 
                                "pinecone", "supabase", "gcs", "redis", "all"],
                        default=["all"], help="Servicios a verificar")
    
    args = parser.parse_args()
    
    # Convertir rutas a objetos Path
    env_file = Path(args.env)
    json_file = Path(args.json) if args.json else None
    
    # Determinar servicios a verificar
    services = args.services
    if "all" in services:
        services = list(REQUIRED_VARS.keys())
    
    # Ejecutar acción correspondiente
    if args.check:
        check_services(env_file, services)
    elif json_file:
        setup_from_json(env_file, json_file)
    else:
        interactive_setup(env_file)

if __name__ == "__main__":
    main()
