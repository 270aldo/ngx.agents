#!/usr/bin/env python
"""
Script para probar el adaptador del BiometricsInsightEngine con el servidor A2A optimizado.

Este script inicializa el servidor A2A optimizado y el adaptador del BiometricsInsightEngine,
y luego realiza una prueba de comunicación entre ellos.
"""

import asyncio
import logging
import sys
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_biometrics_insight_engine_adapter")

# Importar componentes necesarios
from infrastructure.a2a_optimized import a2a_server
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.biometrics_insight_engine_adapter import biometrics_insight_engine_adapter, initialize_biometrics_insight_engine_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter

async def test_direct_call():
    """Prueba una llamada directa al adaptador del BiometricsInsightEngine."""
    logger.info("Probando llamada directa al adaptador del BiometricsInsightEngine...")
    
    # Datos de prueba
    query = "Analiza mis datos de sueño y frecuencia cardíaca de la última semana"
    user_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Llamar al adaptador directamente
    response = await biometrics_insight_engine_adapter.run_async_impl(
        query=query,
        user_id=user_id,
        session_id=session_id
    )
    
    # Mostrar respuesta
    logger.info(f"Respuesta directa recibida: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    return response

async def test_a2a_call():
    """Prueba una llamada a través del sistema A2A."""
    logger.info("Probando llamada a través del sistema A2A...")
    
    # Datos de prueba
    query = "Identifica patrones en mis datos de glucosa y actividad física"
    user_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Llamar al adaptador a través del sistema A2A
    response = await a2a_adapter.call_agent(
        agent_id=biometrics_insight_engine_adapter.agent_id,
        user_input=query,
        context={
            "user_id": user_id,
            "session_id": session_id
        }
    )
    
    # Mostrar respuesta
    logger.info(f"Respuesta A2A recibida: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    return response

async def test_metrics():
    """Prueba la obtención de métricas del adaptador."""
    logger.info("Obteniendo métricas del adaptador...")
    
    # Obtener métricas
    metrics = await biometrics_insight_engine_adapter.get_metrics()
    
    # Mostrar métricas
    logger.info(f"Métricas: {json.dumps(metrics, indent=2, ensure_ascii=False)}")
    
    return metrics

async def main():
    """Función principal del script."""
    try:
        logger.info("Iniciando prueba del adaptador del BiometricsInsightEngine...")
        
        # Inicializar componentes
        logger.info("Inicializando servidor A2A...")
        await a2a_server.start()
        
        logger.info("Inicializando adaptador A2A...")
        await a2a_adapter.start()
        
        logger.info("Inicializando adaptador del Intent Analyzer...")
        await intent_analyzer_adapter.initialize()
        
        logger.info("Inicializando adaptador del State Manager...")
        await state_manager_adapter.initialize()
        
        logger.info("Inicializando adaptador del BiometricsInsightEngine...")
        await initialize_biometrics_insight_engine_adapter()
        
        # Ejecutar pruebas
        logger.info("Ejecutando pruebas...")
        
        # Prueba de llamada directa
        direct_response = await test_direct_call()
        
        # Esperar un momento para asegurar que el adaptador esté registrado
        await asyncio.sleep(1)
        
        # Prueba de llamada a través del sistema A2A
        a2a_response = await test_a2a_call()
        
        # Prueba de métricas
        metrics = await test_metrics()
        
        # Verificar resultados
        logger.info("Verificando resultados...")
        
        direct_success = direct_response.get("status") == "success"
        a2a_success = a2a_response.get("status") == "success"
        metrics_success = "metrics" in metrics
        
        if direct_success and a2a_success and metrics_success:
            logger.info("✅ Todas las pruebas completadas con éxito")
        else:
            logger.error("❌ Algunas pruebas fallaron")
            if not direct_success:
                logger.error("  - Prueba de llamada directa fallida")
            if not a2a_success:
                logger.error("  - Prueba de llamada A2A fallida")
            if not metrics_success:
                logger.error("  - Prueba de métricas fallida")
        
        # Detener componentes
        logger.info("Deteniendo componentes...")
        await a2a_server.stop()
        
        logger.info("Prueba completada")
        
    except Exception as e:
        logger.error(f"Error durante la prueba: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
