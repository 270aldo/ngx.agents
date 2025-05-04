# Guía de Pruebas para NGX Agents

Este documento proporciona instrucciones detalladas sobre cómo configurar y ejecutar las pruebas unitarias para el proyecto NGX Agents.

## Configuración del Entorno de Pruebas

### Requisitos Previos

- Python 3.9 o superior
- Poetry (gestor de dependencias)

### Instalación de Dependencias

Para instalar todas las dependencias necesarias para las pruebas, ejecuta:

```bash
poetry install
```

## Estructura de las Pruebas

Las pruebas están organizadas en los siguientes directorios:

- `tests/unit/`: Pruebas unitarias para componentes individuales
- `tests/integration/`: Pruebas de integración entre componentes
- `tests/mocks/`: Implementaciones simuladas de servicios externos

## Ejecución de las Pruebas

### Ejecutar Pruebas por Tipo

Se han configurado marcadores en pytest para facilitar la ejecución selectiva de pruebas:

```bash
# Ejecutar todas las pruebas
make test

# Ejecutar solo pruebas unitarias
make test-unit
# o: poetry run pytest -m unit

# Ejecutar solo pruebas de integración
make test-integration
# o: poetry run pytest -m integration

# Ejecutar solo pruebas de agentes
make test-agents
# o: poetry run pytest -m agents
```

### Ejecutar Pruebas Específicas

```bash
# Ejecutar pruebas de autenticación
poetry run pytest tests/unit/auth/

# Ejecutar pruebas de persistencia
poetry run pytest tests/unit/persistence/

# Ejecutar pruebas del gestor de estados
poetry run pytest tests/unit/core/test_state_manager.py
```

### Ejecutar con Cobertura de Código

```bash
# Cobertura básica
make test-cov
# o: poetry run pytest --cov=core --cov=clients --cov=agents --cov=tools --cov=api

# Cobertura con informe HTML
make test-cov-html
# o: poetry run pytest --cov=core --cov=clients --cov=agents --cov=tools --cov=api --cov-report=html
```

El informe de cobertura HTML se genera en el directorio `coverage_html_report/`.

## Mocks Implementados

Para facilitar las pruebas sin dependencias externas, se han implementado varios mocks:

### Supabase Mock (`tests/mocks/supabase/__init__.py`)

Simula el comportamiento del cliente de Supabase para pruebas unitarias.

#### Características principales:

- **Modo Mock**: Permite simular operaciones CRUD sin conectarse a una base de datos real.
- **Almacenamiento en Memoria**: Utiliza diccionarios y listas en memoria para almacenar datos temporales.
- **Métodos Síncronos y Asíncronos**: Implementa tanto métodos síncronos como asíncronos para compatibilidad con diferentes partes del código.

#### Métodos implementados:

1. **Métodos de Persistencia**:
   - `get_or_create_user_by_api_key`: Obtiene o crea un usuario por su API key.
   - `log_conversation_message`: Registra un mensaje de conversación.
   - `get_conversation_history`: Obtiene el historial de conversación de un usuario.

2. **Métodos CRUD Asíncronos**:
   - `query`: Simula consultas a tablas con filtros, ordenamiento y paginación.
   - `insert`: Simula la inserción de datos en tablas.
   - `update`: Simula la actualización de datos en tablas.
   - `delete`: Simula la eliminación de datos en tablas.

### Google ADK Mock (`tests/mocks/adk/`)

Simula el comportamiento del Google Agent Development Kit (ADK) para pruebas.

#### Características principales:

- **Toolkit Simulado**: Implementa la clase `Toolkit` que simula el comportamiento del ADK.
- **Herramientas Personalizadas**: Permite registrar y ejecutar herramientas personalizadas.
- **Compatibilidad con Agentes**: Facilita las pruebas de agentes sin necesidad de conectarse a servicios externos.

#### Métodos implementados:

1. **Gestión de Herramientas**:
   - `add_tool`: Registra una nueva herramienta en el toolkit.
   - `execute`: Simula la ejecución de una herramienta.
   - `get_tools`: Obtiene las herramientas registradas.

### Uso de los Mocks

Los mocks se utilizan automáticamente en las pruebas a través de la configuración en `tests/conftest.py`, que aplica parches a las dependencias externas durante la ejecución de las pruebas.

#### Configuración de Mocks

Los mocks se aplican automáticamente para pruebas unitarias y de agentes, pero no para pruebas de integración. Esto se controla mediante la variable `RUNNING_INTEGRATION_TESTS` en `conftest.py`.

```python
# En tests/conftest.py
@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch):
    """Mockea dependencias externas para todas las pruebas."""
    # Solo aplicar mocks en pruebas unitarias y de agentes
    if not RUNNING_INTEGRATION_TESTS:
        # Aplicar mocks...
```

## Resolución de Problemas Comunes

### Advertencias de Pydantic

Las advertencias relacionadas con Pydantic han sido resueltas actualizando el código para usar `json_schema_extra` en lugar de argumentos directos en `Field`:

```python
# Antes (generaba advertencia)
supabase_url: AnyUrl = Field(default="http://localhost:54321", env="SUPABASE_URL")

# Después (sin advertencia)
supabase_url: AnyUrl = Field(default="http://localhost:54321", json_schema_extra={"env": "SUPABASE_URL"})
```

Si aún ves advertencias similares, puedes actualizar el código siguiendo este patrón.

### Conflictos de Dependencias

Si encuentras conflictos de dependencias, sigue estos pasos:

1. Actualiza Poetry a la última versión:
   ```bash
   pip install --upgrade poetry
   ```

2. Limpia la caché de Poetry:
   ```bash
   poetry cache clear --all pypi
   ```

3. Actualiza las dependencias:
   ```bash
   poetry update
   ```

4. Si el problema persiste, intenta recrear el entorno virtual:
   ```bash
   poetry env remove python
   poetry install
   ```

5. Verifica que estés usando la versión correcta de Python (3.9+) y el entorno virtual de Poetry (`poetry shell`).

## Contribución a las Pruebas

Al agregar nuevas funcionalidades, asegúrate de:

1. Crear pruebas unitarias para la nueva funcionalidad
2. Actualizar o crear mocks si es necesario
3. Verificar que todas las pruebas existentes sigan funcionando
4. Agregar marcadores apropiados a las nuevas pruebas (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
5. Actualizar la documentación de pruebas si es necesario

## Integración Continua

El proyecto está configurado con GitHub Actions para ejecutar automáticamente las pruebas en cada push y pull request. La configuración se encuentra en `.github/workflows/test.yml`.

## Limpieza del Entorno de Pruebas

Para limpiar archivos temporales y caché generados durante las pruebas:

```bash
make clean
```

Esto eliminará archivos `.pyc`, directorios `__pycache__`, archivos de cobertura y otros archivos temporales.
