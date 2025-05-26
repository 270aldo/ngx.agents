"""
Configuración de modelos Gemini para NGX Agents.

Este módulo centraliza la configuración de los modelos de Gemini
utilizados por los diferentes componentes del sistema.
"""

import os
from typing import Dict, Any, Optional

# Modelos Gemini 2.0 disponibles
GEMINI_MODELS = {
    # Gemini 2.0 Pro - Para el Orchestrator y análisis complejos
    "orchestrator": {
        "model_id": "gemini-2.0-pro-exp",
        "display_name": "Gemini 2.0 Pro Experimental",
        "description": "Modelo más capaz para el orchestrator y análisis complejos",
        "max_tokens": 8192,
        "supports_vision": True,
        "supports_audio": True,
        "supports_video": True,
        "default_temperature": 0.7,
        "use_cases": [
            "orchestration",
            "complex_analysis",
            "multimodal_synthesis",
            "advanced_reasoning",
        ],
    },
    # Gemini 2.0 Flash - Para agentes especializados
    "agent": {
        "model_id": "gemini-2.0-flash-exp",
        "display_name": "Gemini 2.0 Flash Experimental",
        "description": "Modelo rápido y eficiente para agentes especializados",
        "max_tokens": 8192,
        "supports_vision": True,
        "supports_audio": True,
        "supports_video": False,
        "default_temperature": 0.5,
        "use_cases": [
            "specialized_agents",
            "quick_analysis",
            "real_time_processing",
            "high_volume_tasks",
        ],
    },
    # Gemini 1.5 Pro Vision - Fallback para visión si 2.0 no está disponible
    "vision_fallback": {
        "model_id": "gemini-1.5-pro-vision",
        "display_name": "Gemini 1.5 Pro Vision",
        "description": "Modelo de respaldo para capacidades de visión",
        "max_tokens": 4096,
        "supports_vision": True,
        "supports_audio": False,
        "supports_video": False,
        "default_temperature": 0.3,
        "use_cases": ["image_analysis", "ocr", "visual_understanding"],
    },
}

# Configuración por defecto para cada tipo de agente
AGENT_MODEL_MAPPING = {
    # Orchestrator usa el modelo más potente
    "orchestrator": GEMINI_MODELS["orchestrator"],
    # Agentes especializados usan Flash para eficiencia
    "elite_training_strategist": GEMINI_MODELS["agent"],
    "precision_nutrition_architect": GEMINI_MODELS["agent"],
    "biometrics_insight_engine": GEMINI_MODELS["agent"],
    "motivation_behavior_coach": GEMINI_MODELS["agent"],
    "progress_tracker": GEMINI_MODELS["agent"],
    "recovery_corrective": GEMINI_MODELS["agent"],
    "security_compliance_guardian": GEMINI_MODELS["agent"],
    "systems_integration_ops": GEMINI_MODELS["agent"],
    "biohacking_innovator": GEMINI_MODELS["agent"],
    "client_success_liaison": GEMINI_MODELS["agent"],
    # Configuración especial para tareas específicas
    "vision_analysis": GEMINI_MODELS["orchestrator"],  # Pro para análisis complejos
    "ocr_extraction": GEMINI_MODELS["agent"],  # Flash para OCR rápido
    "multimodal_synthesis": GEMINI_MODELS["orchestrator"],  # Pro para síntesis
}

# Configuración de temperatura por tipo de tarea
TEMPERATURE_SETTINGS = {
    "creative_generation": 0.8,
    "analysis": 0.3,
    "extraction": 0.1,
    "conversation": 0.7,
    "planning": 0.5,
    "validation": 0.2,
}

# Configuración de Google Cloud
GCP_CONFIG = {
    "project_id": os.getenv("GCP_PROJECT_ID", "ngx-agents"),
    "location": os.getenv("GCP_LOCATION", "us-central1"),
    "vertex_ai_endpoint": os.getenv(
        "VERTEX_AI_ENDPOINT", "us-central1-aiplatform.googleapis.com"
    ),
    "storage_bucket": os.getenv("GCS_BUCKET", "ngx-agents-storage"),
    "vision_api_enabled": os.getenv("VISION_API_ENABLED", "true").lower() == "true",
}

# Configuración de límites y seguridad
SAFETY_SETTINGS = {
    "harm_block_threshold": "BLOCK_MEDIUM_AND_ABOVE",
    "categories": [
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    ],
}

# Configuración de caché para visión
VISION_CACHE_CONFIG = {
    "enable_cache": True,
    "cache_ttl": 3600,  # 1 hora
    "max_cache_size_mb": 500,
    "cache_strategy": "LRU",  # Least Recently Used
}


def get_model_config(agent_type: str) -> Dict[str, Any]:
    """
    Obtiene la configuración del modelo para un tipo de agente específico.

    Args:
        agent_type: Tipo de agente o tarea

    Returns:
        Configuración del modelo
    """
    return AGENT_MODEL_MAPPING.get(agent_type, GEMINI_MODELS["agent"])


def get_model_id(agent_type: str) -> str:
    """
    Obtiene el ID del modelo para un tipo de agente.

    Args:
        agent_type: Tipo de agente o tarea

    Returns:
        ID del modelo
    """
    config = get_model_config(agent_type)
    return config["model_id"]


def get_temperature(task_type: str, default: Optional[float] = None) -> float:
    """
    Obtiene la temperatura recomendada para un tipo de tarea.

    Args:
        task_type: Tipo de tarea
        default: Temperatura por defecto si no se encuentra

    Returns:
        Temperatura recomendada
    """
    return TEMPERATURE_SETTINGS.get(task_type, default or 0.5)


def is_vision_enabled(model_config: Dict[str, Any]) -> bool:
    """
    Verifica si un modelo tiene capacidades de visión.

    Args:
        model_config: Configuración del modelo

    Returns:
        True si soporta visión
    """
    return model_config.get("supports_vision", False)


def is_audio_enabled(model_config: Dict[str, Any]) -> bool:
    """
    Verifica si un modelo tiene capacidades de audio.

    Args:
        model_config: Configuración del modelo

    Returns:
        True si soporta audio
    """
    return model_config.get("supports_audio", False)


def get_max_tokens(agent_type: str) -> int:
    """
    Obtiene el límite máximo de tokens para un tipo de agente.

    Args:
        agent_type: Tipo de agente

    Returns:
        Límite de tokens
    """
    config = get_model_config(agent_type)
    return config.get("max_tokens", 4096)


# Configuración de endpoints de Vertex AI
VERTEX_AI_ENDPOINTS = {
    "prediction": f"https://{GCP_CONFIG['location']}-aiplatform.googleapis.com/v1",
    "vision": f"https://vision.googleapis.com/v1",
    "storage": f"https://storage.googleapis.com",
    "speech": f"https://speech.googleapis.com/v1",
    "translate": f"https://translation.googleapis.com/v3",
}

# Configuración de retry para llamadas a API
RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,
    "exponential_base": 2,
    "max_delay": 60,
    "retriable_exceptions": [
        "ServiceUnavailable",
        "DeadlineExceeded",
        "ResourceExhausted",
    ],
}

# Configuración de procesamiento de imágenes
IMAGE_PROCESSING_CONFIG = {
    "max_image_size_mb": 20,
    "supported_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
    "auto_resize": True,
    "target_resolution": {
        "analysis": (1024, 1024),
        "thumbnail": (256, 256),
        "ocr": (2048, 2048),
    },
    "compression_quality": 85,
}

# Configuración de audio (para futuras implementaciones)
AUDIO_CONFIG = {
    "supported_formats": ["mp3", "wav", "m4a", "ogg"],
    "max_duration_seconds": 300,  # 5 minutos
    "sample_rate": 16000,
    "encoding": "LINEAR16",
}
