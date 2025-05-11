"""
Módulo de telemetría mock para pruebas.

Este módulo proporciona una implementación simplificada de telemetría
para usar en pruebas sin depender de OpenTelemetry.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Union

# Configurar logger
logger = logging.getLogger(__name__)

class TelemetryManager:
    """
    Gestor de telemetría simplificado para pruebas.
    
    Proporciona una implementación mock de las funciones de telemetría
    para usar en pruebas sin depender de OpenTelemetry.
    """
    
    def __init__(self):
        """Inicializa el gestor de telemetría."""
        self.spans = {}
        self.metrics = {}
        
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> str:
        """
        Inicia un nuevo span.
        
        Args:
            name: Nombre del span
            attributes: Atributos del span
            
        Returns:
            str: ID del span
        """
        span_id = str(uuid.uuid4())
        self.spans[span_id] = {
            "name": name,
            "attributes": attributes or {},
            "events": [],
            "start_time": time.time(),
            "end_time": None,
            "status": "OK"
        }
        logger.debug(f"Started span {name} with ID {span_id}")
        return span_id
        
    def end_span(self, span_id: str) -> None:
        """
        Finaliza un span.
        
        Args:
            span_id: ID del span
        """
        if span_id in self.spans:
            self.spans[span_id]["end_time"] = time.time()
            logger.debug(f"Ended span {self.spans[span_id]['name']} with ID {span_id}")
            
    def set_span_attribute(self, span_id: str, key: str, value: Any) -> None:
        """
        Establece un atributo en un span.
        
        Args:
            span_id: ID del span
            key: Clave del atributo
            value: Valor del atributo
        """
        if span_id in self.spans:
            self.spans[span_id]["attributes"][key] = value
            
    def add_span_event(self, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Añade un evento a un span.
        
        Args:
            span_id: ID del span
            name: Nombre del evento
            attributes: Atributos del evento
        """
        if span_id in self.spans:
            self.spans[span_id]["events"].append({
                "name": name,
                "attributes": attributes or {},
                "timestamp": time.time()
            })
            
    def record_exception(self, span_id: str, exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra una excepción en un span.
        
        Args:
            span_id: ID del span
            exception: Excepción a registrar
            attributes: Atributos adicionales
        """
        if span_id in self.spans:
            self.spans[span_id]["status"] = "ERROR"
            self.spans[span_id]["attributes"]["error.type"] = type(exception).__name__
            self.spans[span_id]["attributes"]["error.message"] = str(exception)
            if attributes:
                for key, value in attributes.items():
                    self.spans[span_id]["attributes"][key] = value
                    
    def record_metric(self, name: str, value: Union[int, float], attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra una métrica.
        
        Args:
            name: Nombre de la métrica
            value: Valor de la métrica
            attributes: Atributos de la métrica
        """
        if name not in self.metrics:
            self.metrics[name] = []
            
        self.metrics[name].append({
            "value": value,
            "attributes": attributes or {},
            "timestamp": time.time()
        })
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de telemetría.
        
        Returns:
            Dict[str, Any]: Estadísticas de telemetría
        """
        return {
            "spans_count": len(self.spans),
            "active_spans": sum(1 for span in self.spans.values() if span["end_time"] is None),
            "error_spans": sum(1 for span in self.spans.values() if span["status"] == "ERROR"),
            "metrics_count": sum(len(metrics) for metrics in self.metrics.values())
        }
        
    def clear(self) -> None:
        """Limpia todos los datos de telemetría."""
        self.spans.clear()
        self.metrics.clear()

# Instancia global
telemetry_manager = TelemetryManager()