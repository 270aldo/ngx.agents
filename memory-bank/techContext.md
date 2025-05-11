# NGX Agents Technical Context

## Technologies Used

### Core Technologies

#### 1. Python Ecosystem
- **Python 3.10+**: Primary development language
- **FastAPI**: High-performance web framework for API endpoints
- **Asyncio**: Asynchronous I/O library for non-blocking operations
- **Pydantic**: Data validation and settings management
- **pytest**: Testing framework for unit and integration tests

#### 2. Google Cloud Platform
- **Vertex AI**: Core AI service for LLMs, embeddings, and multimodal processing
  - **Gemini models**: For advanced text generation and reasoning
  - **Embedding models**: For semantic representations and search
  - **Vision models**: For image analysis and recognition
  - **Document AI**: For document processing
- **Google Cloud Storage**: For asset storage and data persistence
- **Speech-to-Text/Text-to-Speech**: For voice processing
- **Google ADK**: Agent Development Kit for standardized agent interfaces

#### 3. Database and Storage
- **Supabase**: PostgreSQL-based backend for data persistence
  - **Real-time subscriptions**: For state synchronization
  - **PostgreSQL functions**: For complex data processing
  - **Row-level security**: For data protection
- **Redis**: For in-memory caching (planned)
- **Vector storage**: For embedding-based retrieval

#### 4. DevOps and Infrastructure
- **Docker**: Containerization for deployment consistency
- **Kubernetes**: Container orchestration for production environments
- **Terraform**: Infrastructure as Code for cloud resources
- **GitHub Actions**: CI/CD pipeline automation
- **Monitoring stack**: Prometheus, Grafana, and custom telemetry

### Supporting Libraries and Tools

- **LangChain**: Framework for LLM application development
- **Tenacity**: For retry logic and resilience patterns
- **HTTPX**: Asynchronous HTTP client
- **Uvicorn**: ASGI server for FastAPI
- **Poetry**: Dependency management
- **Black/isort/Ruff**: Code formatting and linting
- **Pre-commit hooks**: Automated code quality checks

## Development Setup

### Environment Setup

```bash
# Clone the repository
git clone git@github.com:company/ngx-agents.git
cd ngx-agents

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with Poetry
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials and configuration

# Run development server
./scripts/run_dev.sh
```

### Component Environment Setup

The project uses a component-based development approach where each major component can be developed and tested independently:

```bash
# Set up component-specific environments
./setup_component_envs.sh

# Activate a specific component environment
source activate_component_env.sh core  # Options: core, agents, clients, tools, app
```

### Testing Setup

```bash
# Run all tests
./run_tests.sh

# Run specific test categories
pytest tests/unit
pytest tests/integration
pytest tests/test_agents

# Run compatibility tests for component interfaces
./run_compatibility_tests.sh
```

## Technical Constraints

### Performance Constraints

1. **Latency Requirements**:
   - End-to-end response time < 3 seconds for text-only queries
   - End-to-end response time < 6 seconds for multimodal queries
   - A2A message routing latency < 50ms per hop

2. **Throughput Requirements**:
   - Support for 100+ concurrent users per instance
   - Ability to handle 1000+ messages per second in the A2A server
   - State manager must support 500+ state updates per second

3. **Resource Limitations**:
   - Memory usage < 2GB per agent instance
   - CPU usage optimized for cost-efficiency in cloud deployment
   - API quota management for Vertex AI services

### Security and Compliance Constraints

1. **Data Protection**:
   - PII (Personally Identifiable Information) handling compliance
   - Health data protection according to relevant regulations
   - Data encryption requirements for sensitive information

2. **Authentication and Authorization**:
   - JWT-based authentication for all API endpoints
   - Role-based access control for administrative functions
   - Secure credential management for service accounts

3. **Audit and Compliance**:
   - Comprehensive logging for security audit trails
   - Regular security scanning and vulnerability assessment
   - Compliance with fitness industry standards

### Integration Constraints

1. **External API Limitations**:
   - Vertex AI rate limits and quotas
   - Supabase connection and query limits
   - Third-party fitness API integration requirements

2. **Deployment Constraints**:
   - Kubernetes-based deployment for production
   - Multi-environment support (dev, staging, production)
   - Zero-downtime deployment requirements

## Dependencies and APIs

### Critical Dependencies

1. **Google Vertex AI**:
   - Text generation models (Gemini)
   - Embedding models
   - Multimodal models for image and audio processing
   - DocumentAI processors

2. **Supabase**:
   - PostgreSQL database
   - Authentication services
   - Real-time subscriptions
   - Storage capabilities

3. **Google ADK**:
   - Agent interfaces and protocols
   - Toolkit infrastructure
   - Communication standards

### Internal Dependencies

1. **Core Components**:
   - `StateManager`: Conversation state persistence
   - `IntentAnalyzer`: User intent classification
   - `VertexAIClient`: AI service access
   - `A2A Server`: Inter-agent communication

2. **Agent Dependencies**:
   - Agent base classes and interfaces
   - Shared utilities and helpers
   - Common data models and schemas

### External APIs

1. **Fitness and Nutrition APIs**:
   - Nutritional database integrations
   - Exercise catalog services
   - Activity tracking integrations

2. **Health Data APIs**:
   - Biometric data providers
   - Health record integrations
   - Medical reference databases

## Tool Usage Patterns

### Development Workflows

1. **Feature Development**:
   ```
   Create branch → Implement feature → Write tests → PR review → CI checks → Merge
   ```

2. **Bug Fixing**:
   ```
   Reproduce issue → Write failing test → Fix implementation → Verify tests pass → PR review
   ```

3. **Refactoring**:
   ```
   Identify targets → Write comprehensive tests → Implement changes → Verify tests → PR review
   ```

### Code Organization Patterns

1. **Agent Implementation Pattern**:
   ```python
   # agents/specialized_agent/agent.py
   from adk.agent import Agent
   from core.skill import Skill
   
   class SpecializedSkill(Skill):
       # Skill implementation
       
   class SpecializedAgent(Agent):
       # Agent implementation with skills
   ```

2. **Adapter Pattern Usage**:
   ```python
   # infrastructure/component_adapter.py
   class ComponentAdapter:
       def __init__(self, legacy_component, new_component):
           self.legacy = legacy_component
           self.new = new_component
           
       async def operation(self, *args, **kwargs):
           # Adaptation logic
   ```

3. **Repository Pattern Usage**:
   ```python
   # clients/repository.py
   class Repository:
       def __init__(self, client):
           self.client = client
           
       async def find_one(self, id):
           # Implementation
           
       async def find_many(self, criteria):
           # Implementation
   ```

### Testing Patterns

1. **Unit Testing**:
   ```python
   # tests/unit/test_component.py
   def test_component_function():
       # Arrange
       component = Component()
       # Act
       result = component.function()
       # Assert
       assert result == expected
   ```

2. **Integration Testing**:
   ```python
   # tests/integration/test_system.py
   async def test_system_flow():
       # Set up integration test environment
       # Execute complex multi-component flow
       # Verify end-to-end behavior
   ```

3. **Mock Usage**:
   ```python
   # tests/test_agent.py
   def test_agent_with_mock_services(mocker):
       # Mock dependencies
       mock_state_manager = mocker.patch('core.state_manager.StateManager')
       # Test with controlled dependencies
   ```

## Deployment Architecture

### Infrastructure Components

1. **Kubernetes Cluster**:
   - Agent deployments as stateless services
   - A2A server deployment with high availability
   - Ingress controllers for API routing
   - Autoscaling configurations

2. **Database Infrastructure**:
   - Supabase project configuration
   - Connection pooling
   - Backup and disaster recovery

3. **Monitoring and Observability**:
   - Prometheus metrics collection
   - Grafana dashboards
   - Custom telemetry integration
   - Logging aggregation

### Deployment Process

1. **CI/CD Pipeline**:
   ```
   Code commit → Automated tests → Container build → Security scan → Staging deployment → Production deployment
   ```

2. **Environment Configuration**:
   - Environment-specific configuration via Kubernetes ConfigMaps and Secrets
   - Feature flags for gradual rollout
   - A/B testing infrastructure

3. **Scaling Strategy**:
   - Horizontal pod autoscaling based on CPU/memory metrics
   - Custom metrics for business-specific scaling
   - Scheduled scaling for predictable load patterns
