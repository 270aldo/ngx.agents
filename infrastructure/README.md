# Infraestructura A2A para NGX Agents

Este directorio contiene los componentes de infraestructura para la comunicación Agent-to-Agent (A2A) en el sistema NGX Agents.

## Servidor A2A

El servidor A2A es el componente central que permite la comunicación entre agentes mediante WebSockets. Está basado en el framework Google ADK y proporciona las siguientes funcionalidades:

- Registro y descubrimiento de agentes
- Enrutamiento de mensajes entre agentes
- Gestión de tareas y respuestas

### Uso del Servidor A2A

Para iniciar el servidor A2A de forma independiente:

```bash
python -m infrastructure.a2a_server
```

El servidor se iniciará en `0.0.0.0:9000` por defecto. Puedes configurar el host y puerto mediante variables de entorno:

```bash
A2A_HOST=localhost A2A_PORT=9001 python -m infrastructure.a2a_server
```

### Arquitectura A2A

La arquitectura A2A se basa en los siguientes componentes:

1. **Servidor A2A**: Actúa como broker para la comunicación entre agentes.
2. **Agentes A2A**: Implementan la interfaz A2A para registrarse y comunicarse con otros agentes.
3. **Orchestrator**: Agente especial que coordina la comunicación entre agentes especializados.

El flujo de comunicación es el siguiente:

```
Usuario -> API FastAPI -> Orchestrator -> Agentes Especializados -> Orchestrator -> Usuario
```

## Integración con Google ADK

El sistema utiliza el framework Google Agent Development Kit (ADK) para implementar la comunicación A2A. Los componentes principales son:

- `adk.toolkit.Toolkit`: Permite registrar y ejecutar herramientas (skills) en los agentes.
- `adk.server.Server`: Implementa el servidor WebSocket para la comunicación A2A.
- `adk.client.Client`: Permite a los agentes conectarse al servidor y comunicarse con otros agentes.

## Ejecución del Entorno Completo

Para iniciar todo el entorno (servidor A2A, agentes y API):

```bash
./scripts/run_dev.sh
```

Este script inicia los siguientes componentes en procesos separados:

1. Servidor A2A
2. Agentes prioritarios:
   - Orchestrator
   - ProgressTracker
   - GeminiTrainingAssistant
   - MotivationBehaviorCoach
3. API FastAPI

## Configuración

La configuración del servidor A2A y los agentes se realiza mediante variables de entorno:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| A2A_HOST | Host del servidor A2A | 0.0.0.0 |
| A2A_PORT | Puerto del servidor A2A | 9000 |
| A2A_SERVER_URL | URL completa del servidor A2A | ws://localhost:9000 |
