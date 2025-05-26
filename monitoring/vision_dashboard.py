"""
Dashboard para monitoreo de capacidades de visión y multimodales.

Este módulo proporciona un dashboard para visualizar métricas y estadísticas
de las capacidades de visión y multimodales, permitiendo monitorear el rendimiento
y configurar alertas.
"""

import asyncio
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.logging_config import get_logger
from core.vision_metrics import vision_metrics
from core.image_cache import image_cache
from core.image_optimizer import image_optimizer
from core.document_processor import document_processor
from core.object_recognition import object_recognition
from monitoring.alert_manager import alert_manager

# Configurar logger
logger = get_logger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="Dashboard de Visión y Multimodal",
    description="Dashboard para monitoreo de capacidades de visión y multimodales",
    version="1.0.0",
)

# Configurar directorio de plantillas y archivos estáticos
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")

# Crear directorios si no existen
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

# Configurar plantillas y archivos estáticos
templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Modelos de datos
class AlertConfig(BaseModel):
    threshold_name: str
    value: float
    enabled: bool = True


class AlertNotification(BaseModel):
    severity: str
    title: str
    message: str
    timestamp: str
    data: Dict[str, Any]


# Rutas del dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Página principal del dashboard."""
    # En una implementación real, se renderizaría una plantilla HTML
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard de Visión y Multimodal</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            .dashboard-container { display: flex; flex-wrap: wrap; }
            .dashboard-card { 
                background: #fff; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                margin: 10px; 
                padding: 15px; 
                width: 300px; 
            }
            .dashboard-card h2 { margin-top: 0; font-size: 18px; }
            .metric { font-size: 24px; font-weight: bold; margin: 10px 0; }
            .metric-label { font-size: 14px; color: #666; }
        </style>
    </head>
    <body>
        <h1>Dashboard de Visión y Multimodal</h1>
        
        <div class="dashboard-container">
            <div class="dashboard-card">
                <h2>Llamadas a API</h2>
                <div id="api-calls-metric" class="metric">Cargando...</div>
                <div class="metric-label">Total de llamadas</div>
            </div>
            
            <div class="dashboard-card">
                <h2>Tasa de Éxito</h2>
                <div id="success-rate-metric" class="metric">Cargando...</div>
                <div class="metric-label">Porcentaje de éxito</div>
            </div>
            
            <div class="dashboard-card">
                <h2>Latencia Promedio</h2>
                <div id="avg-latency-metric" class="metric">Cargando...</div>
                <div class="metric-label">Milisegundos</div>
            </div>
            
            <div class="dashboard-card">
                <h2>Caché</h2>
                <div id="cache-hit-rate-metric" class="metric">Cargando...</div>
                <div class="metric-label">Tasa de aciertos</div>
            </div>
        </div>
        
        <h2>Métricas Detalladas</h2>
        <p>Para ver métricas detalladas, use los endpoints de la API:</p>
        <ul>
            <li><a href="/api/metrics">/api/metrics</a> - Métricas actuales</li>
            <li><a href="/api/metrics/history">/api/metrics/history</a> - Historial de métricas</li>
            <li><a href="/api/components/stats">/api/components/stats</a> - Estadísticas de componentes</li>
        </ul>
        
        <script>
            // Función para actualizar métricas
            async function updateMetrics() {
                try {
                    const response = await fetch('/api/metrics');
                    const data = await response.json();
                    
                    // Actualizar métricas en la UI
                    document.getElementById('api-calls-metric').textContent = 
                        data.api_calls.total || 0;
                    
                    const successRate = data.api_calls.total > 0 
                        ? ((data.api_calls.success / data.api_calls.total) * 100).toFixed(1) + '%' 
                        : '0%';
                    document.getElementById('success-rate-metric').textContent = successRate;
                    
                    const avgLatency = data.latency.count > 0 
                        ? (data.latency.total_ms / data.latency.count).toFixed(1) + ' ms' 
                        : '0 ms';
                    document.getElementById('avg-latency-metric').textContent = avgLatency;
                    
                    const cacheHitRate = ((data.cache.hits / (data.cache.hits + data.cache.misses)) * 100).toFixed(1) + '%';
                    document.getElementById('cache-hit-rate-metric').textContent = 
                        isNaN(cacheHitRate.split('%')[0]) ? '0%' : cacheHitRate;
                    
                } catch (error) {
                    console.error('Error al actualizar métricas:', error);
                }
            }
            
            // Actualizar métricas al cargar y cada 30 segundos
            updateMetrics();
            setInterval(updateMetrics, 30000);
        </script>
    </body>
    </html>
    """


@app.get("/api/metrics")
async def get_current_metrics():
    """Obtiene las métricas actuales."""
    try:
        metrics = await vision_metrics.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error al obtener métricas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error al obtener métricas: {str(e)}"
        )


@app.get("/api/metrics/history")
async def get_metrics_history(period: str = Query("hourly", enum=["hourly", "daily"])):
    """Obtiene el historial de métricas."""
    try:
        history = await vision_metrics.get_history(period)
        return {"period": period, "history": history}
    except Exception as e:
        logger.error(f"Error al obtener historial de métricas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error al obtener historial de métricas: {str(e)}"
        )


@app.get("/api/components/stats")
async def get_components_stats():
    """Obtiene estadísticas de todos los componentes."""
    try:
        # Recopilar estadísticas de todos los componentes
        cache_stats = await image_cache.get_stats()
        optimizer_stats = await image_optimizer.get_stats()
        document_processor_stats = await document_processor.get_stats()
        object_recognition_stats = await object_recognition.get_stats()

        return {
            "image_cache": cache_stats,
            "image_optimizer": optimizer_stats,
            "document_processor": document_processor_stats,
            "object_recognition": object_recognition_stats,
        }
    except Exception as e:
        logger.error(
            f"Error al obtener estadísticas de componentes: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas de componentes: {str(e)}",
        )


@app.get("/api/alerts")
async def get_alerts(limit: int = Query(10, ge=1, le=100)):
    """Obtiene las alertas recientes."""
    try:
        alerts = await alert_manager.get_recent_alerts(limit)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Error al obtener alertas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error al obtener alertas: {str(e)}"
        )


@app.post("/api/alerts/config")
async def update_alert_config(config: AlertConfig):
    """Actualiza la configuración de alertas."""
    try:
        await alert_manager.update_threshold(
            config.threshold_name, config.value, config.enabled
        )
        return {
            "status": "success",
            "message": f"Configuración de alerta '{config.threshold_name}' actualizada",
        }
    except Exception as e:
        logger.error(f"Error al actualizar configuración de alerta: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar configuración de alerta: {str(e)}",
        )


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket para recibir actualizaciones de métricas en tiempo real."""
    await websocket.accept()
    try:
        while True:
            # Obtener métricas actuales
            metrics = await vision_metrics.get_metrics()

            # Enviar métricas al cliente
            await websocket.send_json(metrics)

            # Esperar antes de la siguiente actualización
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Error en WebSocket de métricas: {e}", exc_info=True)
    finally:
        await websocket.close()


def start_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Inicia el dashboard."""
    import uvicorn

    logger.info(f"Iniciando dashboard en http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_dashboard()
