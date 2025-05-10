# Gestión de Dependencias en NGX Agents

Este documento explica las estrategias para gestionar dependencias en el proyecto NGX Agents, evitando conflictos y asegurando la compatibilidad entre componentes.

## Gestores de Dependencias

El proyecto NGX Agents utiliza dos sistemas de gestión de dependencias:

1. **Poetry (Recomendado)**: Sistema moderno de gestión de dependencias y empaquetado para Python.
2. **Pip/requirements.txt**: Mantenido para compatibilidad con entornos que no utilizan Poetry.

## Instalación con Poetry (Recomendado)

Poetry proporciona un entorno aislado y gestión de dependencias más precisa:

```bash
# Instalar Poetry si no está instalado
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependencias del proyecto
poetry install

# Activar el entorno virtual
poetry shell
```

## Instalación con Pip

Para entornos que no utilizan Poetry:

```bash
# Crear un entorno virtual
python -m venv venv

# Activar el entorno virtual
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate     # En Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Entornos Virtuales Aislados por Componente

Para evitar conflictos de dependencias entre componentes, se ha creado un script que configura entornos virtuales aislados para cada componente principal:

```bash
# Ejecutar el script de configuración
bash setup_component_envs.sh

# Activar el entorno de un componente específico
source activate_component_env.sh agents  # Para el componente "agents"
```

Los componentes disponibles son:
- `agents`: Agentes inteligentes del sistema
- `app`: Aplicación FastAPI
- `clients`: Clientes para servicios externos
- `core`: Funcionalidades centrales
- `tools`: Herramientas y utilidades

## Actualización de Dependencias

### Con Poetry

```bash
# Actualizar todas las dependencias dentro de los rangos permitidos
poetry update

# Actualizar una dependencia específica
poetry update nombre-paquete

# Añadir una nueva dependencia
poetry add nombre-paquete
```

### Con Pip

```bash
# Actualizar requirements.txt después de añadir/actualizar dependencias
pip freeze > requirements.txt
```

## Resolución de Conflictos

Si encuentras conflictos de dependencias:

1. Verifica las versiones exactas en `poetry.lock` o usando `poetry show -t`
2. Utiliza entornos virtuales aislados para componentes con dependencias conflictivas
3. Ajusta los rangos de versiones en `pyproject.toml` para evitar incompatibilidades
4. Considera el uso de adaptadores o patrones de diseño para aislar código dependiente de bibliotecas específicas

## Buenas Prácticas

1. **Especificar rangos de versiones precisos**: Utiliza rangos como `>=1.0.0,<2.0.0` en lugar de simplemente `>=1.0.0`
2. **Mantener sincronizados `pyproject.toml` y `requirements.txt`**: Actualiza ambos archivos cuando añadas o modifiques dependencias
3. **Documentar dependencias específicas de componentes**: Añade comentarios explicando por qué se necesita cada dependencia
4. **Revisar regularmente las actualizaciones de seguridad**: Utiliza `safety check` para identificar vulnerabilidades
5. **Minimizar dependencias**: Evalúa si realmente necesitas cada dependencia o si puedes implementar la funcionalidad con bibliotecas estándar

## Estructura de Dependencias

El proyecto está organizado para minimizar el acoplamiento entre componentes:

```
ngx-agents/
├── agents/       # Dependencias: google-adk, google-generativeai
├── app/          # Dependencias: fastapi, uvicorn, pydantic
├── clients/      # Dependencias: httpx, websockets
├── core/         # Dependencias: pydantic, python-json-logger
└── tools/        # Dependencias: supabase
```

Cada componente debe importar solo las dependencias que realmente necesita, evitando importaciones innecesarias de otros componentes.
