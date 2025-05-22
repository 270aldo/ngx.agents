# Requisitos para Vertex AI Vector Search y RAG Engine

Este documento detalla los requisitos necesarios para implementar Vertex AI Vector Search y RAG Engine en el proyecto NGX Agents.

## Credenciales y Permisos

Para utilizar Vertex AI Vector Search y RAG Engine, se necesitan las siguientes credenciales y permisos:

1. **Cuenta de servicio de Google Cloud** con los siguientes roles:
   - `roles/aiplatform.user` - Para usar Vertex AI
   - `roles/storage.objectAdmin` - Para acceder a Cloud Storage
   - `roles/aiplatform.admin` - Para crear y administrar recursos de Vertex AI

2. **Archivo de credenciales JSON** para la cuenta de servicio, que debe contener:
   - `project_id`: ID del proyecto de Google Cloud
   - `private_key`: Clave privada para autenticación
   - `client_email`: Email de la cuenta de servicio
   - Otros campos estándar de las credenciales de Google Cloud

## Recursos de Google Cloud

Se requieren los siguientes recursos en Google Cloud:

1. **Proyecto de Google Cloud** con:
   - API de Vertex AI habilitada
   - API de Vertex AI Vector Search habilitada
   - API de Cloud Storage habilitada
   - Facturación habilitada

2. **Bucket de Cloud Storage** para:
   - Almacenar documentos para RAG Engine
   - Almacenar configuraciones de índices
   - Almacenar resultados intermedios de procesamiento

3. **Región de Google Cloud** compatible con:
   - Vertex AI Vector Search (no todas las regiones lo soportan)
   - Modelos Gemini 2.5 Pro y Flash
   - Modelo de embeddings text-embedding-large-exp-03-07

## Configuración de Vertex AI Vector Search

Para configurar Vertex AI Vector Search, se necesita:

1. **Índice vectorial** con:
   - Dimensión: 3072 (para text-embedding-large-exp-03-07)
   - Métrica de distancia: DOT_PRODUCT_DISTANCE (recomendado para este modelo)
   - Algoritmo de aproximación: tree-AH (recomendado para alta dimensionalidad)

2. **Endpoint de índice** para:
   - Desplegar el índice vectorial
   - Realizar consultas de búsqueda vectorial

## Configuración de RAG Engine

Para configurar Vertex AI RAG Engine, se necesita:

1. **Corpus de documentos** en:
   - Un bucket de Cloud Storage
   - Formato compatible (PDF, TXT, DOCX, HTML, etc.)

2. **Configuración de RAG Engine**:
   - Modelo de embeddings: text-embedding-large-exp-03-07
   - Estrategia de chunking: configurable según necesidades
   - Modelo de generación: gemini-2.5-pro para respuestas

3. **Aplicación RAG**:
   - Configuración de recuperación (top-k, filtros, etc.)
   - Configuración de generación (temperatura, tokens máximos, etc.)

## Variables de Entorno Requeridas

Actualiza el archivo `.env` con las siguientes variables:

```bash
# Google Cloud y Vertex AI
GOOGLE_CLOUD_PROJECT=tu-proyecto-id
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credenciales.json
VERTEX_LOCATION=us-central1  # Región que soporte todos los servicios necesarios

# Vertex AI Vector Search
VECTOR_STORE_TYPE=vertex
VERTEX_VECTOR_SEARCH_INDEX=ngx-embeddings
VERTEX_VECTOR_SEARCH_ENDPOINT=ngx-embeddings-endpoint
VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID=ngx-embeddings-deployed
VERTEX_VECTOR_DIMENSION=3072
VERTEX_VECTOR_DISTANCE_MEASURE=DOT_PRODUCT_DISTANCE

# Vertex AI RAG Engine
VERTEX_RAG_BUCKET=tu-bucket-rag
VERTEX_RAG_CORPUS_DIRECTORY=corpus
VERTEX_RAG_APPLICATION_ID=ngx-rag-application
VERTEX_RAG_CHUNK_SIZE=1024
VERTEX_RAG_CHUNK_OVERLAP=256

# Modelos de Vertex AI
VERTEX_EMBEDDING_MODEL=text-embedding-large-exp-03-07
VERTEX_ORCHESTRATOR_MODEL=gemini-2.5-pro
VERTEX_AGENT_MODEL=gemini-2.5-flash
```

## Pasos para la Configuración

1. **Crear proyecto de Google Cloud** (si no existe):
   ```bash
   gcloud projects create [PROJECT_ID] --name="NGX Agents Project"
   gcloud config set project [PROJECT_ID]
   ```

2. **Habilitar APIs necesarias**:
   ```bash
   gcloud services enable aiplatform.googleapis.com storage.googleapis.com
   ```

3. **Crear cuenta de servicio y descargar credenciales**:
   ```bash
   gcloud iam service-accounts create ngx-agents-sa
   gcloud projects add-iam-policy-binding [PROJECT_ID] \
       --member="serviceAccount:ngx-agents-sa@[PROJECT_ID].iam.gserviceaccount.com" \
       --role="roles/aiplatform.user"
   gcloud projects add-iam-policy-binding [PROJECT_ID] \
       --member="serviceAccount:ngx-agents-sa@[PROJECT_ID].iam.gserviceaccount.com" \
       --role="roles/storage.objectAdmin"
   gcloud projects add-iam-policy-binding [PROJECT_ID] \
       --member="serviceAccount:ngx-agents-sa@[PROJECT_ID].iam.gserviceaccount.com" \
       --role="roles/aiplatform.admin"
   gcloud iam service-accounts keys create credentials.json \
       --iam-account=ngx-agents-sa@[PROJECT_ID].iam.gserviceaccount.com
   ```

4. **Crear bucket de Cloud Storage**:
   ```bash
   gcloud storage buckets create gs://[BUCKET_NAME] --location=[LOCATION]
   ```

5. **Crear índice de Vector Search** (usando la consola de Google Cloud o la API)

6. **Configurar RAG Engine** (usando la consola de Google Cloud o la API)
