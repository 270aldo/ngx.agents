#!/usr/bin/env python
"""
Script para probar el adaptador del Orchestrator con el servidor A2A optimizado.

Este script inicializa el servidor A2A optimizado y el adaptador del Orchestrator,
y luego realiza una prueba de comunicación entre ellos y otros agentes.
"""

import asyncio
import logging
import sys
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("test_orchestrator_adapter")

# Importar componentes necesarios
from infrastructure.a2a_optimized import a2a_server
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.orchestrator_adapter import (
    orchestrator_adapter,
    initialize_orchestrator_adapter,
)
from infrastructure.adapters.recovery_corrective_adapter import (
    initialize_recovery_corrective_adapter,
)
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter


async def test_direct_call():
    """Prueba una llamada directa al adaptador del Orchestrator."""
    logger.info("Probando llamada directa al adaptador del Orchestrator...")

    # Datos de prueba
    query = (
        "Necesito un plan de entrenamiento y recuperación para una lesión en la rodilla"
    )
    user_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Llamar al adaptador directamente
    response = await orchestrator_adapter.run_async_impl(
        query=query, user_id=user_id, session_id=session_id
    )

    # Mostrar respuesta
    logger.info(
        f"Respuesta directa recibida: {json.dumps(response, indent=2, ensure_ascii=False)}"
    )

    return response


async def test_a2a_call():
    """Prueba una llamada a través del sistema A2A."""
    logger.info("Probando llamada a través del sistema A2A...")

    # Datos de prueba
    query = "Coordina un plan de entrenamiento con el agente de entrenamiento y el agente de recuperación"
    user_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Llamar al adaptador a través del sistema A2A
    response = await a2a_adapter.call_agent(
        agent_id=orchestrator_adapter.agent_id,
        user_input=query,
        context={
            "user_id": user_id,
            "session_id": session_id,
            "requires_coordination": True,
        },
    )

    # Mostrar respuesta
    logger.info(
        f"Respuesta A2A recibida: {json.dumps(response, indent=2, ensure_ascii=False)}"
    )

    return response


async def test_multi_agent_coordination():
    """Prueba la coordinación de múltiples agentes a través del Orchestrator."""
    logger.info("Probando coordinación de múltiples agentes...")

    # Datos de prueba
    query = "Necesito un plan integral que incluya entrenamiento y recuperación para una lesión en la rodilla"
    user_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Llamar al adaptador directamente con un contexto que requiere coordinación
    response = await orchestrator_adapter.run_async_impl(
        query=query,
        user_id=user_id,
        session_id=session_id,
        context={
            "requires_coordination": True,
            "agent_interactions": ["elite_training_strategist", "recovery_corrective"],
        },
    )

    # Mostrar respuesta
    logger.info(
        f"Respuesta de coordinación recibida: {json.dumps(response, indent=2, ensure_ascii=False)}"
    )

    return response


async def test_intent_analysis():
    """Prueba el análisis de intención a través del Orchestrator."""
    logger.info("Probando análisis de intención...")

    # Datos de prueba
    query = "Tengo dolor en la rodilla después de correr, ¿qué debo hacer?"
    context = {}

    # Analizar intención
    intent = await orchestrator_adapter._analyze_intent(query, context)

    # Mostrar resultado
    logger.info(
        f"Intención analizada: {json.dumps(intent, indent=2, ensure_ascii=False)}"
    )

    # Determinar agentes objetivo
    target_agents, priority = await orchestrator_adapter._determine_target_agents(
        intent, query, context
    )

    # Mostrar resultado
    logger.info(f"Agentes objetivo: {target_agents}")
    logger.info(f"Prioridad: {orchestrator_adapter._get_priority_name(priority)}")

    return intent, target_agents, priority


async def test_emergency_routing():
    """Prueba el enrutamiento de emergencia."""
    logger.info("Probando enrutamiento de emergencia...")

    # Datos de prueba
    query = "EMERGENCIA: Tengo un dolor agudo en el pecho y dificultad para respirar durante el entrenamiento"
    user_id = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")
    session_id = "test_session_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Llamar al adaptador directamente
    response = await orchestrator_adapter.run_async_impl(
        query=query, user_id=user_id, session_id=session_id
    )

    # Mostrar respuesta
    logger.info(
        f"Respuesta de emergencia recibida: {json.dumps(response, indent=2, ensure_ascii=False)}"
    )

    return response


async def main():
    """Función principal del script."""
    try:
        logger.info("Iniciando prueba del adaptador del Orchestrator...")

        # Inicializar componentes
        logger.info("Inicializando servidor A2A...")
        await a2a_server.start()

        logger.info("Inicializando adaptador A2A...")
        await a2a_adapter.start()

        logger.info("Inicializando adaptador del Intent Analyzer...")
        await intent_analyzer_adapter.initialize()

        logger.info("Inicializando adaptador del State Manager...")
        await state_manager_adapter.initialize()

        logger.info("Inicializando adaptador del Recovery Corrective...")
        await initialize_recovery_corrective_adapter()

        logger.info("Inicializando adaptador del Orchestrator...")
        await initialize_orchestrator_adapter()

        # Esperar un momento para asegurar que los adaptadores estén registrados
        await asyncio.sleep(1)

        # Ejecutar pruebas
        logger.info("Ejecutando pruebas...")

        # Prueba de análisis de intención
        intent_result, target_agents, priority = await test_intent_analysis()

        # Prueba de llamada directa
        direct_response = await test_direct_call()

        # Prueba de llamada a través del sistema A2A
        a2a_response = await test_a2a_call()

        # Prueba de coordinación de múltiples agentes
        multi_agent_response = await test_multi_agent_coordination()

        # Prueba de enrutamiento de emergencia
        emergency_response = await test_emergency_routing()

        # Verificar resultados
        logger.info("Verificando resultados...")

        intent_success = intent_result is not None and len(target_agents) > 0
        direct_success = direct_response.get("status") == "success"
        a2a_success = a2a_response.get("status") == "success"
        multi_agent_success = multi_agent_response.get("status") == "success"
        emergency_success = emergency_response.get("status") == "success"

        if (
            intent_success
            and direct_success
            and a2a_success
            and multi_agent_success
            and emergency_success
        ):
            logger.info("✅ Todas las pruebas completadas con éxito")
        else:
            logger.error("❌ Algunas pruebas fallaron")
            if not intent_success:
                logger.error("  - Prueba de análisis de intención fallida")
            if not direct_success:
                logger.error("  - Prueba de llamada directa fallida")
            if not a2a_success:
                logger.error("  - Prueba de llamada A2A fallida")
            if not multi_agent_success:
                logger.error("  - Prueba de coordinación de múltiples agentes fallida")
            if not emergency_success:
                logger.error("  - Prueba de enrutamiento de emergencia fallida")

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
