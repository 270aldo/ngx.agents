# Sistema de Feedback y Aprendizaje

## Resumen

Se ha implementado un sistema completo de feedback que permite a los usuarios evaluar las respuestas de los agentes, proporcionando datos valiosos para la mejora continua del sistema.

## Arquitectura del Sistema

```
Usuario → API Feedback → Servicio → Base de Datos
           ↓               ↓            ↓
       Validación      Analytics    Métricas
                          ↓
                    Reentrenamiento
```

## Componentes Implementados

### 1. API de Feedback (`app/routers/feedback.py`)

#### Endpoints Disponibles

##### POST `/feedback/message`
Registra feedback para un mensaje específico.

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "feedback_type": "thumbs_up|thumbs_down|rating|comment|issue|suggestion",
  "rating": 1-5,
  "comment": "texto opcional",
  "categories": ["accuracy", "relevance", ...],
  "metadata": {}
}
```

##### POST `/feedback/session`
Registra feedback para una sesión completa.

```json
{
  "conversation_id": "uuid",
  "overall_rating": 1-5,
  "categories_feedback": {
    "accuracy": 5,
    "helpfulness": 4
  },
  "would_recommend": true,
  "comment": "texto opcional",
  "improvement_suggestions": ["sugerencia1", "sugerencia2"]
}
```

##### GET `/feedback/stats`
Obtiene estadísticas agregadas.

Query params:
- `start_date`: Fecha inicio (ISO format)
- `end_date`: Fecha fin (ISO format)
- `conversation_id`: ID específico (opcional)

##### POST `/feedback/search`
Búsqueda avanzada de feedback.

```json
{
  "feedback_type": "rating",
  "categories": ["accuracy"],
  "rating_min": 3,
  "rating_max": 5,
  "start_date": "2024-01-01T00:00:00Z",
  "limit": 100,
  "offset": 0
}
```

##### GET `/feedback/analytics` (Admin)
Analytics avanzados del feedback.

### 2. Servicio de Feedback (`core/feedback_service.py`)

#### Características

- **Registro de Feedback**: Almacena feedback de mensajes y sesiones
- **Análisis de Sentimiento**: Análisis básico de comentarios
- **Cálculo de NPS**: Net Promoter Score basado en recomendaciones
- **Identificación de Problemas**: Extracción de issues comunes
- **Analytics Avanzados**: Tendencias, performance por agente, áreas de mejora

#### Métricas Registradas

- `ngx_agents_feedback_received_total`: Total de feedback por tipo
- `ngx_agents_feedback_processing_seconds`: Tiempo de procesamiento
- `ngx_agents_feedback_sentiment_score`: Score de sentimiento

### 3. Esquemas de Datos (`app/schemas/feedback.py`)

#### Tipos de Feedback
- `thumbs_up`: Respuesta útil
- `thumbs_down`: Respuesta no útil
- `rating`: Calificación 1-5
- `comment`: Comentario general
- `issue`: Reporte de problema
- `suggestion`: Sugerencia de mejora

#### Categorías
- `accuracy`: Precisión de la información
- `relevance`: Relevancia de la respuesta
- `completeness`: Completitud
- `speed`: Velocidad de respuesta
- `helpfulness`: Utilidad
- `user_experience`: Experiencia general
- `technical_issue`: Problema técnico
- `other`: Otros

### 4. Base de Datos

#### Tablas
- `feedback`: Feedback individual de mensajes
- `session_feedback`: Feedback de sesiones completas
- `feedback_analytics`: Analytics agregados (caché)

#### Vistas
- `feedback_stats_view`: Estadísticas rápidas
- `nps_view`: Cálculo de Net Promoter Score

## Uso del Sistema

### Cliente JavaScript/React

```typescript
// Componente de feedback incluido
import FeedbackComponent from './FeedbackComponent';

<FeedbackComponent
  conversationId="conv-123"
  messageId="msg-456"
  authToken={userToken}
  onFeedbackSubmitted={(feedbackId) => {
    console.log('Feedback registrado:', feedbackId);
  }}
/>
```

### Integración con Chat

```javascript
// Después de recibir una respuesta
const response = await chatAPI.sendMessage(message);

// Mostrar componente de feedback
showFeedback(response.messageId);
```

### Dashboard de Analytics

```javascript
// Obtener estadísticas
const stats = await fetch('/feedback/stats', {
  headers: { Authorization: `Bearer ${token}` }
});

// Para admins: analytics completos
const analytics = await fetch('/feedback/analytics', {
  headers: { Authorization: `Bearer ${adminToken}` }
});
```

## Flujo de Feedback

1. **Usuario interactúa** con un agente
2. **Respuesta generada** por el sistema
3. **UI muestra opciones** de feedback
4. **Usuario evalúa** la respuesta
5. **Sistema registra** el feedback
6. **Analytics procesa** los datos
7. **Insights generados** para mejora

## Analytics y Reportes

### Métricas Clave

1. **Satisfaction Rate**
   ```
   thumbs_up / (thumbs_up + thumbs_down)
   ```

2. **Net Promoter Score (NPS)**
   ```
   (promoters - detractors) / total * 100
   ```

3. **Average Rating**
   ```
   sum(ratings) / count(ratings)
   ```

4. **Response Quality by Agent**
   - Rating promedio por agente
   - Issues reportados por agente
   - Categorías problemáticas

### Dashboards en Grafana

Se pueden crear dashboards con:
- Tendencia de satisfacción
- NPS en tiempo real
- Heatmap de categorías
- Top issues reportados
- Performance por agente

## Proceso de Mejora Continua

### 1. Recolección
- Feedback continuo de usuarios
- Métricas automáticas
- Análisis de patrones

### 2. Análisis
- Identificación de problemas recurrentes
- Análisis de sentimiento
- Correlación con métricas de sistema

### 3. Priorización
- Issues críticos (rating < 3)
- Problemas frecuentes
- Sugerencias populares

### 4. Implementación
- Ajuste de prompts
- Mejora de modelos
- Corrección de bugs

### 5. Validación
- A/B testing
- Monitoreo de métricas
- Feedback sobre cambios

## Exportación de Datos

### Para Machine Learning

```python
# Exportar datos para reentrenamiento
feedback_data = await feedback_service.export_for_ml(
    start_date=datetime(2024, 1, 1),
    min_rating=3,
    include_categories=["accuracy", "relevance"]
)

# Formato: conversación, respuesta, feedback, rating
```

### Para Reportes

```python
# Generar reporte mensual
monthly_report = await feedback_service.generate_monthly_report(
    month=1,
    year=2024
)
```

## Mejores Prácticas

### Para Desarrolladores

1. **Solicitar Feedback Contextual**
   - No interrumpir el flujo
   - Opciones rápidas primero
   - Detalles opcionales

2. **Responder al Feedback**
   - Agradecimiento inmediato
   - Acciones visibles
   - Comunicar mejoras

3. **Proteger Privacidad**
   - Anonimizar datos
   - Cumplir GDPR
   - Retention policies

### Para Usuarios

1. **Feedback Específico**
   - Usar categorías apropiadas
   - Comentarios constructivos
   - Ejemplos concretos

2. **Reportar Problemas**
   - Describir el contexto
   - Resultado esperado vs real
   - Pasos para reproducir

## Configuración y Personalización

### Variables de Entorno

```env
# Feedback settings
FEEDBACK_ENABLED=true
FEEDBACK_CACHE_TTL=300
FEEDBACK_MIN_COMMENT_LENGTH=10
FEEDBACK_MAX_COMMENT_LENGTH=2000
```

### Personalización de Categorías

```python
# En app/schemas/feedback.py
class CustomCategory(str, Enum):
    CUSTOM_1 = "custom_category_1"
    CUSTOM_2 = "custom_category_2"
```

## Seguridad y Privacidad

1. **Autenticación**: JWT requerido
2. **Autorización**: Users ven su propio feedback
3. **Sanitización**: Limpieza de inputs
4. **Rate Limiting**: Prevenir spam
5. **Anonimización**: Para analytics agregados

## Troubleshooting

### Feedback no se registra
1. Verificar autenticación
2. Validar formato de datos
3. Revisar logs del servicio

### Analytics vacíos
1. Verificar período de tiempo
2. Confirmar datos en DB
3. Revisar permisos de admin

### Performance lento
1. Verificar índices DB
2. Ajustar cache TTL
3. Limitar queries complejos

## Roadmap Futuro

1. **ML Integration**
   - Análisis de sentimiento avanzado
   - Clasificación automática
   - Detección de anomalías

2. **Real-time Analytics**
   - Dashboards en vivo
   - Alertas automáticas
   - Tendencias emergentes

3. **Gamification**
   - Rewards por feedback
   - Leaderboards
   - Badges de contribución

4. **Integration External**
   - Export a Slack
   - Webhooks
   - API pública

## Referencias

- [Feedback Best Practices](https://www.nngroup.com/articles/feedback/)
- [NPS Calculation](https://www.netpromoter.com/know/)
- [Sentiment Analysis](https://monkeylearn.com/sentiment-analysis/)