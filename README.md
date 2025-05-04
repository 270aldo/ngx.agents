# NGX Agents

Sistema de agentes NGX para entrenamiento y nutrición.

## Requisitos

- Python 3.9 o superior
- Poetry (gestor de dependencias)

## Instalación rápida

```bash
# Instalar Poetry si no está instalado
curl -sSL https://install.python-poetry.org | python3 -

# Clonar el repositorio
git clone <url-del-repositorio>
cd ngx-agents-refactorizado

# Instalar dependencias
make setup
# o directamente: poetry install --with dev,test
```

## Desarrollo

### Iniciar el entorno completo (A2A)

```bash
# Iniciar el servidor A2A, los agentes y la API
./scripts/run_dev.sh
```

Este script inicia los siguientes componentes en procesos separados:

1. Servidor A2A (puerto 9000)
2. Agentes prioritarios (Orchestrator, ProgressTracker, etc.)
3. API FastAPI (puerto 8000)

### Iniciar solo la API

```bash
# Iniciar solo el servidor API
make dev
# o: poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Pruebas

```bash
# Ejecutar todas las pruebas
make test

# Ejecutar solo pruebas unitarias
make test-unit

# Ejecutar solo pruebas de integración
make test-integration

# Ejecutar solo pruebas de agentes
make test-agents

# Ejecutar pruebas con cobertura
make test-cov

# Generar informe de cobertura HTML
make test-cov-html
```

### Sistema de Mocks

Para facilitar las pruebas unitarias sin dependencias externas, se han implementado mocks para:

- **Supabase**: Simulación completa del cliente de Supabase con almacenamiento en memoria.
- **Google ADK**: Simulación del Agent Development Kit para pruebas de agentes.
- **Gemini**: Simulación de la API de Gemini para pruebas de generación de texto.

Los mocks se aplican automáticamente durante las pruebas unitarias y de agentes, pero no durante las pruebas de integración. Consulta la documentación en `tests/README.md` para más detalles.

## Arquitectura A2A

El sistema NGX Agents implementa una arquitectura Agent-to-Agent (A2A) basada en Google ADK, que permite la comunicación entre agentes especializados a través de un servidor WebSocket central.

### Componentes principales

1. **Servidor A2A**: Actúa como broker para la comunicación entre agentes.
2. **Orchestrator**: Agente central que analiza intenciones y coordina con agentes especializados.
3. **Agentes Especializados**: Implementan capacidades específicas (entrenamiento, nutrición, motivación, etc.).

### Flujo de comunicación

```
Usuario → API FastAPI → Orchestrator → Agentes Especializados → Orchestrator → Usuario
```

Para más detalles, consulta la documentación en `infrastructure/README.md`.

## Estructura del proyecto

```
ngx-agents-refactorizado/
├── agents/              # Implementación de los agentes
│   ├── base/            # Clases base para agentes
│   ├── orchestrator/    # Agente orquestador principal
│   └── */               # Agentes especializados
├── app/                 # Aplicación FastAPI
│   ├── routers/         # Endpoints de la API
│   └── schemas/         # Esquemas de datos
├── clients/             # Clientes para servicios externos
├── core/                # Funcionalidades centrales
├── infrastructure/      # Infraestructura A2A
├── tools/               # Herramientas compartidas
├── tests/               # Pruebas
│   ├── unit/            # Pruebas unitarias
│   ├── integration/     # Pruebas de integración
│   ├── agents/          # Pruebas específicas de agentes
│   └── mocks/           # Mocks para pruebas
├── scripts/             # Scripts de utilidad
├── pyproject.toml       # Configuración de Poetry y herramientas
└── Makefile             # Comandos para desarrollo
```

## Gestión de dependencias

Este proyecto utiliza [Poetry](https://python-poetry.org/) para gestionar las dependencias. Las dependencias están definidas en `pyproject.toml` y bloqueadas en `poetry.lock` para garantizar entornos reproducibles.

### Resolución de Conflictos

Si encuentras conflictos de dependencias, sigue estos pasos:

1. Actualiza Poetry a la última versión: `pip install --upgrade poetry`
2. Limpia la caché de Poetry: `poetry cache clear --all pypi`
3. Actualiza las dependencias: `poetry update`
4. Si persisten los problemas, consulta la sección "Troubleshooting" en `tests/README.md`

Las dependencias están organizadas en grupos:

- **main**: Dependencias principales para la ejecución.
- **dev**: Herramientas de desarrollo como linters y formateadores.
- **test**: Dependencias para pruebas como pytest y mocks.

## Entornos de ejecución

- **Desarrollo**: Utiliza el comando `make dev` para iniciar el servidor de desarrollo.
- **Pruebas**: Utiliza los comandos `make test-*` para ejecutar las pruebas.
- **Producción**: Configura las variables de entorno necesarias y ejecuta `poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### Integración Continua

El proyecto está configurado con GitHub Actions para ejecutar automáticamente las pruebas en cada push y pull request. La configuración se encuentra en `.github/workflows/test.yml`.

### Calidad de Código

```bash
# Verificar el formato con Black
make lint

# Formatear el código automáticamente
make format

# Limpiar archivos temporales y caché
make clean
```

## Variables de entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```
# Servidor API
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Servidor A2A
A2A_HOST=0.0.0.0
A2A_PORT=9000
A2A_SERVER_URL=ws://localhost:9000

# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-clave-anonima

# Gemini
GEMINI_API_KEY=tu-api-key

# JWT
JWT_SECRET=tu-secreto-seguro
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Entorno
ENV=dev
LOG_LEVEL=INFO
```

Para pruebas, puedes crear un archivo `.env.test` con valores de prueba.
