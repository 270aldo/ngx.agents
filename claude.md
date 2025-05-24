# NGX Agents - Claude AI Assistant Documentation

## 🎯 Project Overview

NGX Agents is a sophisticated fitness and wellness coaching system that implements a Google ADK-based Agent-to-Agent (A2A) architecture. The system provides personalized assistance through multiple domain-specific agents that communicate via an optimized WebSocket server.

## 🏗️ Architecture

### Core Design Principles
- **Agent-to-Agent (A2A) Communication**: Agents communicate through a central WebSocket server
- **Google ADK Integration**: Built on Google's Agent Development Kit for standardized agent communication
- **Microservices Architecture**: Each agent is a specialized service with specific capabilities
- **Asynchronous Processing**: All agent interactions are asynchronous for optimal performance
- **Distributed State Management**: Redis-based state management for scalability

### Communication Flow
```
User → FastAPI → Orchestrator → Specialized Agents → Orchestrator → User
         ↓           ↓                    ↓                ↑
    JWT Auth    Intent Analysis      A2A Server      Response Synthesis
```

## 🤖 Agent Ecosystem

### Central Coordinator
- **Orchestrator** (`orchestrator/`): Analyzes user intent, routes to specialized agents, synthesizes responses

### Specialized Agents
1. **Elite Training Strategist** (`elite_training_strategist/`): Designs personalized training programs
2. **Precision Nutrition Architect** (`precision_nutrition_architect/`): Creates customized nutrition plans
3. **Biometrics Insight Engine** (`biometrics_insight_engine/`): Analyzes health and biometric data
4. **Motivation Behavior Coach** (`motivation_behavior_coach/`): Provides motivation and behavioral guidance
5. **Progress Tracker** (`progress_tracker/`): Monitors and reports user progress
6. **Recovery Corrective** (`recovery_corrective/`): Specializes in recovery and injury prevention
7. **Security Compliance Guardian** (`security_compliance_guardian/`): Ensures data security and compliance
8. **Systems Integration Ops** (`systems_integration_ops/`): Manages external integrations
9. **Biohacking Innovator** (`biohacking_innovator/`): Explores cutting-edge wellness techniques
10. **Client Success Liaison** (`client_success_liaison/`): Manages client relationships

## 🛠️ Technical Stack

### Core Technologies
- **Python 3.9+**: Primary language
- **FastAPI**: High-performance async web framework
- **Google ADK**: Agent Development Kit for A2A communication
- **WebSockets**: Real-time agent communication
- **Redis**: Distributed caching and state management
- **Supabase**: Database and authentication
- **Google Vertex AI**: AI/ML capabilities
- **Poetry**: Dependency management

### Key Components
- **A2A Server** (`infrastructure/a2a_optimized.py`): Optimized message broker
- **State Manager** (`core/state_manager_optimized.py`): Distributed state management
- **Intent Analyzer** (`core/intent_analyzer_optimized.py`): User intent classification
- **Vertex AI Client** (`clients/vertex_ai/`): Centralized AI client with caching
- **Telemetry** (`core/telemetry.py`): OpenTelemetry-based monitoring

## 📁 Project Structure

```
ngx-agents-refactorizado/
├── agents/                 # Agent implementations
│   ├── base/              # Base classes for agents
│   ├── orchestrator/      # Central orchestrator
│   └── */                 # Specialized agents
├── app/                   # FastAPI application
│   ├── main.py           # Application entry point
│   ├── routers/          # API endpoints
│   └── schemas/          # Pydantic models
├── clients/              # External service clients
│   └── vertex_ai/        # Google Vertex AI client
├── core/                 # Core functionality
│   ├── intent_analyzer_optimized.py
│   ├── state_manager_optimized.py
│   └── telemetry.py
├── infrastructure/       # A2A infrastructure
│   ├── a2a_optimized.py  # Optimized A2A server
│   └── adapters/         # Service adapters
├── tests/               # Test suite
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## 🔑 Key Concepts

### Agent Base Classes
- **BaseAgent**: Extends Google ADK Agent, provides common functionality
- **ADKAgent**: Wrapper for Google ADK integration
- **BaseAgentAdapter**: Standard interface for agent adapters

### Intent Analysis
The system uses embeddings and semantic analysis to classify user intents:
- Training-related queries → Elite Training Strategist
- Nutrition queries → Precision Nutrition Architect
- Health metrics → Biometrics Insight Engine
- General queries → Wellbeing Coach

### State Management
- Session-based conversation history
- User preferences and context
- Agent usage statistics
- Distributed across Redis for scalability

### Multimodal Capabilities
- Vision processing for image analysis
- Document processing for PDFs/files
- Audio transcription support (planned)

## 🚀 Current Development Status

### Completed Migrations (100%)
- A2A Server optimization
- All agent adapters to new architecture
- Multimodal processing implementation
- Base infrastructure refactoring

### Recently Completed (2025-05-23)
- **FASE 1 - Estabilización Crítica**
  - ✅ Error de sintaxis en chaos_testing.py corregido
  - ✅ Cierre de conexiones Redis implementado en StateManager
  - ✅ Configuración CORS segura implementada
  - ✅ Cierre de servicios externos (Vertex AI, Supabase) implementado

### In Progress
- Vertex AI Client optimization (90%)
- State Manager enhancement (95%) - close() method added
- Intent Analyzer improvements (90%)
- Performance testing and optimization

### Pending Refactorization (FASE 2-4)
- **FASE 2 - Estabilización**
  - Limpiar 587 imports no usados
  - Corregir manejo de excepciones (bare except)
  - Reemplazar print() con logging
- **FASE 3 - Optimización**
  - Connection pooling para Redis
  - Circuit breakers para servicios externos
  - Límites de tamaño en caché
- **FASE 4 - Calidad**
  - Type hints completos
  - Validación de entrada en endpoints
  - Tests para escenarios de error

## 💻 Development Guidelines

### Code Standards
- Type hints for all functions
- Comprehensive docstrings
- Async/await for all I/O operations
- Error handling with proper logging
- Unit tests for all new features

### Agent Development
1. Inherit from `BaseAgent` or `ADKAgent`
2. Implement `_run_async_impl` method
3. Define agent capabilities and skills
4. Create corresponding adapter in `infrastructure/adapters/`
5. Add integration tests

### API Development
1. Define Pydantic schemas in `app/schemas/`
2. Create router in `app/routers/`
3. Implement proper authentication
4. Add OpenAPI documentation
5. Include telemetry spans

## 🧪 Testing Strategy

### Test Categories
- **Unit Tests** (`tests/unit/`): Component isolation
- **Integration Tests** (`tests/integration/`): Service integration
- **Agent Tests** (`tests/agents/`): Agent-specific behavior
- **E2E Tests**: Full system validation

### Mock System
- Supabase mock for database operations
- Google ADK mock for agent testing
- Vertex AI mock for AI operations
- Redis mock for state management

## 🔧 Environment Configuration

### Required Environment Variables
```env
# API Server
HOST=0.0.0.0
PORT=8000

# A2A Server
A2A_HOST=0.0.0.0
A2A_PORT=9000

# Authentication
JWT_SECRET=your-secret
JWT_ALGORITHM=HS256

# Supabase
SUPABASE_URL=https://project.supabase.co
SUPABASE_ANON_KEY=your-key

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
VERTEX_PROJECT_ID=your-project
VERTEX_LOCATION=us-central1

# Redis (optional)
USE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 🚦 Development Workflow

### Starting Development Environment
```bash
# Install dependencies
make setup

# Start all services
./scripts/run_dev.sh

# Or start individually:
# A2A Server
python -m infrastructure.a2a_server

# API Server
make dev
```

### Running Tests
```bash
# All tests
make test

# Specific categories
make test-unit
make test-integration
make test-agents

# With coverage
make test-cov
```

### Code Quality
```bash
# Format code
make format

# Run linters
make lint

# Type checking
make type-check
```

## 📊 Performance Considerations

### Optimization Strategies
- Connection pooling for Vertex AI
- Redis caching with TTL
- Parallel agent execution
- Request prioritization
- Circuit breaker patterns

### Monitoring
- OpenTelemetry integration
- Custom metrics for agent performance
- Health checks for all services
- Distributed tracing

## 🔐 Security Features

- JWT-based authentication
- Role-based access control
- Data encryption at rest
- Secure agent communication
- Compliance monitoring

## 📝 Important Notes for Development

1. **Always use async/await** for I/O operations
2. **Follow the adapter pattern** for service integration
3. **Implement proper error handling** with meaningful messages
4. **Add telemetry spans** for observability
5. **Write tests** for all new functionality
6. **Update documentation** when adding features
7. **Use type hints** for better code clarity
8. **Follow the established patterns** in the codebase

## 🎯 Quick Reference

### Common Tasks

**Add a new agent:**
1. Create directory in `agents/`
2. Inherit from `BaseAgent`
3. Implement agent logic
4. Create adapter in `infrastructure/adapters/`
5. Register in orchestrator's intent map

**Add an API endpoint:**
1. Define schema in `app/schemas/`
2. Create router in `app/routers/`
3. Add authentication if needed
4. Include in `app/main.py`
5. Add tests

**Debug agent communication:**
1. Check A2A server logs
2. Verify agent registration
3. Test with integration scripts
4. Use telemetry traces

### Troubleshooting

**Agent not responding:**
- Check A2A server is running
- Verify agent is registered
- Check intent mapping in orchestrator
- Review adapter implementation

**Performance issues:**
- Check Redis cache hit rates
- Monitor Vertex AI latency
- Review parallel execution
- Check for blocking I/O

**Test failures:**
- Ensure mocks are properly configured
- Check environment variables
- Verify test fixtures
- Review async test setup

## 🤝 Contribution Guidelines

1. Create feature branch from `main`
2. Follow existing code patterns
3. Add comprehensive tests
4. Update documentation
5. Ensure all tests pass
6. Submit PR with clear description

---

This documentation is designed to help Claude AI understand and work effectively with the NGX Agents project. For specific implementation details, refer to the individual component documentation in the `docs/` directory. 