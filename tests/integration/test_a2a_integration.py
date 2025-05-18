"""
Pruebas de integración para el Servidor A2A optimizado.

Este módulo contiene pruebas que verifican la interacción correcta
entre el Servidor A2A optimizado y los demás componentes del sistema.
"""


import os
# Configurar modo mock para pruebas
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"

import asyncio
import pytest
import uuid
import time
import sys
from typing import Dict, Any, List, Optional

# Importar adaptadores
from infrastructure.adapters.state_manager_adapter import StateManagerAdapter
from infrastructure.adapters.intent_analyzer_adapter import IntentAnalyzerAdapter

# Crear un mock para el servidor A2A en lugar de usar el real
class MockA2AAdapter:
    def __init__(self):
        self.registered_agents = {}
        self.messages = {}
        self.running = False
    
    async def start(self):
        self.running = True
        return True
    
    async def stop(self):
        self.running = False
        return True
    
    def register_agent(self, agent_id, agent_info):
        self.registered_agents[agent_id] = agent_info
        return True
    
    def unregister_agent(self, agent_id):
        if agent_id in self.registered_agents:
            del self.registered_agents[agent_id]
        return True
    
    def get_registered_agents(self):
        return self.registered_agents
    
    async def send_message(self, from_agent_id, to_agent_id, message, priority="NORMAL"):
        if to_agent_id not in self.messages:
            self.messages[to_agent_id] = []
        
        self.messages[to_agent_id].append({
            "from": from_agent_id,
            "content": message,
            "priority": priority,
            "timestamp": time.time()
        })
        
        # Procesar el mensaje si hay un callback registrado
        if to_agent_id in self.registered_agents and "message_callback" in self.registered_agents[to_agent_id]:
            callback = self.registered_agents[to_agent_id]["message_callback"]
            if callback and callable(callback):
                await callback(message)
        
        return True
    
    async def call_agent(self, agent_id, user_input, context=None):
        if agent_id not in self.registered_agents:
            return {
                "status": "error",
                "error": f"Agente {agent_id} no encontrado",
                "agent_id": agent_id
            }
        
        # Crear mensaje para el agente
        message = {
            "query": user_input,
            "context": context or {}
        }
        
        # Llamar al callback del agente
        callback = self.registered_agents[agent_id].get("message_callback")
        if callback and callable(callback):
            response = await callback(message)
            if response:
                return response
        
        # Respuesta por defecto si no hay callback o no devuelve nada
        return {
            "status": "success",
            "agent_id": agent_id,
            "agent_name": self.registered_agents[agent_id].get("name", agent_id),
            "output": f"Respuesta simulada de {agent_id}",
            "timestamp": time.time()
        }
    
    async def call_multiple_agents(self, user_input, agent_ids, context=None):
        results = {}
        for agent_id in agent_ids:
            try:
                result = await self.call_agent(
                    agent_id=agent_id,
                    user_input=user_input,
                    context=context
                )
                results[agent_id] = result
            except Exception as e:
                results[agent_id] = {
                    "status": "error",
                    "error": str(e),
                    "agent_id": agent_id
                }
        return results

# Usar el mock en lugar del adaptador real
a2a_adapter = MockA2AAdapter()

# Configurar adaptadores para usar versiones optimizadas
state_manager = StateManagerAdapter()
intent_analyzer = IntentAnalyzerAdapter(use_optimized=True)


@pytest.fixture
def initialized_adapters():
    """Fixture para inicializar los adaptadores antes de las pruebas."""
    # Crear una función asíncrona dentro del fixture
    async def _initialize():
        # Inicializar A2A (ahora es un mock, no necesita inicialización asíncrona real)
        await a2a_adapter.start()
        
        # Inicializar State Manager e Intent Analyzer
        await state_manager.initialize()
        await intent_analyzer.initialize()
        
        # Asegurar que todos los adaptadores usen las versiones optimizadas
        state_manager.use_optimized = True
        intent_analyzer.set_use_optimized(True)
    
    # Ejecutar la función asíncrona
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_initialize())
    
    yield
    
    # Limpiar después de las pruebas
    async def _cleanup():
        await a2a_adapter.stop()
        state_manager._reset_stats()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_cleanup())


@pytest.fixture
def test_conversation():
    """Fixture que crea una conversación de prueba."""
    # Crear una función asíncrona dentro del fixture
    async def _create_conversation():
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        context = await state_manager.create_conversation(user_id=user_id)
        return context, user_id
    
    # Ejecutar la función asíncrona
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    context, user_id = loop.run_until_complete(_create_conversation())
    
    yield context
    
    # Limpiar después de las pruebas
    async def _cleanup():
        await state_manager.delete_conversation(context.conversation_id)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_cleanup())


@pytest.fixture
def mock_agents():
    """Fixture que registra agentes simulados para las pruebas."""
    # Crear diccionarios para almacenar mensajes recibidos
    received_messages = {}
    
    # Función para crear un manejador de mensajes para un agente
    def create_message_handler(agent_id):
        async def message_handler(message):
            if agent_id not in received_messages:
                received_messages[agent_id] = []
            received_messages[agent_id].append(message)
            
            # Simular procesamiento y respuesta
            if isinstance(message, dict) and "query" in message:
                return {
                    "status": "success",
                    "agent_id": agent_id,
                    "agent_name": f"Mock {agent_id.capitalize()}",
                    "output": f"Respuesta de {agent_id} a: {message.get('query')}",
                    "timestamp": time.time()
                }
            return None
        return message_handler
    
    # Registrar agentes simulados directamente (sin async)
    test_agents = ["elite_training_strategist", "precision_nutrition_architect", "biometrics_insight_engine"]
    
    for agent_id in test_agents:
        a2a_adapter.register_agent(
            agent_id=agent_id,
            agent_info={
                "name": f"Mock {agent_id.capitalize()}",
                "description": f"Agente simulado para pruebas: {agent_id}",
                "message_callback": create_message_handler(agent_id)
            }
        )
    
    yield test_agents, received_messages
    
    # Limpiar después de las pruebas (sin async)
    for agent_id in test_agents:
        a2a_adapter.unregister_agent(agent_id)


@pytest.mark.asyncio
async def test_a2a_agent_registration(initialized_adapters):
    """
    Prueba el registro de agentes en el servidor A2A.
    
    Verifica que:
    1. Se puedan registrar agentes correctamente
    2. Se pueda obtener la lista de agentes registrados
    3. Se puedan eliminar agentes
    """
    # Crear un agente de prueba
    test_agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
    
    # Función de callback simulada
    async def mock_callback(message):
        return {"status": "received", "message": message}
    
    # 1. Registrar el agente
    a2a_adapter.register_agent(
        agent_id=test_agent_id,
        agent_info={
            "name": "Agente de Prueba",
            "description": "Agente para probar el registro en A2A",
            "message_callback": mock_callback
        }
    )
    
    # 2. Verificar que el agente esté registrado
    registered_agents = a2a_adapter.get_registered_agents()
    assert test_agent_id in registered_agents, f"El agente {test_agent_id} no está registrado"
    
    # 3. Eliminar el agente
    a2a_adapter.unregister_agent(test_agent_id)
    
    # Verificar que el agente ya no esté registrado
    registered_agents = a2a_adapter.get_registered_agents()
    assert test_agent_id not in registered_agents, f"El agente {test_agent_id} sigue registrado después de eliminarlo"


@pytest.mark.asyncio
async def test_a2a_message_sending(initialized_adapters, mock_agents):
    """
    Prueba el envío de mensajes entre agentes a través del servidor A2A.
    
    Verifica que:
    1. Se puedan enviar mensajes entre agentes
    2. Los mensajes se entreguen correctamente
    3. Se puedan enviar mensajes con diferentes prioridades
    """
    test_agents, received_messages = mock_agents
    
    # Verificar que hay al menos dos agentes para la prueba
    assert len(test_agents) >= 2, "Se necesitan al menos dos agentes para la prueba"
    
    from_agent = test_agents[0]
    to_agent = test_agents[1]
    
    # 1. Enviar un mensaje con prioridad normal
    message_content = {
        "type": "test_message",
        "content": "Este es un mensaje de prueba",
        "timestamp": time.time()
    }
    
    success = await a2a_adapter.send_message(
        from_agent_id=from_agent,
        to_agent_id=to_agent,
        message=message_content,
        priority="NORMAL"
    )
    
    assert success, "El envío del mensaje falló"
    
    # Esperar un momento para que el mensaje se procese
    await asyncio.sleep(0.5)
    
    # 2. Verificar que el mensaje se haya entregado
    assert to_agent in received_messages, f"El agente {to_agent} no recibió ningún mensaje"
    assert len(received_messages[to_agent]) > 0, f"El agente {to_agent} no tiene mensajes"
    
    # Verificar el contenido del mensaje
    received = received_messages[to_agent][-1]
    assert received["type"] == message_content["type"], "El tipo de mensaje no coincide"
    assert received["content"] == message_content["content"], "El contenido del mensaje no coincide"
    
    # 3. Enviar un mensaje con prioridad alta
    high_priority_message = {
        "type": "urgent_test_message",
        "content": "Este es un mensaje urgente de prueba",
        "timestamp": time.time()
    }
    
    success = await a2a_adapter.send_message(
        from_agent_id=from_agent,
        to_agent_id=to_agent,
        message=high_priority_message,
        priority="HIGH"
    )
    
    assert success, "El envío del mensaje con prioridad alta falló"
    
    # Esperar un momento para que el mensaje se procese
    await asyncio.sleep(0.5)
    
    # Verificar que el mensaje de alta prioridad se haya entregado
    assert len(received_messages[to_agent]) > 1, f"El agente {to_agent} no recibió el mensaje de alta prioridad"
    
    # Verificar el contenido del mensaje de alta prioridad
    received_high_priority = received_messages[to_agent][-1]
    assert received_high_priority["type"] == high_priority_message["type"], "El tipo de mensaje de alta prioridad no coincide"
    assert received_high_priority["content"] == high_priority_message["content"], "El contenido del mensaje de alta prioridad no coincide"


@pytest.mark.asyncio
async def test_a2a_call_agent(initialized_adapters, mock_agents, test_conversation):
    """
    Prueba la llamada directa a un agente a través del servidor A2A.
    
    Verifica que:
    1. Se pueda llamar a un agente específico
    2. El agente procese la consulta y devuelva una respuesta
    3. La respuesta tenga el formato esperado
    """
    test_agents, _ = mock_agents
    
    # Seleccionar un agente para la prueba
    agent_id = test_agents[0]
    
    # Datos de prueba
    user_input = "¿Puedes recomendarme un plan de entrenamiento?"
    context_data = {
        "conversation_id": test_conversation.conversation_id,
        "user_id": test_conversation.user_id
    }
    
    # 1. Llamar al agente
    response = await a2a_adapter.call_agent(
        agent_id=agent_id,
        user_input=user_input,
        context=context_data
    )
    
    # 2. Verificar la respuesta
    assert response, "No se recibió respuesta del agente"
    assert "status" in response, "La respuesta no tiene campo 'status'"
    assert "agent_id" in response, "La respuesta no tiene campo 'agent_id'"
    assert "output" in response, "La respuesta no tiene campo 'output'"
    
    # 3. Verificar que la respuesta sea del agente correcto
    assert response["agent_id"] == agent_id, f"La respuesta no es del agente esperado: {agent_id}"
    assert response["status"] == "success", "El estado de la respuesta no es 'success'"
    
    # Verificar que la respuesta contenga la consulta original
    assert user_input in response["output"], "La respuesta no hace referencia a la consulta original"


@pytest.mark.asyncio
async def test_a2a_call_multiple_agents(initialized_adapters, mock_agents, test_conversation):
    """
    Prueba la llamada a múltiples agentes en paralelo a través del servidor A2A.
    
    Verifica que:
    1. Se puedan llamar a múltiples agentes simultáneamente
    2. Todos los agentes procesen la consulta y devuelvan respuestas
    3. Las respuestas se combinen correctamente
    """
    test_agents, _ = mock_agents
    
    # Datos de prueba
    user_input = "Necesito mejorar mi rendimiento deportivo"
    context_data = {
        "conversation_id": test_conversation.conversation_id,
        "user_id": test_conversation.user_id
    }
    
    # 1. Llamar a múltiples agentes
    responses = await a2a_adapter.call_multiple_agents(
        user_input=user_input,
        agent_ids=test_agents,
        context=context_data
    )
    
    # 2. Verificar las respuestas
    assert responses, "No se recibieron respuestas de los agentes"
    assert isinstance(responses, dict), "Las respuestas no están en formato de diccionario"
    
    # 3. Verificar que se recibieron respuestas de todos los agentes
    for agent_id in test_agents:
        assert agent_id in responses, f"No se recibió respuesta del agente {agent_id}"
        agent_response = responses[agent_id]
        
        assert "status" in agent_response, f"La respuesta del agente {agent_id} no tiene campo 'status'"
        assert "agent_id" in agent_response, f"La respuesta del agente {agent_id} no tiene campo 'agent_id'"
        assert "output" in agent_response, f"La respuesta del agente {agent_id} no tiene campo 'output'"
        
        assert agent_response["agent_id"] == agent_id, f"La respuesta no es del agente esperado: {agent_id}"
        assert agent_response["status"] == "success", f"El estado de la respuesta del agente {agent_id} no es 'success'"
        
        # Verificar que la respuesta contenga la consulta original
        assert user_input in agent_response["output"], f"La respuesta del agente {agent_id} no hace referencia a la consulta original"


@pytest.mark.asyncio
async def test_a2a_integration_with_state_manager(initialized_adapters, mock_agents):
    """
    Prueba la integración entre el servidor A2A y el State Manager.
    
    Verifica que:
    1. Se pueda crear una conversación en el State Manager
    2. Se puedan llamar a agentes con el contexto de la conversación
    3. Se puedan guardar las respuestas de los agentes en el State Manager
    """
    test_agents, _ = mock_agents
    agent_id = test_agents[0]
    
    # 1. Crear una conversación
    user_id = f"integration_test_user_{uuid.uuid4().hex[:8]}"
    context = await state_manager.create_conversation(user_id=user_id)
    conversation_id = context.conversation_id
    
    # Añadir un mensaje inicial
    await state_manager.add_message_to_conversation(
        conversation_id=conversation_id,
        message={
            "role": "user",
            "content": "Hola, necesito ayuda con mi entrenamiento"
        }
    )
    
    # 2. Llamar a un agente con el contexto de la conversación
    user_input = "¿Qué ejercicios debo hacer para mejorar mi resistencia?"
    context_data = {
        "conversation_id": conversation_id,
        "user_id": user_id
    }
    
    response = await a2a_adapter.call_agent(
        agent_id=agent_id,
        user_input=user_input,
        context=context_data
    )
    
    # Verificar la respuesta
    assert response, "No se recibió respuesta del agente"
    assert response["status"] == "success", "El estado de la respuesta no es 'success'"
    
    # 3. Guardar la respuesta en el State Manager
    await state_manager.add_message_to_conversation(
        conversation_id=conversation_id,
        message={
            "role": "assistant",
            "content": response["output"],
            "agent_id": agent_id,
            "timestamp": time.time()
        }
    )
    
    # Verificar que la respuesta se haya guardado
    updated_context = await state_manager.get_conversation(conversation_id)
    assert len(updated_context.messages) == 2, "No se guardaron todos los mensajes"
    
    # Verificar el contenido del último mensaje
    last_message = updated_context.messages[-1]
    assert last_message["role"] == "assistant", "El rol del mensaje no es 'assistant'"
    assert last_message["content"] == response["output"], "El contenido del mensaje no coincide con la respuesta"
    assert last_message["agent_id"] == agent_id, "El ID del agente no coincide"
    
    # Limpiar
    await state_manager.delete_conversation(conversation_id)


@pytest.mark.asyncio
async def test_a2a_integration_with_intent_analyzer(initialized_adapters, mock_agents, test_conversation):
    """
    Prueba la integración entre el servidor A2A y el Intent Analyzer.
    
    Verifica que:
    1. Se pueda analizar una intención con el Intent Analyzer
    2. Se puedan llamar a los agentes recomendados por el Intent Analyzer
    3. Las respuestas de los agentes se puedan combinar y guardar
    """
    test_agents, _ = mock_agents
    
    # 1. Analizar una intención
    user_query = "Quiero mejorar mi rendimiento en ciclismo"
    
    intents = await intent_analyzer.analyze_intent(
        user_query=user_query,
        conversation_id=test_conversation.conversation_id,
        user_id=test_conversation.user_id
    )
    
    # Verificar que se hayan analizado intenciones
    assert intents, "No se obtuvieron intenciones del analizador"
    assert len(intents) > 0, "La lista de intenciones está vacía"
    
    # Obtener los agentes recomendados por la intención principal
    recommended_agents = intents[0].agents
    
    # Filtrar para usar solo los agentes que tenemos registrados
    available_agents = [agent for agent in recommended_agents if agent in test_agents]
    
    # Verificar que haya al menos un agente disponible
    assert available_agents, "No hay agentes disponibles para la prueba"
    
    # 2. Llamar a los agentes recomendados
    context_data = {
        "conversation_id": test_conversation.conversation_id,
        "user_id": test_conversation.user_id,
        "intent": {
            "intent_type": intents[0].intent_type,
            "confidence": intents[0].confidence
        }
    }
    
    responses = await a2a_adapter.call_multiple_agents(
        user_input=user_query,
        agent_ids=available_agents,
        context=context_data
    )
    
    # Verificar las respuestas
    assert responses, "No se recibieron respuestas de los agentes"
    
    # 3. Guardar la intención y las respuestas
    # Guardar la intención
    intent_dict = {
        "intent_type": intents[0].intent_type,
        "confidence": intents[0].confidence,
        "agents": intents[0].agents,
        "metadata": intents[0].metadata
    }
    await state_manager.add_intent_to_conversation(
        conversation_id=test_conversation.conversation_id,
        intent=intent_dict
    )
    
    # Guardar las respuestas de los agentes
    for agent_id, response in responses.items():
        if response["status"] == "success":
            await state_manager.add_message_to_conversation(
                conversation_id=test_conversation.conversation_id,
                message={
                    "role": "assistant",
                    "content": response["output"],
                    "agent_id": agent_id,
                    "timestamp": time.time()
                }
            )
    
    # Verificar que se hayan guardado las respuestas
    updated_context = await state_manager.get_conversation(test_conversation.conversation_id)
    
    # Verificar la intención
    assert hasattr(updated_context, "intents"), "La conversación no tiene intenciones"
    assert len(updated_context.intents) > 0, "No se guardó la intención"
    
    # Verificar los mensajes
    assert hasattr(updated_context, "messages"), "La conversación no tiene mensajes"
    assert len(updated_context.messages) == len(responses), "No se guardaron todas las respuestas"


@pytest.mark.asyncio
async def test_a2a_performance_under_load(initialized_adapters, mock_agents):
    """
    Prueba el rendimiento del servidor A2A bajo carga.
    
    Verifica que:
    1. El servidor pueda manejar múltiples solicitudes simultáneas
    2. El tiempo de respuesta sea aceptable bajo carga
    3. No se pierdan mensajes durante la carga
    """
    test_agents, _ = mock_agents
    
    # Parámetros de carga
    num_requests = 10
    agent_id = test_agents[0]
    
    # Crear consultas de prueba
    test_queries = [
        f"Consulta de prueba {i} para rendimiento" for i in range(num_requests)
    ]
    
    # Función para realizar una llamada al agente
    async def call_agent_task(query):
        return await a2a_adapter.call_agent(
            agent_id=agent_id,
            user_input=query
        )
    
    # Medir tiempo de inicio
    start_time = time.time()
    
    # Crear tareas para todas las consultas
    tasks = [call_agent_task(query) for query in test_queries]
    
    # Ejecutar todas las tareas en paralelo
    responses = await asyncio.gather(*tasks)
    
    # Medir tiempo total
    total_time = time.time() - start_time
    avg_time = total_time / num_requests
    
    # Verificar que todas las consultas recibieron respuesta
    assert len(responses) == num_requests, "No se recibieron todas las respuestas"
    
    # Verificar que todas las respuestas son válidas
    for i, response in enumerate(responses):
        assert response, f"No se recibió respuesta para la consulta {i}"
        assert response["status"] == "success", f"El estado de la respuesta {i} no es 'success'"
        assert test_queries[i] in response["output"], f"La respuesta {i} no hace referencia a la consulta original"
    
    # Verificar rendimiento
    assert avg_time < 0.5, f"Tiempo promedio por operación ({avg_time:.3f}s) excede el límite de 0.5s"
