"""
Pruebas de integración completa del sistema NGX Agents.

Este módulo contiene pruebas que verifican la interacción correcta
entre todos los componentes principales del sistema:
- State Manager optimizado
- Intent Analyzer optimizado
- Servidor A2A optimizado

Estas pruebas simulan flujos de trabajo reales del sistema.
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
import json
from typing import Dict, Any, List, Optional

from infrastructure.adapters.state_manager_adapter import StateManagerAdapter, ConversationContext
from infrastructure.adapters.intent_analyzer_adapter import IntentAnalyzerAdapter
from infrastructure.adapters.a2a_adapter import A2AAdapter, a2a_adapter

# Configurar adaptadores para usar versiones optimizadas
state_manager = StateManagerAdapter()
intent_analyzer = IntentAnalyzerAdapter(use_optimized=True)


@pytest.fixture
def initialized_system():
    """Fixture para inicializar todo el sistema antes de las pruebas."""
    # Crear una función asíncrona dentro del fixture
    async def _initialize():
        # Inicializar A2A
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
            
            # Simular procesamiento y respuesta según el tipo de agente
            if isinstance(message, dict) and "query" in message:
                query = message.get("query", "")
                
                if agent_id == "elite_training_strategist":
                    return {
                        "status": "success",
                        "agent_id": agent_id,
                        "agent_name": "Elite Training Strategist",
                        "output": f"Plan de entrenamiento personalizado para: {query}",
                        "timestamp": time.time(),
                        "artifacts": [
                            {
                                "type": "training_plan",
                                "content": json.dumps({
                                    "title": "Plan de Entrenamiento Personalizado",
                                    "duration": "4 semanas",
                                    "sessions_per_week": 3,
                                    "focus": "Resistencia y fuerza",
                                    "exercises": ["Sentadillas", "Press de banca", "Dominadas"]
                                })
                            }
                        ]
                    }
                
                elif agent_id == "precision_nutrition_architect":
                    return {
                        "status": "success",
                        "agent_id": agent_id,
                        "agent_name": "Precision Nutrition Architect",
                        "output": f"Plan nutricional adaptado para: {query}",
                        "timestamp": time.time(),
                        "artifacts": [
                            {
                                "type": "nutrition_plan",
                                "content": json.dumps({
                                    "title": "Plan Nutricional Personalizado",
                                    "meals_per_day": 5,
                                    "calories": 2500,
                                    "macros": {"protein": "30%", "carbs": "50%", "fats": "20%"},
                                    "hydration": "3L diarios"
                                })
                            }
                        ]
                    }
                
                elif agent_id == "biometrics_insight_engine":
                    return {
                        "status": "success",
                        "agent_id": agent_id,
                        "agent_name": "Biometrics Insight Engine",
                        "output": f"Análisis biométrico para: {query}",
                        "timestamp": time.time(),
                        "artifacts": [
                            {
                                "type": "biometric_analysis",
                                "content": json.dumps({
                                    "title": "Análisis Biométrico",
                                    "metrics": ["Frecuencia cardíaca", "VO2 max", "Composición corporal"],
                                    "recommendations": ["Monitoreo de frecuencia cardíaca", "Prueba de esfuerzo"]
                                })
                            }
                        ]
                    }
                
                else:
                    return {
                        "status": "success",
                        "agent_id": agent_id,
                        "agent_name": f"Mock {agent_id.capitalize()}",
                        "output": f"Respuesta genérica de {agent_id} a: {query}",
                        "timestamp": time.time()
                    }
            return None
        return message_handler
    
    # Registrar agentes simulados
    test_agents = ["elite_training_strategist", "precision_nutrition_architect", "biometrics_insight_engine"]
    
    # Función asíncrona para registrar agentes
    async def _register_agents():
        for agent_id in test_agents:
            a2a_adapter.register_agent(
                agent_id=agent_id,
                agent_info={
                    "name": f"Mock {agent_id.capitalize()}",
                    "description": f"Agente simulado para pruebas: {agent_id}",
                    "message_callback": create_message_handler(agent_id)
                }
            )
    
    # Ejecutar la función asíncrona
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_register_agents())
    
    yield test_agents, received_messages
    
    # Limpiar después de las pruebas
    async def _cleanup():
        for agent_id in test_agents:
            a2a_adapter.unregister_agent(agent_id)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_cleanup())


@pytest.mark.asyncio
async def test_complete_user_interaction_flow(initialized_system, mock_agents):
    """
    Prueba un flujo completo de interacción de usuario con el sistema.
    
    Simula un escenario completo donde:
    1. Se crea una conversación para un usuario
    2. El usuario envía una consulta
    3. Se analiza la intención de la consulta
    4. Se identifican los agentes apropiados
    5. Se envían mensajes a los agentes
    6. Se reciben y procesan las respuestas
    7. Se actualiza el estado de la conversación
    """
    # Obtener los agentes de prueba
    test_agents, _ = mock_agents
    
    # 1. Crear una conversación para un usuario
    user_id = f"integration_test_user_{uuid.uuid4().hex[:8]}"
    context = await state_manager.create_conversation(user_id=user_id)
    conversation_id = context.conversation_id
    
    # 2. Usuario envía una consulta
    user_query = "Necesito un plan de entrenamiento y nutrición para preparar un maratón"
    
    # Guardar la consulta del usuario en el State Manager
    await state_manager.add_message_to_conversation(
        conversation_id=conversation_id,
        message={
            "role": "user",
            "content": user_query,
            "timestamp": time.time()
        }
    )
    
    # 3. Analizar la intención de la consulta
    intents = await intent_analyzer.analyze_intent(
        user_query=user_query,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    # Verificar que se hayan analizado intenciones
    assert intents, "No se obtuvieron intenciones del analizador"
    assert len(intents) > 0, "La lista de intenciones está vacía"
    
    # Guardar la intención en el State Manager
    intent_dict = {
        "intent_type": intents[0].intent_type,
        "confidence": intents[0].confidence,
        "agents": intents[0].agents,
        "metadata": intents[0].metadata
    }
    await state_manager.add_intent_to_conversation(
        conversation_id=conversation_id,
        intent=intent_dict
    )
    
    # 4. Identificar los agentes apropiados (filtrar por los disponibles)
    recommended_agents = intents[0].agents
    available_agents = [agent for agent in recommended_agents if agent in test_agents]
    
    # Si no hay agentes recomendados disponibles, usar todos los de prueba
    if not available_agents:
        available_agents = test_agents
    
    # 5 y 6. Enviar mensajes a los agentes y recibir respuestas
    context_data = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "intent": {
            "intent_type": intents[0].intent_type,
            "confidence": intents[0].confidence
        }
    }
    
    # Llamar a los agentes
    responses = await a2a_adapter.call_multiple_agents(
        user_input=user_query,
        agent_ids=available_agents,
        context=context_data
    )
    
    # Verificar las respuestas
    assert responses, "No se recibieron respuestas de los agentes"
    assert len(responses) == len(available_agents), "No se recibieron respuestas de todos los agentes"
    
    # 7. Actualizar el estado de la conversación con las respuestas
    for agent_id, response in responses.items():
        if response["status"] == "success":
            # Guardar el mensaje de respuesta
            await state_manager.add_message_to_conversation(
                conversation_id=conversation_id,
                message={
                    "role": "assistant",
                    "content": response["output"],
                    "agent_id": agent_id,
                    "timestamp": time.time()
                }
            )
            
            # Guardar artefactos si existen
            if "artifacts" in response and response["artifacts"]:
                for artifact in response["artifacts"]:
                    await state_manager.add_message_to_conversation(
                        conversation_id=conversation_id,
                        message={
                            "role": "artifact",
                            "content": artifact["content"],
                            "type": artifact["type"],
                            "agent_id": agent_id,
                            "timestamp": time.time()
                        }
                    )
    
    # Verificar el estado final de la conversación
    final_context = await state_manager.get_conversation(conversation_id)
    
    # Verificar mensajes
    assert hasattr(final_context, "messages"), "La conversación no tiene mensajes"
    assert len(final_context.messages) >= len(available_agents) + 1, "No se guardaron todos los mensajes"
    
    # Verificar intenciones
    assert hasattr(final_context, "intents"), "La conversación no tiene intenciones"
    assert len(final_context.intents) > 0, "No se guardó la intención"
    
    # Verificar agentes involucrados
    assert hasattr(final_context, "agents_involved"), "La conversación no tiene agentes involucrados"
    for agent_id in available_agents:
        assert agent_id in final_context.agents_involved, f"El agente {agent_id} no está registrado como involucrado"
    
    # Limpiar
    await state_manager.delete_conversation(conversation_id)


@pytest.mark.asyncio
async def test_multi_turn_conversation(initialized_system, mock_agents):
    """
    Prueba una conversación de múltiples turnos con el sistema.
    
    Simula un escenario donde:
    1. Se crea una conversación para un usuario
    2. El usuario envía múltiples consultas en secuencia
    3. Cada consulta se procesa completamente
    4. El contexto de la conversación se mantiene y enriquece
    """
    # Obtener los agentes de prueba
    test_agents, _ = mock_agents
    
    # 1. Crear una conversación para un usuario
    user_id = f"multi_turn_test_user_{uuid.uuid4().hex[:8]}"
    context = await state_manager.create_conversation(user_id=user_id)
    conversation_id = context.conversation_id
    
    # Definir las consultas del usuario para la conversación
    user_queries = [
        "Quiero empezar a entrenar para mejorar mi condición física",
        "¿Qué tipo de alimentación debo seguir?",
        "¿Cómo puedo monitorear mi progreso?"
    ]
    
    # Procesar cada consulta en secuencia
    for turn, user_query in enumerate(user_queries):
        # Guardar la consulta del usuario
        await state_manager.add_message_to_conversation(
            conversation_id=conversation_id,
            message={
                "role": "user",
                "content": user_query,
                "timestamp": time.time(),
                "turn": turn + 1
            }
        )
        
        # Analizar la intención
        intents = await intent_analyzer.analyze_intent(
            user_query=user_query,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        # Guardar la intención
        intent_dict = {
            "intent_type": intents[0].intent_type,
            "confidence": intents[0].confidence,
            "agents": intents[0].agents,
            "metadata": intents[0].metadata,
            "turn": turn + 1
        }
        await state_manager.add_intent_to_conversation(
            conversation_id=conversation_id,
            intent=intent_dict
        )
        
        # Identificar agentes apropiados
        recommended_agents = intents[0].agents
        available_agents = [agent for agent in recommended_agents if agent in test_agents]
        
        if not available_agents:
            available_agents = test_agents[:1]  # Usar al menos un agente
        
        # Obtener el contexto actualizado para pasarlo a los agentes
        updated_context = await state_manager.get_conversation(conversation_id)
        
        # Preparar contexto para los agentes
        context_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "messages": updated_context.messages,
            "intents": updated_context.intents if hasattr(updated_context, "intents") else [],
            "current_turn": turn + 1
        }
        
        # Llamar a los agentes
        responses = await a2a_adapter.call_multiple_agents(
            user_input=user_query,
            agent_ids=available_agents,
            context=context_data
        )
        
        # Guardar las respuestas
        for agent_id, response in responses.items():
            if response["status"] == "success":
                await state_manager.add_message_to_conversation(
                    conversation_id=conversation_id,
                    message={
                        "role": "assistant",
                        "content": response["output"],
                        "agent_id": agent_id,
                        "timestamp": time.time(),
                        "turn": turn + 1
                    }
                )
                
                # Guardar artefactos si existen
                if "artifacts" in response and response["artifacts"]:
                    for artifact in response["artifacts"]:
                        await state_manager.add_message_to_conversation(
                            conversation_id=conversation_id,
                            message={
                                "role": "artifact",
                                "content": artifact["content"],
                                "type": artifact["type"],
                                "agent_id": agent_id,
                                "timestamp": time.time(),
                                "turn": turn + 1
                            }
                        )
    
    # Verificar el estado final de la conversación
    final_context = await state_manager.get_conversation(conversation_id)
    
    # Verificar que todos los turnos estén presentes
    messages_by_turn = {}
    for message in final_context.messages:
        turn = message.get("turn", 0)
        if turn not in messages_by_turn:
            messages_by_turn[turn] = []
        messages_by_turn[turn].append(message)
    
    for turn in range(1, len(user_queries) + 1):
        assert turn in messages_by_turn, f"No hay mensajes para el turno {turn}"
        turn_messages = messages_by_turn[turn]
        
        # Verificar que haya al menos un mensaje de usuario y uno de asistente
        user_messages = [m for m in turn_messages if m["role"] == "user"]
        assistant_messages = [m for m in turn_messages if m["role"] == "assistant"]
        
        assert len(user_messages) > 0, f"No hay mensajes de usuario en el turno {turn}"
        assert len(assistant_messages) > 0, f"No hay mensajes de asistente en el turno {turn}"
        
        # Verificar que el contenido del mensaje de usuario coincida con la consulta original
        assert user_messages[0]["content"] == user_queries[turn-1], f"El contenido del mensaje de usuario no coincide en el turno {turn}"
    
    # Verificar intenciones
    intents_by_turn = {}
    for intent in final_context.intents:
        turn = intent.get("turn", 0)
        if turn not in intents_by_turn:
            intents_by_turn[turn] = []
        intents_by_turn[turn].append(intent)
    
    for turn in range(1, len(user_queries) + 1):
        assert turn in intents_by_turn, f"No hay intenciones para el turno {turn}"
    
    # Limpiar
    await state_manager.delete_conversation(conversation_id)


@pytest.mark.asyncio
async def test_error_handling_and_recovery(initialized_system, mock_agents):
    """
    Prueba el manejo de errores y la recuperación del sistema.
    
    Simula escenarios de error y verifica que:
    1. El sistema detecte y maneje adecuadamente los errores
    2. Se proporcionen respuestas alternativas cuando sea necesario
    3. El sistema pueda recuperarse y continuar funcionando
    """
    # Obtener los agentes de prueba
    test_agents, _ = mock_agents
    
    # Crear una conversación
    user_id = f"error_test_user_{uuid.uuid4().hex[:8]}"
    context = await state_manager.create_conversation(user_id=user_id)
    conversation_id = context.conversation_id
    
    # 1. Probar error con un agente inexistente
    non_existent_agent = "non_existent_agent_123"
    
    # Intentar llamar al agente inexistente
    user_query = "Esta consulta debería fallar"
    
    response = await a2a_adapter.call_agent(
        agent_id=non_existent_agent,
        user_input=user_query,
        context={"conversation_id": conversation_id}
    )
    
    # Verificar que se maneje el error
    assert response, "No se recibió respuesta para el agente inexistente"
    assert "status" in response, "La respuesta no tiene campo 'status'"
    assert response["status"] == "error", "El estado de la respuesta no es 'error'"
    
    # 2. Probar recuperación después del error
    # Llamar a un agente válido después del error
    valid_agent = test_agents[0]
    
    valid_response = await a2a_adapter.call_agent(
        agent_id=valid_agent,
        user_input="Esta consulta debería funcionar",
        context={"conversation_id": conversation_id}
    )
    
    # Verificar que el sistema se recupere
    assert valid_response, "No se recibió respuesta del agente válido"
    assert valid_response["status"] == "success", "El estado de la respuesta no es 'success'"
    
    # 3. Probar manejo de errores en el Intent Analyzer
    # Forzar un error usando una consulta vacía
    empty_query = ""
    
    intents = await intent_analyzer.analyze_intent(
        user_query=empty_query,
        conversation_id=conversation_id
    )
    
    # Verificar que se devuelva una intención predeterminada
    assert intents, "No se obtuvieron intenciones para la consulta vacía"
    assert len(intents) > 0, "La lista de intenciones está vacía"
    
    # Verificar que la intención tenga metadatos de error o fallback
    assert "metadata" in intents[0].__dict__, "La intención no tiene metadatos"
    metadata = intents[0].metadata
    assert "fallback" in metadata or "error" in metadata, "No hay indicadores de fallback o error en los metadatos"
    
    # Limpiar
    await state_manager.delete_conversation(conversation_id)


@pytest.mark.asyncio
async def test_system_performance_metrics(initialized_system, mock_agents):
    """
    Prueba las métricas de rendimiento del sistema completo.
    
    Mide y verifica:
    1. Tiempo de respuesta del sistema completo
    2. Uso de memoria (indirectamente a través de estadísticas)
    3. Throughput (operaciones por segundo)
    4. Tasa de errores
    5. Escalabilidad bajo carga moderada
    """
    # Obtener los agentes de prueba
    test_agents, _ = mock_agents
    
    # Parámetros de la prueba
    num_conversations = 5
    queries_per_conversation = 3
    
    # Crear conversaciones
    conversations = []
    for i in range(num_conversations):
        user_id = f"perf_test_user_{i}"
        context = await state_manager.create_conversation(user_id=user_id)
        conversations.append(context)
    
    # Consultas de prueba
    test_queries = [
        "Quiero un plan de entrenamiento para principiantes",
        "Necesito mejorar mi resistencia cardiovascular",
        "¿Cómo puedo preparar comidas saludables?",
        "Quiero aumentar mi masa muscular",
        "¿Cuál es la mejor rutina para perder peso?"
    ]
    
    # Estadísticas
    total_operations = 0
    successful_operations = 0
    failed_operations = 0
    total_time = 0
    
    # Medir tiempo de inicio
    import time
    start_time = time.time()
    
    # Realizar operaciones
    for context in conversations:
        for i in range(queries_per_conversation):
            query_start_time = time.time()
            total_operations += 1
            
            try:
                # Analizar intención
                query = test_queries[i % len(test_queries)]
                intents = await intent_analyzer.analyze_intent(
                    user_query=query,
                    conversation_id=context.conversation_id,
                    user_id=context.user_id
                )
                
                # Guardar intención
                intent_dict = {
                    "intent_type": intents[0].intent_type,
                    "confidence": intents[0].confidence,
                    "agents": intents[0].agents,
                    "metadata": intents[0].metadata
                }
                await state_manager.add_intent_to_conversation(
                    conversation_id=context.conversation_id,
                    intent=intent_dict
                )
                
                # Llamar a un agente
                agent_id = test_agents[i % len(test_agents)]
                response = await a2a_adapter.call_agent(
                    agent_id=agent_id,
                    user_input=query,
                    context={"conversation_id": context.conversation_id}
                )
                
                # Guardar respuesta
                if response["status"] == "success":
                    await state_manager.add_message_to_conversation(
                        conversation_id=context.conversation_id,
                        message={
                            "role": "assistant",
                            "content": response["output"],
                            "agent_id": agent_id,
                            "timestamp": time.time()
                        }
                    )
                    successful_operations += 1
                else:
                    failed_operations += 1
                
            except Exception as e:
                failed_operations += 1
                print(f"Error en operación: {e}")
            
            # Medir tiempo de la operación
            operation_time = time.time() - query_start_time
            total_time += operation_time
    
    # Medir tiempo total
    elapsed_time = time.time() - start_time
    
    # Calcular métricas
    throughput = total_operations / elapsed_time if elapsed_time > 0 else 0
    avg_response_time = total_time / total_operations if total_operations > 0 else 0
    error_rate = failed_operations / total_operations if total_operations > 0 else 0
    
    # Obtener estadísticas de los componentes
    state_manager_stats = await state_manager.get_stats()
    intent_analyzer_stats = await intent_analyzer.get_stats()
    
    # Verificar métricas
    assert throughput > 0.5, f"Throughput ({throughput:.2f} ops/s) por debajo del umbral mínimo"
    assert avg_response_time < 1.0, f"Tiempo de respuesta promedio ({avg_response_time:.3f}s) excede el límite"
    assert error_rate < 0.1, f"Tasa de errores ({error_rate:.2%}) excede el límite máximo"
    
    # Verificar que se hayan registrado operaciones en todos los componentes
    assert state_manager_stats["operations"] > 0, "No se registraron operaciones en el State Manager"
    assert intent_analyzer_stats["total_queries"] > 0, "No se registraron consultas en el Intent Analyzer"
    
    # Limpiar
    for context in conversations:
        await state_manager.delete_conversation(context.conversation_id)


@pytest.mark.asyncio
async def test_extreme_case_handling(initialized_system, mock_agents):
    """
    Prueba el manejo de casos extremos en el sistema.
    
    Verifica que el sistema maneje correctamente:
    1. Consultas muy largas
    2. Consultas vacías o muy cortas
    3. Caracteres especiales y contenido multilíngüe
    4. Múltiples intenciones en una sola consulta
    """
    # Obtener los agentes de prueba
    test_agents, _ = mock_agents
    agent_id = test_agents[0]
    
    # Crear una conversación
    user_id = f"extreme_test_user_{uuid.uuid4().hex[:8]}"
    context = await state_manager.create_conversation(user_id=user_id)
    conversation_id = context.conversation_id
    
    # 1. Consulta muy larga
    long_query = "Necesito un plan de entrenamiento detallado " + "muy completo " * 100 + "para mejorar mi condición física"
    
    # Verificar que se pueda procesar
    long_intents = await intent_analyzer.analyze_intent(
        user_query=long_query,
        conversation_id=conversation_id
    )
    
    assert long_intents, "No se obtuvieron intenciones para la consulta larga"
    
    # 2. Consulta vacía y muy corta
    empty_query = ""
    short_query = "Hola"
    
    empty_intents = await intent_analyzer.analyze_intent(
        user_query=empty_query,
        conversation_id=conversation_id
    )
    
    short_intents = await intent_analyzer.analyze_intent(
        user_query=short_query,
        conversation_id=conversation_id
    )
    
    assert empty_intents, "No se obtuvieron intenciones para la consulta vacía"
    assert short_intents, "No se obtuvieron intenciones para la consulta corta"
    
    # 3. Caracteres especiales y contenido multilíngüe
    special_query = "¿Cómo puedo mejorar mi técnica de natación? 🏊‍♂️ Swimming technique 水泳技術"
    
    special_intents = await intent_analyzer.analyze_intent(
        user_query=special_query,
        conversation_id=conversation_id
    )
    
    assert special_intents, "No se obtuvieron intenciones para la consulta con caracteres especiales"
    
    # Llamar al agente con la consulta especial
    special_response = await a2a_adapter.call_agent(
        agent_id=agent_id,
        user_input=special_query,
        context={"conversation_id": conversation_id}
    )
    
    assert special_response, "No se recibió respuesta para la consulta con caracteres especiales"
    assert special_response["status"] == "success", "El estado de la respuesta no es 'success'"
    
    # 4. Múltiples intenciones en una sola consulta
    multi_intent_query = "Quiero un plan de entrenamiento para correr un maratón y también necesito consejos de nutrición para deportistas"
    
    multi_intents = await intent_analyzer.analyze_intent(
        user_query=multi_intent_query,
        conversation_id=conversation_id
    )
    
    assert multi_intents, "No se obtuvieron intenciones para la consulta con múltiples intenciones"
    
    # Verificar que se llamen a los agentes apropiados
    available_agents = test_agents[:2]  # Usar los primeros dos agentes
    
    multi_responses = await a2a_adapter.call_multiple_agents(
        user_input=multi_intent_query,
        agent_ids=available_agents,
        context={"conversation_id": conversation_id}
    )
    
    assert multi_responses, "No se recibieron respuestas para la consulta con múltiples intenciones"
    assert len(multi_responses) == len(available_agents), "No se recibieron respuestas de todos los agentes"
    
    # Limpiar
    await state_manager.delete_conversation(conversation_id)
