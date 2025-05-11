"""
Pruebas unitarias para el agente EliteTrainingStrategist.

Este módulo contiene pruebas para verificar el funcionamiento
del agente EliteTrainingStrategist.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from agents.elite_training_strategist import EliteTrainingStrategist

# Mock para GeminiClient
class MockGeminiClient:
    async def generate_response(self, user_input, context=None, temperature=0.7):
        return f"Respuesta simulada para: {user_input}"
    
    async def generate_structured_output(self, prompt):
        return {
            "objective": "Plan de entrenamiento personalizado",
            "duration": "4-6 semanas",
            "frequency": "3-4 días por semana",
            "sessions": [
                {
                    "name": "Sesión de ejemplo",
                    "exercises": [
                        {
                            "name": "Ejemplo de ejercicio",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": "60-90 segundos"
                        }
                    ]
                }
            ]
        }

# Mock para SupabaseClient
class MockSupabaseClient:
    def get_user_profile(self, user_id):
        return {
            "name": "Usuario de prueba",
            "age": 30,
            "experience_level": "intermedio",
            "goals": "Ganar masa muscular",
            "limitations": "Ninguna"
        }
    
    def log_conversation_message(self, user_id, role, message):
        return True

# Mock para MCPToolkit y MCPClient
class MockMCPToolkit:
    pass

class MockMCPClient:
    pass

@pytest.fixture
def mock_dependencies():
    """Fixture para simular las dependencias del agente."""
    # Los parches deben apuntar a donde los nombres son buscados,
    # que es dentro del módulo 'agent.py' de 'elite_training_strategist'.
    with patch("agents.elite_training_strategist.agent.GeminiClient", return_value=MockGeminiClient()), \
         patch("agents.elite_training_strategist.agent.SupabaseClient", return_value=MockSupabaseClient()), \
         patch("agents.elite_training_strategist.agent.MCPToolkit", return_value=MockMCPToolkit()), \
         patch("agents.elite_training_strategist.agent.MCPClient", return_value=MockMCPClient()):
        yield

@pytest.mark.asyncio
async def test_elite_training_strategist_initialization(mock_dependencies):
    """Prueba la inicialización del agente EliteTrainingStrategist y el procesamiento de skills."""
    agent = EliteTrainingStrategist()
    
    # Verificar atributos básicos
    assert agent.agent_id == "elite_training_strategist"
    assert agent.name == "Elite Training Strategist"
    expected_capabilities = [
        "generate_training_plan", 
        "adapt_training_program", 
        "analyze_performance_data", 
        "set_training_intensity_volume", 
        "prescribe_exercise_routines"
    ]
    assert all(cap in agent.capabilities for cap in expected_capabilities)
    assert len(agent.capabilities) == len(expected_capabilities)

    # Verificar que self.skills (la lista de objetos Skill) se haya definido
    assert hasattr(agent, 'skills')
    assert isinstance(agent.skills, list)
    assert len(agent.skills) == 5 # EliteTrainingStrategist define 5 skills

    # Verificar los atributos poblados por ADKAgent._initialize_and_prepare_skills
    # Estos atributos son utilizados internamente por ADKAgent y pasados a A2AAgent

    # 1. Verificar agent.google_adk_tools (lista de callables para Google ADK)
    # Este atributo es usado por ADKAgent para pasarlo como 'tools' en kwargs a BaseAgent de Google ADK.
    # Accedemos a él a través de lo que se pasó a BaseAgent de Google (simulado por A2AAgent en nuestra jerarquía)
    # ADKAgent.__init__ hace: if processed_google_adk_tools: kwargs['tools'] = processed_google_adk_tools
    # Y luego A2AAgent (como superclase directa de ADKAgent) recibe **kwargs.
    # Sin embargo, el BaseAgent original de Google es el que finalmente lo usaría.
    # Para nuestros propósitos de prueba, podemos verificar que ADKAgent preparó estos tools.
    # Podríamos necesitar un mock para el BaseAgent de Google o acceder a un atributo intermedio si ADKAgent lo guarda.
    # Por ahora, asumimos que ADKAgent no guarda 'processed_google_adk_tools' directamente en self.
    # En su lugar, lo pasa en kwargs a su superclase. Es difícil de testear directamente sin más mocks.
    # Vamos a enfocarnos en self.a2a_skills que SÍ es un atributo de A2AAgent (super de ADKAgent).

    # 2. Verificar agent.a2a_skills (lista de diccionarios para A2A cards, poblado por ADKAgent)
    # ADKAgent._initialize_and_prepare_skills retorna 'processed_a2a_skills_for_card'
    # y ADKAgent.__init__ pasa esto como 'skills' a A2AAgent.__init__,
    # donde se almacena en self.a2a_skills.
    assert hasattr(agent, 'a2a_skills')
    assert isinstance(agent.a2a_skills, list)
    assert len(agent.a2a_skills) == len(agent.skills)

    for skill_object, a2a_skill_def in zip(agent.skills, agent.a2a_skills):
        assert a2a_skill_def["name"] == skill_object.name.replace('_', ' ').title() # ADKAgent capitaliza y reemplaza guiones bajos
        assert a2a_skill_def["description"] == skill_object.description
        # ADKAgent usa skill_object.name para el skill_id en la definición de A2A skill.
        assert a2a_skill_def["skill_id"] == skill_object.name 

        # Verificar inputModes y outputModes (JSON Schemas)
        if skill_object.input_schema:
            assert "inputModes" in a2a_skill_def
            assert isinstance(a2a_skill_def["inputModes"], list)
            assert len(a2a_skill_def["inputModes"]) == 1
            input_mode = a2a_skill_def["inputModes"][0]
            assert input_mode["format"] == "json"
            assert "schema" in input_mode
            # Comprobar que el esquema no esté vacío y tenga 'properties' o 'type'
            assert isinstance(input_mode["schema"], dict)
            assert bool(input_mode["schema"]), f"Input schema for {skill_object.name} is empty"
            # Podríamos hacer una validación más profunda del schema si fuera necesario
            # Por ejemplo, compararlo con skill_object.input_schema.model_json_schema()
        else:
            assert "inputModes" not in a2a_skill_def

        if skill_object.output_schema:
            assert "outputModes" in a2a_skill_def
            assert isinstance(a2a_skill_def["outputModes"], list)
            assert len(a2a_skill_def["outputModes"]) == 1
            output_mode = a2a_skill_def["outputModes"][0]
            assert output_mode["format"] == "json"
            assert "schema" in output_mode
            assert isinstance(output_mode["schema"], dict)
            assert bool(output_mode["schema"]), f"Output schema for {skill_object.name} is empty"
        else:
            assert "outputModes" not in a2a_skill_def

    # 3. Verificar skill_names_for_card (si ADKAgent lo guarda directamente)
    # ADKAgent._initialize_and_prepare_skills retorna 'skill_names' que se usa para 'final_capabilities'.
    # 'final_capabilities' se pasa a A2AAgent.__init__ como 'capabilities'.
    # A2AAgent guarda esto en self.capabilities.
    assert hasattr(agent, 'capabilities') # Esto viene de A2AAgent
    assert isinstance(agent.capabilities, list)
    # Los nombres en capabilities deben coincidir con los nombres capitalizados de las skills
    expected_card_names = [s.name.replace('_', ' ').title() for s in agent.skills]
    # No, ADKAgent usa las capabilities explícitas si se proveen.
    # EliteTrainingStrategist las provee, así que agent.capabilities viene de ahí.
    # Ya lo verificamos al inicio de la prueba.

@pytest.mark.asyncio
async def test_run_method_success(mock_dependencies):
    """Prueba que el método run() funciona correctamente."""
    agent = EliteTrainingStrategist()
    
    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()
    
    # Ejecutar el método run
    result = await agent.run("Necesito un plan de entrenamiento para ganar masa muscular", "test_user_123")
    
    # Verificar el resultado
    assert result["status"] == "success"
    assert "Respuesta simulada para:" in result["response"]
    assert result["error"] is None
    assert result["confidence"] > 0
    assert result["agent_id"] == "elite_training_strategist"
    assert "elite_training" in result["metadata"]["capabilities_used"]

@pytest.mark.asyncio
async def test_run_method_with_error(mock_dependencies):
    """Prueba que el método run() maneja correctamente los errores."""
    agent = EliteTrainingStrategist()
    
    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()
    
    # Simular un error en generate_response
    with patch.object(MockGeminiClient, "generate_response", side_effect=Exception("Error simulado")):
        # Ejecutar el método run
        result = await agent.run("Necesito un plan de entrenamiento", "test_user_123")
        
        # Verificar el resultado
        assert result["status"] == "error"
        assert "Error simulado" in result["error"]
        assert result["confidence"] == 0.0
        assert result["agent_id"] == "elite_training_strategist"

@pytest.mark.asyncio
async def test_generate_training_plan(mock_dependencies):
    """Prueba la generación de un plan de entrenamiento."""
    agent = EliteTrainingStrategist()
    
    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()
    
    # Ejecutar el método _generate_training_plan
    result = await agent._generate_training_plan("Necesito un plan de entrenamiento", None)
    
    # Verificar el resultado
    assert "objective" in result
    assert "duration" in result
    assert "frequency" in result
    assert "sessions" in result
    assert len(result["sessions"]) > 0

@pytest.mark.asyncio
async def test_prepare_context(mock_dependencies):
    """Prueba la preparación del contexto para la generación de respuesta."""
    agent = EliteTrainingStrategist()
    
    user_input_example = "Quiero un plan para mejorar mi resistencia en carrera de 10km."
    user_profile_example = {
        "name": "Alex Corredor", 
        "age": 32,
        "experience_level": "avanzado",
        "goals": "Correr 10km en menos de 40 minutos",
        "program_type": "PRIME", # Para verificar _extract_profile_details
        "injury_history": "Tendinitis rotuliana hace 1 año, ya recuperado."
    }
    context_input_example = {
        "user_id": "user_alex_123", # Debería ser filtrado
        "session_id": "session_xyz_789", # Debería ser filtrado
        "last_activity": "Carrera de 5km ayer, ritmo suave.",
        "preferred_training_days": ["Lunes", "Miércoles", "Viernes"],
        "very_long_key_to_be_ignored_hopefully": "x" * 300 # Debería ser filtrado por longitud
    }

    # Escenario 1: Con perfil de usuario y contexto adicional
    prepared_context_full = agent._prepare_context(
        user_input_example, 
        user_profile_example,
        context_input_example
    )
    
    # Aserciones para el escenario 1
    assert "Eres EliteTrainingStrategist" in prepared_context_full
    assert "Información del Atleta:" in prepared_context_full
    assert "Alex Corredor" in prepared_context_full
    assert "Edad: 32" in prepared_context_full
    assert "Experiencia: avanzado" in prepared_context_full
    assert "Objetivos: Correr 10km en menos de 40 minutos" in prepared_context_full
    assert "Programa: PRIME" in prepared_context_full # Verificamos que _get_program_type_from_profile funciona
    assert "Tendinitis rotuliana" in prepared_context_full
    
    assert "Contexto Adicional Relevante:" in prepared_context_full
    assert "last_activity: Carrera de 5km ayer, ritmo suave." in prepared_context_full
    assert "preferred_training_days: [" in prepared_context_full # Chequeo flexible de la lista
    
    assert "user_id" not in prepared_context_full
    assert "session_id" not in prepared_context_full
    assert "very_long_key_to_be_ignored_hopefully" not in prepared_context_full

    assert f"Solicitud Específica del Usuario:\n{user_input_example}" in prepared_context_full

    # Escenario 2: Sin perfil de usuario y sin contexto adicional
    prepared_context_minimal = agent._prepare_context(
        user_input_example,
        None, 
        {}
    )
    assert "Eres EliteTrainingStrategist" in prepared_context_minimal
    assert "Información del Atleta: No disponible." in prepared_context_minimal
    assert "Contexto Adicional Relevante:" not in prepared_context_minimal
    assert f"Solicitud Específica del Usuario:\n{user_input_example}" in prepared_context_minimal

    # Escenario 3: Con perfil de usuario pero contexto adicional vacío
    prepared_context_profile_only = agent._prepare_context(
        user_input_example,
        user_profile_example,
        {}
    )
    assert "Alex Corredor" in prepared_context_profile_only
    assert "Contexto Adicional Relevante:" not in prepared_context_profile_only
    assert f"Solicitud Específica del Usuario:\n{user_input_example}" in prepared_context_profile_only

    # Escenario 4: Sin perfil de usuario pero con contexto adicional
    prepared_context_context_only = agent._prepare_context(
        user_input_example,
        None,
        context_input_example
    )
    assert "Información del Atleta: No disponible." in prepared_context_context_only
    assert "last_activity: Carrera de 5km ayer, ritmo suave." in prepared_context_context_only
    assert f"Solicitud Específica del Usuario:\n{user_input_example}" in prepared_context_context_only

    print("\nContexto Preparado (Completo):\n", prepared_context_full)
    print("\nContexto Preparado (Mínimo):\n", prepared_context_minimal)
