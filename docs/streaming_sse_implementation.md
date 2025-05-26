# Implementación de Response Streaming con SSE

## Resumen

Se ha implementado un sistema de streaming de respuestas en tiempo real utilizando Server-Sent Events (SSE) para mejorar la experiencia del usuario al interactuar con los agentes NGX.

## Características Implementadas

### 1. Endpoint de Streaming SSE

- **Ruta**: `POST /stream/chat`
- **Autenticación**: JWT requerido
- **Content-Type Response**: `text/event-stream`

### 2. Arquitectura

```
Cliente → FastAPI → Stream Router → Orchestrator → Agentes
           ↓            ↓                ↓
      Auth JWT    EventSource      Procesamiento
                   Response         Incremental
```

### 3. Formato de Eventos SSE

#### Evento de Inicio
```javascript
event: start
data: {"conversation_id": "uuid", "status": "processing"}
```

#### Chunks de Contenido
```javascript
event: chunk
data: {
  "type": "content",
  "content": "texto parcial",
  "chunk_index": 0,
  "is_final": false
}
```

#### Evento de Finalización
```javascript
event: end
data: {"conversation_id": "uuid", "status": "completed", "message_count": 1}
```

#### Evento de Error
```javascript
event: error
data: {"error": "mensaje de error", "conversation_id": "uuid", "status": "error"}
```

## Uso

### Cliente JavaScript/HTML

```javascript
const response = await fetch('http://localhost:8000/stream/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream'
    },
    body: JSON.stringify({
        message: 'Tu mensaje aquí',
        metadata: {}
    })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    // Procesar eventos SSE
}
```

### Cliente React

Ver ejemplo completo en `/examples/StreamChatComponent.tsx`

```typescript
import StreamChatComponent from './StreamChatComponent';

function App() {
    return (
        <StreamChatComponent 
            authToken="tu-jwt-token"
            apiUrl="http://localhost:8000"
        />
    );
}
```

## Testing

### Tests de Integración

Ejecutar tests de streaming:
```bash
poetry run pytest tests/integration/test_stream_endpoint.py -v
```

### Tests de Rendimiento

```bash
# Obtener token de autenticación
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' | jq -r .access_token)

# Ejecutar tests de rendimiento
python scripts/test_stream_performance.py --token $TOKEN
```

## Métricas de Rendimiento

### Objetivos
- **Time to First Byte (TTFB)**: < 200ms
- **Latencia entre chunks**: < 100ms
- **Throughput**: > 1000 requests/segundo
- **Concurrencia**: Soportar 100+ streams simultáneos

### Monitoreo

Los eventos de streaming generan las siguientes métricas:
- `stream.chat.started`: Contador de streams iniciados
- `stream.chat.completed`: Contador de streams completados
- `stream.chat.error`: Contador de errores
- `stream.chat.duration`: Histograma de duración total
- `stream.chat.ttfb`: Histograma de tiempo hasta primer byte

## Próximos Pasos

### Mejoras Planificadas

1. **Integración Real con Orchestrator**
   - Modificar el orquestador para generar respuestas incrementales
   - Implementar buffer de chunks para optimizar transmisión

2. **Backpressure y Control de Flujo**
   - Implementar mecanismos para pausar/reanudar streams
   - Control de velocidad basado en capacidad del cliente

3. **Compresión**
   - Habilitar gzip para reducir uso de ancho de banda
   - Implementar compresión específica para SSE

4. **Reconexión Automática**
   - Implementar Last-Event-ID para recuperación de conexión
   - Mantener estado de conversación en caché

5. **WebSocket como Alternativa**
   - Evaluar implementación con WebSockets para bidireccionalidad
   - Comparar rendimiento SSE vs WebSocket

## Ejemplos de Uso

### Cliente Básico HTML
Ver `/examples/stream_client.html`

### Componente React Avanzado
Ver `/examples/StreamChatComponent.tsx`

### Script de Performance Testing
Ver `/scripts/test_stream_performance.py`

## Consideraciones de Seguridad

1. **Autenticación**: JWT requerido para todos los endpoints
2. **Rate Limiting**: Implementar límites por usuario
3. **Timeout**: Streams se cierran automáticamente después de 5 minutos
4. **CORS**: Configurado para permitir Event-Stream desde dominios autorizados

## Troubleshooting

### Problemas Comunes

1. **"Connection refused"**
   - Verificar que el servidor esté corriendo
   - Verificar CORS configuration

2. **"Unauthorized"**
   - Verificar token JWT válido
   - Verificar headers de autorización

3. **Chunks no llegan**
   - Verificar proxy/nginx configuration para SSE
   - Deshabilitar buffering en proxies intermedios

### Debug

Habilitar logs detallados:
```python
LOG_LEVEL=DEBUG poetry run uvicorn app.main:app --reload
```

## Referencias

- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [FastAPI Streaming Response](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [SSE vs WebSocket Comparison](https://www.smashingmagazine.com/2018/02/sse-websockets-data-flow-http2/)