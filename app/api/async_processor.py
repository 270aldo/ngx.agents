"""
API para el procesador asíncrono.

Este módulo proporciona endpoints para gestionar tareas asíncronas,
consultar su estado y obtener resultados.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from pydantic import BaseModel, Field

from core.async_processor import async_processor, TaskPriority, TaskStatus
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/async",
    tags=["async"],
    responses={404: {"description": "No encontrado"}},
)

# Modelos de datos para la API
class TaskSubmitRequest(BaseModel):
    """Solicitud para enviar una tarea asíncrona."""
    function_name: str = Field(..., description="Nombre de la función a ejecutar")
    args: List[Any] = Field(default=[], description="Argumentos posicionales")
    kwargs: Dict[str, Any] = Field(default={}, description="Argumentos con nombre")
    priority: str = Field(default="MEDIUM", description="Prioridad de la tarea (HIGH, MEDIUM, LOW, BACKGROUND)")
    timeout: Optional[float] = Field(default=None, description="Tiempo máximo de ejecución en segundos")
    max_retries: Optional[int] = Field(default=None, description="Número máximo de reintentos")
    retry_delay: Optional[float] = Field(default=None, description="Tiempo de espera entre reintentos en segundos")
    agent_id: Optional[str] = Field(default=None, description="ID del agente asociado")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales")

class TaskSubmitResponse(BaseModel):
    """Respuesta a una solicitud de envío de tarea."""
    task_id: str = Field(..., description="ID de la tarea")
    status: str = Field(..., description="Estado inicial de la tarea")

class TaskStatusResponse(BaseModel):
    """Respuesta con el estado de una tarea."""
    task_id: str = Field(..., description="ID de la tarea")
    status: str = Field(..., description="Estado de la tarea")
    created_at: Optional[str] = Field(default=None, description="Fecha de creación")
    started_at: Optional[str] = Field(default=None, description="Fecha de inicio")
    completed_at: Optional[str] = Field(default=None, description="Fecha de finalización")
    execution_time: Optional[float] = Field(default=None, description="Tiempo de ejecución en segundos")
    retry_count: int = Field(..., description="Número de reintentos realizados")
    agent_id: Optional[str] = Field(default=None, description="ID del agente asociado")
    priority: str = Field(..., description="Prioridad de la tarea")
    has_result: bool = Field(..., description="Si la tarea tiene resultado")
    has_error: bool = Field(..., description="Si la tarea tiene error")

class TaskResultResponse(BaseModel):
    """Respuesta con el resultado de una tarea."""
    task_id: str = Field(..., description="ID de la tarea")
    status: str = Field(..., description="Estado de la tarea")
    result: Optional[Any] = Field(default=None, description="Resultado de la tarea")
    error: Optional[str] = Field(default=None, description="Error de la tarea")
    execution_time: Optional[float] = Field(default=None, description="Tiempo de ejecución en segundos")

class ProcessorStatsResponse(BaseModel):
    """Respuesta con estadísticas del procesador."""
    total_tasks: int = Field(..., description="Número total de tareas")
    completed_tasks: int = Field(..., description="Número de tareas completadas")
    failed_tasks: int = Field(..., description="Número de tareas fallidas")
    cancelled_tasks: int = Field(..., description="Número de tareas canceladas")
    timeout_tasks: int = Field(..., description="Número de tareas con timeout")
    retried_tasks: int = Field(..., description="Número de tareas reintentadas")
    avg_execution_time: float = Field(..., description="Tiempo medio de ejecución")
    queue_sizes: Dict[str, int] = Field(..., description="Tamaño de las colas por prioridad")
    status_counts: Dict[str, int] = Field(..., description="Número de tareas por estado")
    priority_counts: Dict[str, int] = Field(..., description="Número de tareas por prioridad")
    agent_counts: Dict[str, int] = Field(..., description="Número de tareas por agente")
    active_workers: int = Field(..., description="Número de workers activos")
    max_workers: int = Field(..., description="Número máximo de workers")

# Registro de funciones disponibles para ejecución asíncrona
# Esto es un ejemplo, en una implementación real se registrarían dinámicamente
AVAILABLE_FUNCTIONS = {
    "analyze_sentiment": {
        "module": "clients.gemini_client",
        "function": "analyze_sentiment",
        "description": "Analiza el sentimiento de un texto"
    },
    "summarize_text": {
        "module": "clients.gemini_client",
        "function": "summarize",
        "description": "Genera un resumen de un texto"
    },
    "analyze_image": {
        "module": "clients.gemini_client",
        "function": "analyze_image",
        "description": "Analiza una imagen"
    },
    "analyze_pdf": {
        "module": "clients.gemini_client",
        "function": "analyze_pdf",
        "description": "Analiza un documento PDF"
    },
    "analyze_csv": {
        "module": "clients.gemini_client",
        "function": "analyze_csv",
        "description": "Analiza un archivo CSV"
    }
}

@router.post("/tasks", response_model=TaskSubmitResponse)
async def submit_task(
    request: TaskSubmitRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Envía una tarea para ejecución asíncrona.
    
    Args:
        request: Solicitud con los datos de la tarea
        user_id: ID del usuario autenticado
        
    Returns:
        ID de la tarea creada
    """
    # Verificar si la función está disponible
    if request.function_name not in AVAILABLE_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Función '{request.function_name}' no disponible")
    
    try:
        # Obtener información de la función
        func_info = AVAILABLE_FUNCTIONS[request.function_name]
        
        # Importar dinámicamente la función
        module_name = func_info["module"]
        function_name = func_info["function"]
        
        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)
        
        # Convertir prioridad de string a enum
        priority = TaskPriority[request.priority]
        
        # Enviar tarea
        task_id = await async_processor.submit(
            func,
            *request.args,
            priority=priority,
            timeout=request.timeout,
            max_retries=request.max_retries,
            retry_delay=request.retry_delay,
            agent_id=request.agent_id,
            user_id=user_id,
            metadata=request.metadata,
            **request.kwargs
        )
        
        # Obtener estado inicial
        task_info = await async_processor.get_task(task_id)
        
        return TaskSubmitResponse(
            task_id=task_id,
            status=task_info["status"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar tarea: {str(e)}")

@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Path(..., description="ID de la tarea"),
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene el estado de una tarea.
    
    Args:
        task_id: ID de la tarea
        user_id: ID del usuario autenticado
        
    Returns:
        Estado de la tarea
    """
    task_info = await async_processor.get_task(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail=f"Tarea {task_id} no encontrada")
    
    return TaskStatusResponse(**task_info)

@router.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str = Path(..., description="ID de la tarea"),
    wait: bool = Query(False, description="Esperar a que la tarea termine"),
    timeout: Optional[float] = Query(None, description="Tiempo máximo de espera en segundos"),
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene el resultado de una tarea.
    
    Args:
        task_id: ID de la tarea
        wait: Si se debe esperar a que la tarea termine
        timeout: Tiempo máximo de espera en segundos
        user_id: ID del usuario autenticado
        
    Returns:
        Resultado de la tarea
    """
    try:
        result = await async_processor.get_result(task_id, wait=wait, timeout=timeout)
        return TaskResultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except asyncio.TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resultado: {str(e)}")

@router.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def cancel_task(
    task_id: str = Path(..., description="ID de la tarea"),
    user_id: str = Depends(get_current_user)
):
    """
    Cancela una tarea pendiente.
    
    Args:
        task_id: ID de la tarea
        user_id: ID del usuario autenticado
        
    Returns:
        Resultado de la operación
    """
    success = await async_processor.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"No se pudo cancelar la tarea {task_id}")
    
    return {
        "success": True,
        "task_id": task_id,
        "message": f"Tarea {task_id} cancelada"
    }

@router.get("/stats", response_model=ProcessorStatsResponse)
async def get_processor_stats(
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene estadísticas del procesador asíncrono.
    
    Args:
        user_id: ID del usuario autenticado
        
    Returns:
        Estadísticas del procesador
    """
    stats = await async_processor.get_stats()
    return ProcessorStatsResponse(**stats)

@router.post("/clear", response_model=Dict[str, Any])
async def clear_completed_tasks(
    older_than: Optional[int] = Query(None, description="Eliminar tareas completadas hace más de X segundos"),
    user_id: str = Depends(get_current_user)
):
    """
    Elimina tareas completadas del procesador.
    
    Args:
        older_than: Eliminar tareas completadas hace más de X segundos
        user_id: ID del usuario autenticado
        
    Returns:
        Resultado de la operación
    """
    removed_count = await async_processor.clear_completed_tasks(older_than)
    
    return {
        "success": True,
        "removed_count": removed_count,
        "message": f"Eliminadas {removed_count} tareas completadas"
    }

@router.get("/functions", response_model=Dict[str, Dict[str, str]])
async def get_available_functions(
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene la lista de funciones disponibles para ejecución asíncrona.
    
    Args:
        user_id: ID del usuario autenticado
        
    Returns:
        Lista de funciones disponibles
    """
    return AVAILABLE_FUNCTIONS