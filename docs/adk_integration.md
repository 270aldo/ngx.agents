# Integración con Google ADK Oficial

Este documento describe la integración del proyecto NGX Agents con la biblioteca oficial de Google Agent Development Kit (ADK).

## Cambios Realizados

### 1. Adaptadores para Google ADK

Se han creado adaptadores en el directorio `adk/` que utilizan la biblioteca oficial de Google ADK:

- `adk/agent.py`: Implementa las clases `Agent` y `Skill` utilizando la biblioteca oficial
- `adk/toolkit.py`: Implementa la clase `Toolkit` utilizando la biblioteca oficial

Estos adaptadores mantienen compatibilidad con el código existente, permitiendo una migración gradual.

### 2. Mecanismo de Fallback

Los adaptadores incluyen un mecanismo de fallback que utiliza stubs locales si la biblioteca oficial no está disponible. Esto permite:

- Ejecutar el código en entornos donde la biblioteca oficial no está instalada
- Mantener compatibilidad con pruebas existentes
- Facilitar el desarrollo sin dependencias externas

### 3. Pruebas de Integración

Se han añadido pruebas específicas para verificar la integración con Google ADK:

- `tests/test_adk_integration.py`: Pruebas para verificar la inicialización de agentes, registro de skills y ejecución de skills

## Uso de la Integración

### Importación de Componentes

Para utilizar la integración con Google ADK, importa los componentes desde el directorio `adk/`:

```python
from adk.agent import Agent, Skill
from adk.toolkit import Toolkit
```

### Creación de Agentes

```python
# Crear un toolkit
toolkit = Toolkit()

# Crear un agente
agent = Agent(
    toolkit=toolkit,
    name="MiAgente",
    description="Descripción del agente"
)
```

### Definición de Skills

```python
# Definir una skill
async def mi_skill_handler(input_text: str) -> str:
    return f"Procesado: {input_text}"

# Crear una skill
mi_skill = Skill(
    name="mi_skill",
    description="Descripción de la skill",
    handler=mi_skill_handler
)

# Registrar la skill en el toolkit
toolkit.register_skill(mi_skill)
```

### Ejecución de Skills

```python
# Ejecutar una skill
result = await toolkit.execute_skill("mi_skill", input_text="Hola mundo")
```

## Compatibilidad con Código Existente

La integración mantiene compatibilidad con el código existente a través de:

- Interfaces consistentes con las implementaciones anteriores
- Mecanismo de fallback para entornos sin la biblioteca oficial
- Adaptadores que abstraen las diferencias entre la implementación oficial y la local

## Próximos Pasos

1. Migrar gradualmente los agentes existentes para utilizar la implementación oficial
2. Actualizar la documentación y ejemplos
3. Implementar pruebas adicionales para verificar la compatibilidad
4. Eliminar los stubs locales una vez que la migración esté completa
