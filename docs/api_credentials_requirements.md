# Lista de APIs, Credenciales y Configuraciones Necesarias para Pruebas

A continuación, presento una lista completa de las APIs, credenciales y configuraciones necesarias para comenzar a hacer pruebas con los diferentes servicios utilizados en el proyecto NGX Agents:

## 1. Google Cloud / Vertex AI

### Credenciales Básicas:
- **GOOGLE_APPLICATION_CREDENTIALS**: Ruta al archivo JSON de credenciales de servicio
- **GOOGLE_CLOUD_PROJECT**: ID del proyecto de Google Cloud

### Configuraciones de Vertex AI:
- **VERTEX_AI_LOCATION**: Ubicación/región de los servicios (ej. "us-central1")
- **VERTEX_AI_MODEL**: Modelo de Vertex AI a utilizar (ej. "text-bison@001")
- **VERTEX_AI_EMBEDDING_MODEL**: Modelo para generación de embeddings (ej. "textembedding-gecko@001")
- **VERTEX_AI_VISION_MODEL**: Modelo para procesamiento de imágenes (ej. "imagetext@001")
- **VERTEX_AI_MULTIMODAL_MODEL**: Modelo multimodal (ej. "gemini-pro-vision")
- **VERTEX_AI_MAX_OUTPUT_TOKENS**: Número máximo de tokens de salida
- **VERTEX_AI_TEMPERATURE**: Temperatura para generación (ej. 0.2)
- **VERTEX_AI_TOP_P**: Valor top-p para generación (ej. 0.95)
- **VERTEX_AI_TOP_K**: Valor top-k para generación (ej. 40)

### Configuraciones para Document AI:
- **DOCUMENT_AI_LOCATION**: Ubicación de los procesadores (ej. "us")
- **DOCUMENT_AI_PROCESSOR_ID**: ID del procesador general
- **DOCUMENT_AI_OCR_PROCESSOR_ID**: ID del procesador OCR
- **DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID**: ID del procesador de clasificación
- **DOCUMENT_AI_ENTITY_PROCESSOR_ID**: ID del procesador de entidades
- **DOCUMENT_AI_FORM_PROCESSOR_ID**: ID del procesador de formularios
- **DOCUMENT_AI_INVOICE_PROCESSOR_ID**: ID del procesador de facturas
- **DOCUMENT_AI_RECEIPT_PROCESSOR_ID**: ID del procesador de recibos
- **DOCUMENT_AI_ID_PROCESSOR_ID**: ID del procesador de documentos de identidad
- **DOCUMENT_AI_MEDICAL_PROCESSOR_ID**: ID del procesador de documentos médicos
- **DOCUMENT_AI_TAX_PROCESSOR_ID**: ID del procesador de documentos fiscales
- **DOCUMENT_AI_TIMEOUT**: Tiempo máximo de espera para operaciones (segundos)

### Configuraciones para Speech-to-Text:
- **SPEECH_TO_TEXT_LOCATION**: Ubicación del servicio (ej. "global")
- **SPEECH_TO_TEXT_MODEL**: Modelo a utilizar (ej. "latest_long")
- **SPEECH_TO_TEXT_LANGUAGE_CODE**: Código de idioma (ej. "es-MX")

### Configuraciones para Text-to-Speech:
- **TEXT_TO_SPEECH_LOCATION**: Ubicación del servicio (ej. "global")
- **TEXT_TO_SPEECH_VOICE_NAME**: Nombre de la voz (ej. "es-ES-Standard-A")
- **TEXT_TO_SPEECH_LANGUAGE_CODE**: Código de idioma (ej. "es-ES")

## 2. Pinecone

### Credenciales:
- **PINECONE_API_KEY**: Clave API de Pinecone
- **PINECONE_ENVIRONMENT**: Entorno de Pinecone (ej. "us-west1-gcp")

### Configuraciones:
- **PINECONE_INDEX_NAME**: Nombre del índice a utilizar
- **PINECONE_NAMESPACE**: Namespace dentro del índice (opcional)
- **PINECONE_DIMENSION**: Dimensión de los vectores (debe coincidir con el modelo de embeddings)
- **PINECONE_METRIC**: Métrica de similitud (ej. "cosine", "euclidean", "dotproduct")

## 3. Supabase

### Credenciales:
- **SUPABASE_URL**: URL de la instancia de Supabase
- **SUPABASE_KEY**: Clave API de Supabase (anon key o service_role key)
- **SUPABASE_JWT_SECRET**: Secreto JWT para autenticación (si se utiliza)

### Configuraciones:
- **SUPABASE_STORAGE_BUCKET**: Nombre del bucket de almacenamiento (si se utiliza Storage)
- **SUPABASE_REALTIME_ENABLED**: Habilitar funcionalidades en tiempo real (true/false)

## 4. Google Cloud Storage (GCS)

### Credenciales:
- Ya incluidas en GOOGLE_APPLICATION_CREDENTIALS

### Configuraciones:
- **GCS_BUCKET_NAME**: Nombre del bucket de GCS
- **GCS_LOCATION**: Ubicación del bucket (ej. "us-central1")

## 5. Redis (para caché)

### Credenciales:
- **REDIS_HOST**: Host del servidor Redis
- **REDIS_PORT**: Puerto del servidor Redis
- **REDIS_PASSWORD**: Contraseña del servidor Redis (si está configurado)

### Configuraciones:
- **REDIS_DB**: Número de base de datos a utilizar
- **REDIS_SSL**: Usar SSL para conexión (true/false)
- **REDIS_TIMEOUT**: Tiempo de espera para operaciones

## 6. Configuraciones Generales del Sistema

### Telemetría:
- **TELEMETRY_ENABLED**: Habilitar telemetría (true/false)
- **OTEL_EXPORTER_OTLP_ENDPOINT**: Endpoint para exportar telemetría OpenTelemetry
- **OTEL_SERVICE_NAME**: Nombre del servicio para telemetría

### Configuraciones de Entorno:
- **ENVIRONMENT**: Entorno de ejecución (development, testing, production)
- **LOG_LEVEL**: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
- **MOCK_EXTERNAL_SERVICES**: Usar mocks para servicios externos (true/false)

### Configuraciones de Circuito:
- **CIRCUIT_BREAKER_FAILURE_THRESHOLD**: Umbral de fallos para circuit breaker
- **CIRCUIT_BREAKER_RECOVERY_TIMEOUT**: Tiempo de recuperación para circuit breaker

## Notas Importantes

1. **Archivos de Configuración**: Es recomendable mantener estas credenciales en archivos `.env` separados por entorno (`.env.development`, `.env.testing`, `.env.production`).

2. **Seguridad**: Nunca incluir credenciales en el código fuente o repositorios. Utilizar variables de entorno o servicios de gestión de secretos.

3. **Modos de Prueba**: Para pruebas iniciales, todos los clientes tienen un `mock_mode` que puede activarse para simular respuestas sin hacer llamadas reales a las APIs.

4. **Cuotas y Costos**: Tener en cuenta las cuotas y costos asociados a cada servicio, especialmente para Vertex AI y Pinecone que tienen modelos de precios basados en uso.

5. **Permisos**: Asegurarse de que las cuentas de servicio tengan los permisos mínimos necesarios para las operaciones requeridas.

## Plantilla para Archivo .env

A continuación se presenta una plantilla para un archivo `.env` que puede utilizarse para configurar el entorno de pruebas:

```
# Google Cloud / Vertex AI
GOOGLE_APPLICATION_CREDENTIALS=/ruta/al/archivo/credenciales.json
GOOGLE_CLOUD_PROJECT=nombre-proyecto

# Vertex AI - General
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=text-bison@001
VERTEX_AI_EMBEDDING_MODEL=textembedding-gecko@001
VERTEX_AI_VISION_MODEL=imagetext@001
VERTEX_AI_MULTIMODAL_MODEL=gemini-pro-vision
VERTEX_AI_MAX_OUTPUT_TOKENS=1024
VERTEX_AI_TEMPERATURE=0.2
VERTEX_AI_TOP_P=0.95
VERTEX_AI_TOP_K=40

# Document AI
DOCUMENT_AI_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=processor-id-general
DOCUMENT_AI_OCR_PROCESSOR_ID=processor-id-ocr
DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID=processor-id-classifier
DOCUMENT_AI_ENTITY_PROCESSOR_ID=processor-id-entity
DOCUMENT_AI_FORM_PROCESSOR_ID=processor-id-form
DOCUMENT_AI_INVOICE_PROCESSOR_ID=processor-id-invoice
DOCUMENT_AI_RECEIPT_PROCESSOR_ID=processor-id-receipt
DOCUMENT_AI_ID_PROCESSOR_ID=processor-id-id
DOCUMENT_AI_MEDICAL_PROCESSOR_ID=processor-id-medical
DOCUMENT_AI_TAX_PROCESSOR_ID=processor-id-tax
DOCUMENT_AI_TIMEOUT=60

# Speech-to-Text
SPEECH_TO_TEXT_LOCATION=global
SPEECH_TO_TEXT_MODEL=latest_long
SPEECH_TO_TEXT_LANGUAGE_CODE=es-MX

# Text-to-Speech
TEXT_TO_SPEECH_LOCATION=global
TEXT_TO_SPEECH_VOICE_NAME=es-ES-Standard-A
TEXT_TO_SPEECH_LANGUAGE_CODE=es-ES

# Pinecone
PINECONE_API_KEY=tu-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=nombre-indice
PINECONE_NAMESPACE=namespace-opcional
PINECONE_DIMENSION=768
PINECONE_METRIC=cosine

# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-api-key
SUPABASE_JWT_SECRET=tu-jwt-secret
SUPABASE_STORAGE_BUCKET=nombre-bucket
SUPABASE_REALTIME_ENABLED=true

# Google Cloud Storage
GCS_BUCKET_NAME=nombre-bucket
GCS_LOCATION=us-central1

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=contraseña-opcional
REDIS_DB=0
REDIS_SSL=false
REDIS_TIMEOUT=5

# Telemetría
TELEMETRY_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=ngx-agents

# Configuraciones Generales
ENVIRONMENT=development
LOG_LEVEL=INFO
MOCK_EXTERNAL_SERVICES=false

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30
```

Esta lista será actualizada con las credenciales específicas que se proporcionen para el proyecto.
