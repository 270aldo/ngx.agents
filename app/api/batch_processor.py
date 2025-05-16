"""
API para el procesador por lotes.

Este módulo proporciona endpoints para gestionar el procesamiento por lotes,
consultar su estado y obtener resultados.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from pydantic import BaseModel, Field

from core.batch_processor import batch_processor, BatchStrategy, BatchStatus
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/batch",
    tags=["batch"],
    responses={404: {"description": "No encontrado"}},
)

# Modelos de datos para la API
class BatchProcessRequest(BaseModel):
    """Solicitud para procesar un lote."""
    items: List[Any] = Field(..., description="Lista de elementos a procesar")
    processor_name: str = Field(..., description="Nombre del procesador a utilizar")
    strategy: str = Field(default="adaptive", description="Estrategia de división en lotes (chunk_size, chunk_count, adaptive)")
    chunk_size: Optional[int] = Field(default=None, description="Tamaño de cada lote (para chunk_size)")
    chunk_count: Optional[int] = Field(default=None, description="Número de lotes (para chunk_count)")
    timeout: Optional[float] = Field(default=None, description="Tiempo máximo de ejecución en segundos")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales")

class BatchProcessResponse(BaseModel):
    """Respuesta a una solicitud de procesamiento por lotes."""
    batch_id: str = Field(..., description="ID del lote")
    total_items: int = Field(..., description="Número total de elementos")
    status: str = Field(..., description="Estado inicial del lote")

class BatchStatusResponse(BaseModel):
    """Respuesta con el estado de un lote."""
    batch_id: str = Field(..., description="ID del lote")
    status: str = Field(..., description="Estado del lote")
    start_time: Optional[str] = Field(default=None, description="Fecha de inicio")
    end_time: Optional[str] = Field(default=None, description="Fecha de finalización")
    total_items: int = Field(..., description="Número total de elementos")
    processed_items: int = Field(..., description="Número de elementos procesados")
    successful_items: int = Field(..., description="Número de elementos procesados correctamente")
    failed_items: int = Field(..., description="Número de elementos con error")
    progress: float = Field(..., description="Progreso del procesamiento (0-100)")
    execution_time: Optional[float] = Field(default=None, description="Tiempo de ejecución en segundos")
    metadata: Dict[str, Any] = Field(default={}, description="Metadatos adicionales")

class BatchResultsResponse(BaseModel):
    """Respuesta con los resultados de un lote."""
    batch_id: str = Field(..., description="ID del lote")
    status: str = Field(..., description="Estado del lote")
    results: List[Any] = Field(..., description="Resultados del procesamiento")
    errors: Optional[Dict[str, str]] = Field(default=None, description="Errores del procesamiento")
    total_items: int = Field(..., description="Número total de elementos")
    successful_items: int = Field(..., description="Número de elementos procesados correctamente")
    failed_items: int = Field(..., description="Número de elementos con error")
    execution_time: Optional[float] = Field(default=None, description="Tiempo de ejecución en segundos")

class ProcessorStatsResponse(BaseModel):
    """Respuesta con estadísticas del procesador."""
    total_batches: int = Field(..., description="Número total de lotes")
    completed_batches: int = Field(..., description="Número de lotes completados")
    failed_batches: int = Field(..., description="Número de lotes fallidos")
    cancelled_batches: int = Field(..., description="Número de lotes cancelados")
    partial_batches: int = Field(..., description="Número de lotes completados parcialmente")
    total_items_processed: int = Field(..., description="Número total de elementos procesados")
    successful_items: int = Field(..., description="Número total de elementos procesados correctamente")
    failed_items: int = Field(..., description="Número total de elementos con error")
    avg_execution_time: float = Field(..., description="Tiempo medio de ejecución")
    status_counts: Dict[str, int] = Field(..., description="Número de lotes por estado")
    active_workers: int = Field(..., description="Número de workers activos")
    max_workers: int = Field(..., description="Número máximo de workers")

# Registro de procesadores disponibles
# Esto es un ejemplo, en una implementación real se registrarían dinámicamente
AVAILABLE_PROCESSORS = {
    "text_sentiment": {
        "module": "clients.gemini_client",
        "function": "analyze_sentiment",
        "description": "Analiza el sentimiento de textos",
        "item_type": "string"
    },
    "text_summarize": {
        "module": "clients.gemini_client",
        "function": "summarize",
        "description": "Genera resúmenes de textos",
        "item_type": "string"
    },
    "image_analyze": {
        "module": "clients.gemini_client",
        "function": "analyze_image",
        "description": "Analiza imágenes",
        "item_type": "string"  # Ruta de la imagen
    },
    "pdf_analyze": {
        "module": "clients.gemini_client",
        "function": "analyze_pdf",
        "description": "Analiza documentos PDF",
        "item_type": "string"  # Ruta del PDF
    },
    "csv_analyze": {
        "module": "clients.gemini_client",
        "function": "analyze_csv",
        "description": "Analiza archivos CSV",
        "item_type": "string"  # Ruta del CSV
    }
}

@router.post("/process", response_model=BatchProcessResponse)
async def process_batch(
    request: BatchProcessRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Inicia el procesamiento de un lote.
    
    Args:
        request: Solicitud con los datos del lote
        user_id: ID del usuario autenticado
        
    Returns:
        ID del lote creado
    """
    # Verificar si el procesador está disponible
    if request.processor_name not in AVAILABLE_PROCESSORS:
        raise HTTPException(status_code=400, detail=f"Procesador '{request.processor_name}' no disponible")
    
    try:
        # Obtener información del procesador
        processor_info = AVAILABLE_PROCESSORS[request.processor_name]
        
        # Importar dinámicamente la función
        module_name = processor_info["module"]
        function_name = processor_info["function"]
        
        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)
        
        # Convertir estrategia de string a enum
        strategy = BatchStrategy[request.strategy.upper()]
        
        # Añadir metadatos
        metadata = request.metadata or {}
        metadata["processor_name"] = request.processor_name
        metadata["user_id"] = user_id
        
        # Iniciar procesamiento
        batch_id = await batch_processor.process_batch(
            items=request.items,
            processor_func=func,
            strategy=strategy,
            chunk_size=request.chunk_size,
            chunk_count=request.chunk_count,
            timeout=request.timeout,
            metadata=metadata
        )
        
        # Obtener estado inicial
        status = await batch_processor.get_batch_status(batch_id)
        
        return BatchProcessResponse(
            batch_id=batch_id,
            total_items=status["total_items"],
            status=status["status"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al iniciar procesamiento: {str(e)}")

@router.get("/status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str = Path(..., description="ID del lote"),
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene el estado de un lote.
    
    Args:
        batch_id: ID del lote
        user_id: ID del usuario autenticado
        
    Returns:
        Estado del lote
    """
    status = await batch_processor.get_batch_status(batch_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Lote {batch_id} no encontrado")
    
    return BatchStatusResponse(**status)

@router.get("/results/{batch_id}", response_model=BatchResultsResponse)
async def get_batch_results(
    batch_id: str = Path(..., description="ID del lote"),
    include_errors: bool = Query(False, description="Incluir errores en la respuesta"),
    max_results: Optional[int] = Query(None, description="Número máximo de resultados a devolver"),
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene los resultados de un lote.
    
    Args:
        batch_id: ID del lote
        include_errors: Incluir errores en la respuesta
        max_results: Número máximo de resultados a devolver
        user_id: ID del usuario autenticado
        
    Returns:
        Resultados del lote
    """
    try:
        results = await batch_processor.get_batch_results(
            batch_id=batch_id,
            include_errors=include_errors,
            max_results=max_results
        )
        return BatchResultsResponse(**results)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resultados: {str(e)}")

@router.delete("/cancel/{batch_id}", response_model=Dict[str, Any])
async def cancel_batch(
    batch_id: str = Path(..., description="ID del lote"),
    user_id: str = Depends(get_current_user)
):
    """
    Cancela un lote en ejecución.
    
    Args:
        batch_id: ID del lote
        user_id: ID del usuario autenticado
        
    Returns:
        Resultado de la operación
    """
    success = await batch_processor.cancel_batch(batch_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"No se pudo cancelar el lote {batch_id}")
    
    return {
        "success": True,
        "batch_id": batch_id,
        "message": f"Lote {batch_id} cancelado"
    }

@router.get("/stats", response_model=ProcessorStatsResponse)
async def get_processor_stats(
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene estadísticas del procesador por lotes.
    
    Args:
        user_id: ID del usuario autenticado
        
    Returns:
        Estadísticas del procesador
    """
    stats = await batch_processor.get_stats()
    return ProcessorStatsResponse(**stats)

@router.post("/clear", response_model=Dict[str, Any])
async def clear_completed_batches(
    older_than: Optional[int] = Query(None, description="Eliminar lotes completados hace más de X segundos"),
    user_id: str = Depends(get_current_user)
):
    """
    Elimina lotes completados del procesador.
    
    Args:
        older_than: Eliminar lotes completados hace más de X segundos
        user_id: ID del usuario autenticado
        
    Returns:
        Resultado de la operación
    """
    removed_count = await batch_processor.clear_completed_batches(older_than)
    
    return {
        "success": True,
        "removed_count": removed_count,
        "message": f"Eliminados {removed_count} lotes completados"
    }

@router.get("/processors", response_model=Dict[str, Dict[str, str]])
async def get_available_processors(
    user_id: str = Depends(get_current_user)
):
    """
    Obtiene la lista de procesadores disponibles.
    
    Args:
        user_id: ID del usuario autenticado
        
    Returns:
        Lista de procesadores disponibles
    """
    return AVAILABLE_PROCESSORS