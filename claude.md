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

### Recently Completed (2025-01-25)
- **FASE 2 - Estabilización**
  - ✅ Limpieza de imports no usados (239 archivos actualizados con autoflake)
  - ✅ Corrección de manejo de excepciones - bare except reemplazados con except Exception (12 archivos)
  - ✅ Reemplazo de print() con logging apropiado (11 archivos)

- **FASE 3 - Optimización**
  - ✅ Connection pooling para Redis implementado (core/redis_pool.py)
  - ✅ Circuit breakers para servicios externos (Vertex AI, Supabase) implementados
  - ✅ Límites de tamaño en caché ya implementados con políticas de evicción (LRU, LFU, FIFO, Hybrid)

- **FASE 4 - Calidad**
  - ✅ Type hints agregados a funciones críticas (a2a_agent.py, adk_agent.py)
  - ✅ Validación de entrada mejorada en endpoints (ChatRequest, AgentRunRequest con validators)
  - ✅ Tests para escenarios de error creados (circuit breaker, redis pool, API endpoints)

- **FASE 5 - Features Avanzadas** ✅ (2025-05-24)
  - ✅ Sistema de streaming de respuestas con SSE
  - ✅ Sistema de métricas y analytics con Prometheus/Grafana
  - ✅ Sistema de feedback con análisis de sentimientos

- **FASE 6 - Multimodalidad Completa** ✅ (2025-05-24)
  - ✅ Procesamiento avanzado de imágenes (análisis de postura, OCR)
  - ✅ Sistema de audio/voz con Vertex AI Speech
  - ✅ Generación de contenido visual (gráficos, PDFs, infografías)

- **FASE 7 - Escalabilidad y Distribución** ✅ (2025-01-25)
  - ✅ **7.1 Kubernetes y Microservicios**: Docker, K8s manifests, Istio, auto-scaling
  - ✅ **7.2 Sistema de Colas Distribuidas**: Celery + RabbitMQ con 6 tipos de tareas
  - ✅ **7.3 CDN y Optimización de Assets**: Cloud CDN, compresión, caché avanzado

### In Progress
- Update remaining adapters to BaseAgentAdapter
- Add tests for BaseAgentAdapter
- FASE 8: External Integrations (next major phase)

### Refactorization Complete
All 4 phases of the refactorization plan have been successfully completed:
- ✅ FASE 1 - Estabilización Crítica (2025-05-23)
- ✅ FASE 2 - Estabilización (2025-05-24)
- ✅ FASE 3 - Optimización (2025-05-24)
- ✅ FASE 4 - Calidad (2025-05-24)

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

## 🏗️ Current Architecture Status (Post-Refactorization)

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend/Cliente                       │
└─────────────────────────────────────┘────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI + Auth JWT                       │
│                  [Circuit Breakers Active]                   │
└─────────────────────────────────────┘────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    NGX Orchestrator                          │
│              [Intent Analysis + Routing]                     │
└─────────────────────────────────────┘────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      A2A WebSocket Server                    │
│                   [Optimized Message Broker]                 │
└─────────────────────────────────────┘────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   Specialized Agents      │   │   External Services       │
│   - Training Strategy     │   │   - Vertex AI [CB]        │
│   - Nutrition Architect   │   │   - Supabase [CB]         │
│   - Biometrics Engine     │   │   - Redis [Pool]          │
│   - Motivation Coach      │   │                           │
│   - Progress Tracker      │   │   [CB] = Circuit Breaker  │
│   - Recovery Expert       │   │   [Pool] = Connection Pool│
│   - Security Guardian     │   │                           │
│   - Integration Ops       │   │                           │
│   - Biohacking Innovator  │   │                           │
│   - Client Success        │   │                           │
└───────────────────────────┘   └───────────────────────────┘
```

### Key Improvements Implemented
- **Connection Pooling**: Redis connections are now pooled for efficiency
- **Circuit Breakers**: All external services protected against cascading failures
- **Enhanced Validation**: Pydantic validators on all API endpoints
- **Type Safety**: Type hints added to critical functions
- **Error Handling**: Comprehensive error scenarios tested
- **Clean Code**: 239 files cleaned of unused imports
- **Logging**: Consistent logging throughout the application

## 🚀 Implementation Roadmap - Next Phases

### FASE 5: Advanced Features (1-2 weeks)
#### 5.1 Response Streaming System ✅ (2025-05-24)
- [x] Implement SSE (Server-Sent Events) for real-time responses
- [x] `/stream/chat` endpoint implementation
- [x] JavaScript/React client for SSE consumption (HTML + React component)
- [x] Latency and throughput testing script
- [x] Integration tests for streaming endpoint
- [x] Adapt Orchestrator for incremental response generation ✅ (2025-05-24)

#### 5.2 Metrics and Analytics System ✅ (2025-05-24)
- [x] Prometheus integration for metrics collection
- [x] Grafana dashboards configuration
- [x] Custom metrics: agent usage, response times, circuit breaker states, cache hit rates
- [x] Automated anomaly alerts (4 categorías con 16 reglas)
- [x] Docker Compose para stack de monitoreo
- [x] Documentación completa y ejemplos de uso

#### 5.3 Feedback and Learning System ✅ (2025-05-24)
- [x] Feedback API endpoints (👍/👎, rating, comments, issues, suggestions)
- [x] Success/failure interaction storage in Supabase
- [x] Analytics system with sentiment analysis and NPS
- [x] React component for feedback UI
- [x] Integration tests completos
- [ ] Intent analyzer retraining system (pending - requiere ML pipeline)
- [ ] A/B testing for responses (pending - requiere infraestructura adicional)

### FASE 6: Complete Multimodality (2-3 weeks)
#### 6.1 Advanced Image Processing ✅ (2025-05-24)
- [x] Physical form analysis from photos
- [x] Exercise posture detection
- [x] Visual progress tracking
- [x] OCR for nutritional labels

#### 6.2 Audio/Voice Processing
- [ ] Speech-to-Text with Vertex AI
- [ ] Text-to-Speech for responses
- [ ] Voice tone/emotion analysis
- [ ] Voice commands for workouts

#### 6.3 Visual Content Generation ✅ (2025-05-24)
- [x] Dynamic progress charts - ProgressChartGenerator con 4 tipos de gráficos
- [x] Nutritional plan infographics - NutritionInfographicGenerator
- [x] Exercise demonstration videos (links) - ExerciseVideoLinkGenerator
- [x] Personalized PDF reports - PDFReportGenerator completo
- [x] API router completo con 11 endpoints (/visualization/*)
- [x] Skills de visualización integradas en Progress Tracker
- [x] Tests de integración para todos los componentes
- [x] Demo HTML interactivo completo

### FASE 7: Scalability and Distribution (2-3 weeks)
#### 7.1 Kubernetes and Microservices ✅ (2025-05-25)
- [x] Dockerize all agents - Dockerfile.base y Dockerfiles específicos por agente
- [x] Kubernetes configuration (GKE) - Manifiestos completos en k8s/
- [x] Service mesh with Istio - Gateway, VirtualService y DestinationRules
- [x] Auto-scaling policies - HPA, VPA y métricas personalizadas
- [x] Blue-green deployments - Script k8s-deploy.sh con estrategia completa
- [x] docker-compose.yml para desarrollo local con todos los servicios
- [x] Makefile.k8s con comandos para gestión completa
- [x] ConfigMaps y Secrets organizados
- [x] Health checks y readiness probes configurados
- [x] Pod Disruption Budgets para alta disponibilidad

#### 7.2 Distributed Queue System ✅ (2025-01-25)
- [x] Celery + RabbitMQ/Redis integration - core/celery_app.py con 6 colas prioritarias
- [x] Tasks for: report generation (5 tipos), image processing (5 operaciones), data analysis (6 funciones)
- [x] Queue monitoring dashboard - Flower con autenticación
- [x] Maintenance tasks (8 tareas) y Critical tasks (5 operaciones)
- [x] Docker Compose para desarrollo local
- [x] Kubernetes manifests para workers con auto-scaling

#### 7.3 CDN and Asset Optimization ✅ (2025-01-25)
- [x] Cloud CDN configuration - Google Cloud CDN con backend service
- [x] On-the-fly image optimization - WebP/AVIF automático
- [x] Strategic response caching - 4 estrategias de caché
- [x] Payload compression - Gzip/Brotli middleware
- [x] CDN deployment script - scripts/cdn-deploy.sh
- [x] API endpoints para gestión de CDN

### FASE 8: External Integrations (3-4 weeks)
#### 8.1 Wearables and IoT Devices ✅ (Partially Complete - 2025-01-26)
- [x] WHOOP Integration (OAuth2, recovery, sleep, strain, workouts)
- [x] Apple Watch/Health Integration (webhooks, shortcuts)
- [x] Oura Ring Integration (OAuth2, sleep, readiness, activity, heart rate) ✅ (2025-01-26)
- [ ] Fitbit/Garmin APIs
- [ ] Smart scale integration
- [ ] Heart rate monitors (additional devices)
- [x] Sleep pattern analysis (via WHOOP, Oura, Apple)

#### 8.2 Fitness Platforms ✅ (Partially Complete - 2025-01-26)
- [x] MyFitnessPal for nutrition ✅ (2025-01-26)
  - OAuth-like authentication implementation
  - Daily nutrition tracking and sync
  - Food diary and meal logging
  - Weight tracking
  - Nutrition trends analysis
  - Integration with Precision Nutrition Architect agent
- [ ] Strava for activities
- [x] Google Fit / Apple Health (via wearables integration)
- [ ] Cronometer for detailed tracking

#### 8.3 Communication and Notifications
- [ ] Push notification system
- [ ] WhatsApp Business API integration
- [ ] Personalized email templates
- [ ] SMS for critical reminders

### FASE 9: Advanced AI and Personalization (4-5 weeks)
#### 9.1 Specialized Models
- [ ] Fine-tuning for: nutritional analysis, exercise prescription, injury detection
- [ ] Progress prediction models
- [ ] ML recommendation system

#### 9.2 Deep Personalization
- [ ] Enriched user profiles
- [ ] Tone and style adaptation
- [ ] Self-adjusting plans
- [ ] Churn prediction

#### 9.3 Proactive Assistant
- [ ] Predictive behavior analysis
- [ ] Contextual suggestions
- [ ] Smart alerts
- [ ] Automatic check-ins

### FASE 10: Security and Compliance (2-3 weeks)
#### 10.1 Advanced Security
- [ ] End-to-end encryption
- [ ] Complete audit logs
- [ ] Pentesting and vulnerability analysis
- [ ] 2FA/MFA for users

#### 10.2 Regulatory Compliance
- [ ] HIPAA compliance (USA)
- [ ] GDPR compliance (EU)
- [ ] Data retention policies
- [ ] Right to be forgotten

#### 10.3 Backup and Disaster Recovery
- [ ] Multi-region automatic backups
- [ ] Disaster recovery plan
- [ ] Automatic failover
- [ ] RPO/RTO < 1 hour

## 📊 Success Metrics

### Performance
- Latency P95 < 200ms
- Uptime > 99.9%
- Cache hit rate > 80%

### Scalability
- Support for 10K concurrent users
- Auto-scaling in < 30 seconds
- Cost per user < $0.10/month

### Quality
- Test coverage > 80%
- Zero downtime deployments
- Error rate < 0.1%

### User Experience
- Satisfaction > 4.5/5
- 30-day retention > 60%
- Average session time > 10 min

---

This documentation is designed to help Claude AI understand and work effectively with the NGX Agents project. For specific implementation details, refer to the individual component documentation in the `docs/` directory.

---

## 📅 Development Progress Log

### 2025-01-26 - External Integrations Progress

#### Completed Today:
1. **Oura Ring Integration** ✅
   - Full OAuth2 implementation following WHOOP pattern
   - Sleep, activity, readiness, and heart rate data sync
   - Complete data normalization to NGX format
   - Integration with wearables service

2. **MyFitnessPal Integration** ✅
   - Authentication adapter (username/password based)
   - Daily nutrition data synchronization
   - Meal and food tracking with macronutrients
   - Weight tracking functionality
   - Nutrition trends analysis
   - Full integration with Precision Nutrition Architect agent
   - New agent skills: `sync_nutrition_data` and `analyze_nutrition_trends`

#### Next Session Tasks (Prioritized):
1. **Strava Integration** (Activity Tracking)
   - OAuth2 v3 authentication
   - Activity sync (runs, rides, swims, workouts)
   - Segments and performance metrics
   - Integration with Elite Training Strategist

2. **Smart Scale Integration** (Body Composition)
   - Support for Withings, Fitbit Aria, Garmin Index
   - Body composition metrics (weight, body fat, muscle mass, BMI)
   - Trend analysis and progress tracking
   - Integration with Biometrics Insight Engine

3. **Push Notifications System**
   - Firebase Cloud Messaging (FCM) setup
   - Notification templates for reminders and alerts
   - User preference management
   - Scheduled notifications for meals, workouts, check-ins

4. **WhatsApp Business API**
   - Two-way messaging for coaching
   - Automated updates and reminders
   - Quick replies for logging
   - Media support for progress photos

#### Current Phase Status:
- **FASE 8.1 Wearables**: 60% Complete (3 of 5 major devices integrated)
- **FASE 8.2 Fitness Platforms**: 25% Complete (1 of 4 platforms integrated)
- **FASE 8.3 Communication**: 0% Complete (Next priority) 