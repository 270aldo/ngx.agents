"""
Pruebas para el servidor A2A optimizado.

Este módulo contiene pruebas para verificar el correcto funcionamiento
del servidor A2A optimizado con comunicación asíncrona y mecanismos de resiliencia.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.a2a_optimized import a2a_server, MessagePriority, CircuitBreakerState


@pytest.mark.asyncio
async def test_a2a_optimized_initialization():
    """Prueba la inicialización del servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Verificar que está en ejecución
    stats = await a2a_server.get_stats()
    assert stats["running"] is True
    
    # Detener servidor
    await a2a_server.stop()
    
    # Verificar que se detuvo
    stats = await a2a_server.get_stats()
    assert stats["running"] is False


@pytest.mark.asyncio
async def test_a2a_optimized_register_agent():
    """Prueba el registro de agentes en el servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Crear manejador de mensajes
    async def message_handler(message):
        pass
    
    # Registrar agente
    await a2a_server.register_agent("test_agent", message_handler)
    
    # Verificar que se registró
    stats = await a2a_server.get_stats()
    assert "test_agent" in stats["registered_agents"]
    
    # Eliminar agente
    await a2a_server.unregister_agent("test_agent")
    
    # Verificar que se eliminó
    stats = await a2a_server.get_stats()
    assert "test_agent" not in stats["registered_agents"]
    
    # Detener servidor
    await a2a_server.stop()


@pytest.mark.asyncio
async def test_a2a_optimized_send_message():
    """Prueba el envío de mensajes a través del servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Variables para verificar recepción de mensajes
    received_messages = []
    
    # Manejador de mensajes para el agente receptor
    async def message_handler(message):
        received_messages.append(message)
    
    # Registrar agentes
    await a2a_server.register_agent("agent1", AsyncMock())
    await a2a_server.register_agent("agent2", message_handler)
    
    # Enviar mensaje
    message = {"text": "Mensaje de prueba", "data": {"key": "value"}}
    result = await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=message,
        priority=MessagePriority.NORMAL
    )
    
    # Esperar a que se procese el mensaje
    await asyncio.sleep(0.1)
    
    # Verificar que se recibió el mensaje
    assert result is True
    assert len(received_messages) == 1
    assert received_messages[0]["content"] == message
    
    # Detener servidor
    await a2a_server.stop()


@pytest.mark.asyncio
async def test_a2a_optimized_message_priority():
    """Prueba la priorización de mensajes en el servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Variables para verificar recepción de mensajes
    received_messages = []
    
    # Manejador de mensajes para el agente receptor
    async def message_handler(message):
        # Simular procesamiento lento
        await asyncio.sleep(0.1)
        received_messages.append(message)
    
    # Registrar agentes
    await a2a_server.register_agent("agent1", AsyncMock())
    await a2a_server.register_agent("agent2", message_handler)
    
    # Enviar mensajes con diferentes prioridades
    # El de prioridad alta debería procesarse primero aunque se envíe después
    low_message = {"text": "Mensaje de baja prioridad"}
    normal_message = {"text": "Mensaje de prioridad normal"}
    high_message = {"text": "Mensaje de alta prioridad"}
    critical_message = {"text": "Mensaje crítico"}
    
    # Enviar en orden inverso a la prioridad
    await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=low_message,
        priority=MessagePriority.LOW
    )
    
    await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=normal_message,
        priority=MessagePriority.NORMAL
    )
    
    await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=high_message,
        priority=MessagePriority.HIGH
    )
    
    await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=critical_message,
        priority=MessagePriority.CRITICAL
    )
    
    # Esperar a que se procesen los mensajes
    await asyncio.sleep(0.5)
    
    # Verificar que se recibieron en orden de prioridad
    assert len(received_messages) == 4
    assert received_messages[0]["content"] == critical_message
    assert received_messages[1]["content"] == high_message
    assert received_messages[2]["content"] == normal_message
    assert received_messages[3]["content"] == low_message
    
    # Detener servidor
    await a2a_server.stop()


@pytest.mark.asyncio
async def test_a2a_optimized_circuit_breaker():
    """Prueba el circuit breaker del servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Manejador de mensajes que siempre falla
    async def failing_handler(message):
        raise Exception("Error simulado")
    
    # Registrar agentes
    await a2a_server.register_agent("agent1", AsyncMock())
    await a2a_server.register_agent("agent2", failing_handler)
    
    # Enviar varios mensajes para activar el circuit breaker
    message = {"text": "Mensaje de prueba"}
    
    # Configurar umbral bajo para pruebas
    a2a_server.circuit_breaker_threshold = 3
    a2a_server.circuit_breaker_reset_timeout = 0.5
    
    # Enviar mensajes hasta activar el circuit breaker
    for _ in range(5):
        await a2a_server.send_message(
            from_agent_id="agent1",
            to_agent_id="agent2",
            message=message,
            priority=MessagePriority.NORMAL
        )
    
    # Verificar que el circuit breaker está abierto
    circuit_state = await a2a_server.get_circuit_breaker_state("agent2")
    assert circuit_state == CircuitBreakerState.OPEN
    
    # Esperar a que se reinicie el circuit breaker
    await asyncio.sleep(0.6)
    
    # Verificar que el circuit breaker está en estado semi-abierto
    circuit_state = await a2a_server.get_circuit_breaker_state("agent2")
    assert circuit_state == CircuitBreakerState.HALF_OPEN
    
    # Detener servidor
    await a2a_server.stop()


@pytest.mark.asyncio
async def test_a2a_optimized_retry_mechanism():
    """Prueba el mecanismo de reintentos del servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Contador de intentos
    attempt_count = 0
    
    # Manejador de mensajes que falla en los primeros intentos
    async def flaky_handler(message):
        nonlocal attempt_count
        attempt_count += 1
        
        # Fallar en los primeros 2 intentos
        if attempt_count <= 2:
            raise Exception(f"Error simulado en intento {attempt_count}")
        
        # Éxito en el tercer intento
        return True
    
    # Registrar agentes
    await a2a_server.register_agent("agent1", AsyncMock())
    await a2a_server.register_agent("agent2", flaky_handler)
    
    # Configurar reintentos
    a2a_server.max_retry_attempts = 3
    a2a_server.retry_delay = 0.1
    
    # Enviar mensaje
    message = {"text": "Mensaje con reintentos"}
    result = await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=message,
        priority=MessagePriority.NORMAL
    )
    
    # Esperar a que se procesen los reintentos
    await asyncio.sleep(0.5)
    
    # Verificar que se realizaron 3 intentos y finalmente tuvo éxito
    assert attempt_count == 3
    assert result is True
    
    # Verificar estadísticas
    stats = await a2a_server.get_stats()
    assert stats["retry_attempts"] >= 2
    assert stats["successful_retries"] >= 1
    
    # Detener servidor
    await a2a_server.stop()


@pytest.mark.asyncio
async def test_a2a_optimized_message_timeout():
    """Prueba el timeout de mensajes en el servidor A2A optimizado."""
    # Iniciar servidor
    await a2a_server.start()
    
    # Manejador de mensajes que tarda demasiado
    async def slow_handler(message):
        await asyncio.sleep(0.5)  # Tarda más que el timeout
        return True
    
    # Registrar agentes
    await a2a_server.register_agent("agent1", AsyncMock())
    await a2a_server.register_agent("agent2", slow_handler)
    
    # Configurar timeout bajo para la prueba
    a2a_server.message_timeout = 0.2
    
    # Enviar mensaje
    message = {"text": "Mensaje con timeout"}
    result = await a2a_server.send_message(
        from_agent_id="agent1",
        to_agent_id="agent2",
        message=message,
        priority=MessagePriority.NORMAL
    )
    
    # Esperar a que se procese el mensaje
    await asyncio.sleep(0.6)
    
    # Verificar que el envío falló por timeout
    assert result is False
    
    # Verificar estadísticas
    stats = await a2a_server.get_stats()
    assert stats["timeouts"] >= 1
    
    # Detener servidor
    await a2a_server.stop()
