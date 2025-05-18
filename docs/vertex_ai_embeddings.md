# Guía de Modelos de Embeddings en NGX Agents

## Modelos de Embeddings de Vertex AI

NGX Agents utiliza los modelos de embeddings de Vertex AI para convertir texto en representaciones vectoriales que capturan el significado semántico. Estos vectores se utilizan para búsquedas semánticas, clasificación y otras tareas de procesamiento de lenguaje natural.

### Modelo Actual

El sistema utiliza actualmente el modelo `text-embedding-large-exp-03-07` de Vertex AI, que ofrece las siguientes características:

- **Dimensionalidad**: 3072 dimensiones
- **Rendimiento**: Modelo más avanzado con mayor precisión y capacidad de capturar matices semánticos
- **Compatibilidad**: Requiere un índice Pinecone configurado con la misma dimensionalidad (3072)
- **Disponibilidad**: Disponible en la región us-central1

### Ventajas del Modelo Seleccionado

- **Máxima precisión**: Ofrece el mejor rendimiento en tareas de similitud semántica y recuperación de información
- **Representaciones más ricas**: La alta dimensionalidad permite capturar relaciones semánticas más complejas
- **Mejor rendimiento en tareas específicas**: Ideal para aplicaciones que requieren alta precisión en la comprensión del texto
- **Resultados de última generación**: Implementa las técnicas más avanzadas en embeddings de texto

### Comparativa con Alternativas

| Modelo | Dimensiones | Ventajas | Desventajas | Recomendado para |
|--------|-------------|----------|-------------|------------------|
| **text-embedding-large-exp-03-07** | 3072 | Máxima precisión, mejor rendimiento | Mayor costo, requiere plan de pago en Pinecone | Aplicaciones críticas donde la precisión es prioritaria |
| **text-multilingual-embedding-002** | 768 | Buen soporte multilingüe, compatible con plan gratuito de Pinecone | Menor precisión que el modelo large | Aplicaciones multilingües con presupuesto limitado |
| **text-embedding-005** | 768 | Optimizado para inglés, compatible con plan gratuito | Rendimiento limitado en otros idiomas | Aplicaciones principalmente en inglés con presupuesto limitado |
| **AWS Bedrock Embeddings** | Variable | Ofrece capa gratuita, múltiples modelos | Ecosistema diferente, posible complejidad de integración | Proyectos ya integrados con AWS |

### Configuración

Para utilizar el modelo de embeddings avanzado, se deben configurar las siguientes variables de entorno:

```
# Configuración de Vertex AI Embeddings
VERTEX_EMBEDDING_MODEL=text-embedding-large-exp-03-07
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credenciales.json
GOOGLE_CLOUD_PROJECT=tu-proyecto-id
EMBEDDING_VECTOR_DIMENSION=3072

# Configuración de Pinecone
PINECONE_API_KEY=tu-api-key
PINECONE_ENVIRONMENT=tu-entorno
PINECONE_INDEX_NAME=ngx-embeddings
PINECONE_DIMENSION=3072
PINECONE_METRIC=cosine
```

## Integración con Pinecone

Los embeddings generados se almacenan en Pinecone con las siguientes configuraciones:

- **Dimensión**: 3072 (debe coincidir con la dimensionalidad del modelo de embeddings)
- **Métrica**: cosine (recomendada para la mayoría de los casos de uso de búsqueda semántica)
- **Tipo de vector**: Dense
- **Modo de capacidad**: Serverless (para escalabilidad automática)
- **Plan requerido**: Se requiere un plan de pago en Pinecone para soportar vectores de 3072 dimensiones

## Consideraciones de Rendimiento y Costos

- **Latencia vs. Precisión**: El modelo `text-embedding-large-exp-03-07` prioriza la precisión sobre la latencia
- **Caché**: El sistema implementa estrategias de caché avanzadas para optimizar el rendimiento y reducir costos
- **Costos de Vertex AI**: El modelo large tiene un costo más elevado por solicitud que los modelos de menor dimensionalidad
- **Costos de Pinecone**: Se requiere un plan de pago para soportar vectores de 3072 dimensiones
- **Optimización de costos**: Implementar estrategias de batch processing y caché para reducir el número de solicitudes

## Recomendaciones sobre Proveedores de Servicios

### Google Cloud Vertex AI (Implementación Actual)
- **Ventajas**: Mejor rendimiento con el modelo text-embedding-large-exp-03-07, integración perfecta con otros servicios de Google Cloud
- **Desventajas**: Sin capa gratuita para embeddings, costos más elevados para el modelo large
- **Recomendado para**: Aplicaciones donde la precisión es crítica y se dispone de presupuesto

### AWS Bedrock
- **Ventajas**: Ofrece capa gratuita, múltiples modelos disponibles (Titan, Cohere, etc.)
- **Desventajas**: Posible complejidad en la migración desde Google Cloud
- **Recomendado para**: Proyectos con restricciones de presupuesto o ya integrados con AWS

### Implementación Híbrida (Recomendación)
Para optimizar costos y rendimiento, se recomienda una implementación híbrida:
1. Utilizar el modelo `text-embedding-large-exp-03-07` para:
   - Indexación inicial de contenido
   - Consultas críticas donde la precisión es fundamental
   - Análisis semántico avanzado

2. Considerar AWS Bedrock con su capa gratuita para:
   - Consultas de alto volumen y baja criticidad
   - Entornos de desarrollo y pruebas
   - Reducción de costos en operaciones frecuentes

Esta estrategia permite aprovechar la máxima precisión del modelo large donde es necesario, mientras se controlan los costos utilizando alternativas más económicas para operaciones menos críticas.

## Implementación en el Código

El cliente de embeddings está implementado en `clients/vertex_ai/embedding_client.py` y proporciona:

- Generación de embeddings individuales y en batch
- Caché configurable para optimizar rendimiento
- Manejo de errores con patrón circuit breaker
- Telemetría detallada para monitoreo

## Pruebas y Validación

Para validar el rendimiento del modelo avanzado, se recomienda:

1. Generar embeddings para un conjunto diverso de textos
2. Realizar pruebas comparativas de similitud semántica entre el modelo large y alternativas
3. Evaluar la precisión en tareas de recuperación de información y clasificación
4. Medir el impacto en costos y rendimiento en diferentes escenarios de uso

## Recomendaciones para Producción

- Monitorear el uso de memoria y costos de manera rigurosa
- Implementar estrategias de particionamiento en Pinecone para colecciones grandes
- Considerar la compresión de vectores para optimizar almacenamiento y transferencia
- Establecer presupuestos y alertas para controlar costos
- Evaluar periódicamente el balance entre precisión y costos según las necesidades del proyecto
