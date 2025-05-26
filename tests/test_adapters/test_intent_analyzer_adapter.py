"""
Pruebas para el adaptador del analizador de intenciones.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador del analizador de intenciones.
"""

import pytest

from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter


@pytest.mark.asyncio
async def test_initialize():
    """Prueba la inicialización del adaptador."""
    # Inicializar adaptador
    result = await intent_analyzer_adapter.initialize()

    # Verificar resultado
    assert result is True


@pytest.mark.asyncio
async def test_analyze_intent():
    """Prueba la función analyze_intent del adaptador."""
    # Datos de prueba
    user_query = "Necesito un programa de entrenamiento para ganar masa muscular"

    # Analizar intención
    intents = await intent_analyzer_adapter.analyze_intent(user_query)

    # Verificar resultado
    assert len(intents) > 0
    assert hasattr(intents[0], "intent_type")
    assert hasattr(intents[0], "confidence")
    assert hasattr(intents[0], "agents")


@pytest.mark.asyncio
async def test_analyze_intents_with_embeddings():
    """Prueba la función analyze_intents_with_embeddings del adaptador."""
    # Datos de prueba
    user_query = "¿Cuál es la mejor dieta para perder peso?"

    # Analizar intención con embeddings
    intents = await intent_analyzer_adapter.analyze_intents_with_embeddings(user_query)

    # Verificar resultado
    assert len(intents) > 0
    assert hasattr(intents[0], "intent_type")
    assert hasattr(intents[0], "confidence")
    assert hasattr(intents[0], "agents")


@pytest.mark.asyncio
async def test_set_use_optimized():
    """Prueba la función set_use_optimized del adaptador."""
    # Cambiar a modo optimizado
    intent_analyzer_adapter.set_use_optimized(True)

    # Verificar que se cambió correctamente
    assert intent_analyzer_adapter.use_optimized is True

    # Analizar intención en modo optimizado
    user_query = "Necesito un programa de entrenamiento"
    intents = await intent_analyzer_adapter.analyze_intent(user_query)

    # Verificar resultado
    assert len(intents) > 0

    # Cambiar a modo original
    intent_analyzer_adapter.set_use_optimized(False)

    # Verificar que se cambió correctamente
    assert intent_analyzer_adapter.use_optimized is False

    # Analizar intención en modo original
    intents = await intent_analyzer_adapter.analyze_intent(user_query)

    # Verificar resultado
    assert len(intents) > 0


@pytest.mark.asyncio
async def test_get_stats():
    """Prueba la función get_stats del adaptador."""
    # Obtener estadísticas
    stats = await intent_analyzer_adapter.get_stats()

    # Verificar resultado
    assert "total_queries" in stats
    assert "original_analyzer" in stats
