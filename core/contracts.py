"""
Definiciones de contratos para la comunicación entre agentes.

Este módulo define los esquemas JSON para las tareas y resultados
que se intercambian entre agentes, asegurando una comunicación estandarizada.
"""

from typing import Dict, Any, Optional

# Esquema JSON para las tareas
TaskSchema = {
    "type": "object",
    "required": ["task_id", "agent_id", "action", "data"],
    "properties": {
        "task_id": {"type": "string", "description": "Identificador único de la tarea"},
        "agent_id": {
            "type": "string",
            "description": "Identificador del agente que envía la tarea",
        },
        "target_agent_id": {
            "type": "string",
            "description": "Identificador del agente destinatario (opcional)",
        },
        "action": {
            "type": "string",
            "description": "Acción a realizar (ej: generate_training_plan, analyze_performance)",
        },
        "data": {
            "type": "object",
            "description": "Datos específicos para la acción",
            "properties": {
                "input_text": {
                    "type": "string",
                    "description": "Texto de entrada para la acción",
                },
                "context": {
                    "type": "object",
                    "description": "Contexto adicional para la acción",
                },
                "parameters": {
                    "type": "object",
                    "description": "Parámetros adicionales para la acción",
                },
            },
        },
        "metadata": {
            "type": "object",
            "description": "Metadatos adicionales (opcional)",
        },
        "timestamp": {
            "type": "number",
            "description": "Marca de tiempo de la tarea (timestamp Unix)",
        },
    },
}

# Esquema JSON para los resultados
ResultSchema = {
    "type": "object",
    "required": ["task_id", "agent_id", "status", "data"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Identificador de la tarea a la que responde",
        },
        "agent_id": {
            "type": "string",
            "description": "Identificador del agente que envía el resultado",
        },
        "status": {
            "type": "string",
            "enum": ["success", "error", "in_progress"],
            "description": "Estado del resultado",
        },
        "data": {
            "type": "object",
            "description": "Datos del resultado",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "Respuesta textual del agente",
                },
                "result": {
                    "type": "object",
                    "description": "Resultado estructurado (opcional)",
                },
            },
        },
        "error": {
            "type": "object",
            "description": "Información de error (si status='error')",
            "properties": {
                "code": {"type": "string", "description": "Código de error"},
                "message": {"type": "string", "description": "Mensaje de error"},
            },
        },
        "metadata": {
            "type": "object",
            "description": "Metadatos adicionales (opcional)",
        },
        "timestamp": {
            "type": "number",
            "description": "Marca de tiempo del resultado (timestamp Unix)",
        },
    },
}


def validate_task(task: Dict[str, Any]) -> bool:
    """
    Valida una tarea contra el esquema TaskSchema.

    Args:
        task: Tarea a validar

    Returns:
        bool: True si la tarea es válida, False en caso contrario
    """
    # Aquí implementaríamos la validación real contra el esquema
    # Por ahora, verificamos solo los campos requeridos
    required_fields = ["task_id", "agent_id", "action", "data"]
    return all(field in task for field in required_fields)


def validate_result(result: Dict[str, Any]) -> bool:
    """
    Valida un resultado contra el esquema ResultSchema.

    Args:
        result: Resultado a validar

    Returns:
        bool: True si el resultado es válido, False en caso contrario
    """
    # Aquí implementaríamos la validación real contra el esquema
    # Por ahora, verificamos solo los campos requeridos
    required_fields = ["task_id", "agent_id", "status", "data"]
    return all(field in result for field in required_fields)


def create_task(
    agent_id: str,
    action: str,
    data: Dict[str, Any],
    task_id: Optional[str] = None,
    target_agent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Crea una tarea válida según el esquema TaskSchema.

    Args:
        agent_id: ID del agente que crea la tarea
        action: Acción a realizar
        data: Datos para la acción
        task_id: ID de la tarea (opcional, se genera automáticamente si no se proporciona)
        target_agent_id: ID del agente destinatario (opcional)
        metadata: Metadatos adicionales (opcional)

    Returns:
        Dict[str, Any]: Tarea válida
    """
    import time
    import uuid

    task = {
        "task_id": task_id or str(uuid.uuid4()),
        "agent_id": agent_id,
        "action": action,
        "data": data,
        "timestamp": time.time(),
    }

    if target_agent_id:
        task["target_agent_id"] = target_agent_id

    if metadata:
        task["metadata"] = metadata

    return task


def create_result(
    task_id: str,
    agent_id: str,
    status: str,
    data: Dict[str, Any],
    error: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Crea un resultado válido según el esquema ResultSchema.

    Args:
        task_id: ID de la tarea a la que responde
        agent_id: ID del agente que crea el resultado
        status: Estado del resultado ('success', 'error', 'in_progress')
        data: Datos del resultado
        error: Información de error (opcional, requerido si status='error')
        metadata: Metadatos adicionales (opcional)

    Returns:
        Dict[str, Any]: Resultado válido
    """
    import time

    result = {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": status,
        "data": data,
        "timestamp": time.time(),
    }

    if error and status == "error":
        result["error"] = error

    if metadata:
        result["metadata"] = metadata

    return result
