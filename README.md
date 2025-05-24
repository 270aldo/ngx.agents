# NGX Agents - Sistema de Agentes Inteligentes para Fitness y Nutrición

Sistema avanzado de agentes especializados basado en la arquitectura Agent-to-Agent (A2A) de Google ADK para proporcionar asistencia personalizada en entrenamiento, nutrición y bienestar.

## 🚀 Estado Actual del Proyecto

### Resumen General
NGX Agents es un sistema de inteligencia artificial multi-agente que implementa el protocolo A2A de Google para coordinar agentes especializados en diferentes aspectos del fitness y bienestar. El proyecto está en fase de optimización final con la mayoría de componentes completados.

### Componentes Principales

#### 1. **Arquitectura A2A (Agent-to-Agent)**
- ✅ **Estado**: Implementación completa (100%)
- **Servidor A2A optimizado** con características enterprise:
  - Circuit breakers para prevenir fallos en cascada
  - Colas de mensajes con priorización (CRITICAL, HIGH, NORMAL, LOW)
  - Comunicación asíncrona WebSocket y HTTP
  - Telemetría y métricas integradas
  - Sistema de reintentos y timeouts configurables

#### 2. **Google ADK (Agent Development Kit)**
- ✅ **Estado**: Implementado con fallback inteligente
- Utiliza la biblioteca oficial `google-adk` v0.1.0
- Sistema de fallback a stubs locales cuando ADK no está disponible
- Implementación de Agent y Toolkit siguiendo el estándar de Google

#### 3. **Agentes Especializados** (11 agentes - 100% implementados)
1. **Orchestrator**: Coordinador central que analiza intenciones y distribuye tareas
2. **Elite Training Strategist**: Diseña programas de entrenamiento personalizados
3. **Precision Nutrition Architect**: Crea planes nutricionales adaptados
4. **Biometrics Insight Engine**: Analiza datos biométricos y de salud
5. **Motivation Behavior Coach**: Proporciona apoyo motivacional y conductual
6. **Progress Tracker**: Monitorea y reporta el progreso del usuario
7. **Recovery Corrective**: Especialista en recuperación y prevención de lesiones
8. **Security Compliance Guardian**: Asegura privacidad y cumplimiento normativo
9. **Systems Integration Ops**: Gestiona integraciones con sistemas externos
10. **Biohacking Innovator**: Explora técnicas avanzadas de optimización
11. **Client Success Liaison**: Gestiona la satisfacción del cliente

#### 4. **MCP Tools (Model Context Protocol)**
- ⚠️ **Estado**: Implementación básica (necesita desarrollo)
- Servidores MCP configurados:
  - Databutton (almacenamiento y visualización)
  - Supabase (base de datos y autenticación)
  - 21st Magic (componentes UI)
  - GitHub (gestión de código)
  - Sequential Thinking (razonamiento estructurado)
  - Think (razonamiento avanzado)
- **Nota**: Actualmente devuelve respuestas simuladas, requiere implementación completa

## 🛠️ Stack Tecnológico

### Backend
- **Python 3.9+** - Lenguaje principal
- **FastAPI** - Framework web asíncrono
- **Poetry** - Gestión de dependencias
- **WebSockets** - Comunicación en tiempo real
- **Redis** - Caché y gestión de estado distribuido

### IA y Machine Learning
- **Google Vertex AI** - Modelos de lenguaje y embeddings
- **Google Gemini** - Generación de texto avanzada
- **OpenAI GPT** - Modelos alternativos (opcional)

### Base de Datos y Autenticación
- **Supabase** - Base de datos PostgreSQL y autenticación
- **JWT** - Tokens de autenticación (migrando a Supabase Auth)

### Infraestructura y DevOps
- **Docker** - Contenedorización
- **Kubernetes** - Orquestación de contenedores
- **Terraform** - Infraestructura como código
- **Google Cloud Platform** - Plataforma cloud principal
- **GitHub Actions** - CI/CD

### Observabilidad
- **OpenTelemetry** - Telemetría y trazas distribuidas
- **Prometheus** - Métricas
- **Grafana** - Visualización

## ⚠️ Problemas Identificados y Soluciones

### 1. Error de Configuración de Variables de Entorno
**Problema**: ValidationError de Pydantic por variables de entorno no definidas en el modelo Settings.

**Solución aplicada**: 
```python
class Config:
    extra = "ignore"  # Agregado para ignorar campos extra
```

**Acción requerida**: Crear archivo `.env` basándose en `.env.example`:
```bash
cp .env.example .env
# Editar .env con tus credenciales reales
```

### 2. MCP Tools en Estado Preliminar
**Problema**: La integración con MCP solo devuelve respuestas simuladas.

**Solución propuesta**: Implementar clientes reales para cada servidor MCP en `tools/mcp_toolkit.py`.

### 3. Falta de Archivo .env
**Problema**: El proyecto requiere variables de entorno que no están configuradas.

**Solución**: Crear `.env` con todas las variables necesarias (ver sección Configuración).

## 📋 Requisitos

- Python 3.9 o superior
- Poetry (gestor de dependencias)
- Redis (para caché, opcional en desarrollo)
- Cuenta en Supabase (para base de datos)
- Credenciales de Google Cloud (para Vertex AI)

## 🚀 Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd ngx-agents-refactorizado

# 2. Instalar Poetry si no está instalado
curl -sSL https://install.python-poetry.org | python3 -

# 3. Instalar dependencias
poetry install --with dev,test

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Activar el entorno virtual
poetry shell
```

## 🏃‍♂️ Ejecución

### Desarrollo Completo (Recomendado)
```bash
# Inicia servidor A2A, agentes y API
./scripts/run_dev.sh
```

Este comando inicia:
1. Servidor A2A (puerto 9000)
2. Agentes prioritarios
3. API FastAPI (puerto 8000)

### Solo API
```bash
make dev
# o: poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Solo Servidor A2A
```bash
python -m infrastructure.a2a_server
```

## 🧪 Pruebas

```bash
# Todas las pruebas
make test

# Por categoría
make test-unit        # Pruebas unitarias
make test-integration # Pruebas de integración
make test-agents      # Pruebas de agentes

# Con cobertura
make test-cov         # Cobertura básica
make test-cov-html    # Informe HTML detallado
```

## 📁 Estructura del Proyecto

```
ngx-agents-refactorizado/
├── agents/              # Implementación de los 11 agentes especializados
│   ├── base/            # Clases base ADKAgent y A2AAgent
│   ├── orchestrator/    # Agente coordinador principal
│   └── */               # Demás agentes especializados
├── app/                 # API FastAPI
│   ├── routers/         # Endpoints REST
│   └── schemas/         # Esquemas Pydantic
├── clients/             # Clientes para servicios externos
│   ├── vertex_ai/       # Cliente optimizado para Vertex AI
│   ├── gemini_client.py # Cliente para Gemini
│   └── supabase_client.py # Cliente para Supabase
├── core/                # Funcionalidades centrales
│   ├── state_manager_optimized.py # Gestión de estado distribuido
│   ├── intent_analyzer.py # Análisis de intenciones
│   └── telemetry.py     # Sistema de telemetría
├── infrastructure/      # Infraestructura A2A
│   ├── a2a_optimized.py # Servidor A2A optimizado
│   └── adapters/        # Adaptadores para cada agente
├── tools/               # Herramientas y utilidades
│   ├── mcp_client.py    # Cliente MCP
│   └── mcp_toolkit.py   # Toolkit MCP
├── tests/               # Suite completa de pruebas
│   ├── unit/            # Pruebas unitarias
│   ├── integration/     # Pruebas de integración
│   └── mocks/           # Mocks para pruebas
├── terraform/           # Infraestructura como código
├── kubernetes/          # Configuración K8s
└── docs/                # Documentación detallada
```

## 🔧 Configuración de Variables de Entorno

Variables críticas que deben configurarse en `.env`:

```env
# API y Servidor
HOST=0.0.0.0
PORT=8000
DEBUG=false

# A2A
A2A_HOST=0.0.0.0
A2A_PORT=9000
A2A_SERVER_URL=ws://localhost:9000

# Supabase (Requerido)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-clave-anonima

# Google AI (Requerido para agentes)
GEMINI_API_KEY=tu-api-key
VERTEX_PROJECT_ID=tu-proyecto-id
VERTEX_LOCATION=us-central1

# Redis (Opcional en desarrollo)
USE_REDIS_CACHE=false

# MCP (Opcional)
MCP_BASE_URL=http://localhost:8080
MCP_API_KEY=tu-mcp-api-key
```

## 📊 Estado de Migración y Optimización

| Componente | Estado | Progreso |
|-----------|--------|----------|
| Servidor A2A | ✅ Completado | 100% |
| Adaptadores de Agentes | ✅ Completado | 100% |
| Cliente Vertex AI | 🔄 En progreso | 90% |
| State Manager | 🔄 En progreso | 90% |
| Intent Analyzer | 🔄 En progreso | 90% |
| MCP Tools | ⚠️ Básico | 25% |
| Documentación | 🔄 Actualización | 80% |

## 🚦 Próximos Pasos

### Inmediatos (Prioridad Alta)
1. **Configurar entorno**: Crear `.env` con credenciales reales
2. **Ejecutar pruebas**: Verificar que todos los tests pasen
3. **Validar integración A2A**: Probar comunicación entre agentes

### Corto Plazo
1. **Completar cliente Vertex AI**: Finalizar optimizaciones pendientes
2. **Implementar MCP Tools reales**: Desarrollar integraciones con servidores MCP
3. **Mejorar documentación**: Actualizar guías de API y ejemplos

### Medio Plazo
1. **Optimización de rendimiento**: Implementar caché distribuido con Redis
2. **Escalabilidad**: Configurar auto-scaling en Kubernetes
3. **Monitoreo avanzado**: Dashboard completo con Grafana
4. **Tests de carga**: Validar rendimiento bajo alta demanda

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/NuevaCaracteristica`)
3. Commit con mensajes descriptivos siguiendo el formato:
   - `Feat(component): descripción`
   - `Fix(component): descripción`
   - `Docs(component): descripción`
4. Push a tu rama (`git push origin feature/NuevaCaracteristica`)
5. Abre un Pull Request

## 📄 Licencia

[Especificar licencia del proyecto]

## 📞 Soporte

Para reportar problemas o solicitar ayuda:
- Abrir un issue en GitHub
- Contactar al equipo de desarrollo
- Revisar la documentación en `/docs`

---

**Nota**: Este README refleja el estado actual del proyecto al 13/05/2025. Para información más detallada sobre componentes específicos, consultar la documentación en el directorio `/docs`.
