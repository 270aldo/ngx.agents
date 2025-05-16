#!/bin/bash
# Script para configuración de backups automáticos del cliente Vertex AI
# 
# Este script implementa:
# 1. Backups de la base de datos
# 2. Backups del estado del sistema
# 3. Verificación de integridad de backups
# 4. Procedimientos de restauración
#
# Uso: ./vertex_ai_backup.sh [--action backup|restore|verify] [--backup-id BACKUP_ID] [--dry-run]

set -e

# Configuración por defecto
ACTION=${ACTION:-"backup"}
BACKUP_ID=${BACKUP_ID:-""}
DRY_RUN=${DRY_RUN:-false}
NAMESPACE=${NAMESPACE:-"ngx-agents"}
BACKUP_BUCKET=${BACKUP_BUCKET:-"gs://ngx-agents-backups"}
DB_INSTANCE=${DB_INSTANCE:-"ngx-agents-db"}
REDIS_POD=${REDIS_POD:-"redis-cache-0"}
RETENTION_DAYS=${RETENTION_DAYS:-30}
BACKUP_PREFIX="vertex-ai-backup"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parsear argumentos
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --action)
      ACTION="$2"
      shift
      shift
      ;;
    --backup-id)
      BACKUP_ID="$2"
      shift
      shift
      ;;
    --namespace)
      NAMESPACE="$2"
      shift
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help)
      echo "Uso: $0 [--action backup|restore|verify] [--backup-id BACKUP_ID] [--namespace NAMESPACE] [--dry-run]"
      echo ""
      echo "Opciones:"
      echo "  --action ACTION    Acción a realizar: backup, restore, verify (default: backup)"
      echo "  --backup-id BACKUP_ID    ID del backup para restaurar o verificar (requerido para restore/verify)"
      echo "  --namespace NAMESPACE    Namespace de Kubernetes (default: ngx-agents)"
      echo "  --dry-run    Ejecutar en modo simulación sin aplicar cambios"
      exit 0
      ;;
    *)
      echo "Opción desconocida: $1"
      echo "Usa --help para ver las opciones disponibles"
      exit 1
      ;;
  esac
done

# Función para imprimir mensajes con timestamp
log() {
  local level=$1
  local message=$2
  local color=$NC
  
  case $level in
    INFO)
      color=$BLUE
      ;;
    SUCCESS)
      color=$GREEN
      ;;
    WARNING)
      color=$YELLOW
      ;;
    ERROR)
      color=$RED
      ;;
  esac
  
  echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message${NC}"
}

# Función para verificar dependencias
check_dependencies() {
  local missing_deps=false
  
  # Verificar kubectl
  if ! command -v kubectl &> /dev/null; then
    log "ERROR" "kubectl no está disponible. Por favor, instálalo e inténtalo de nuevo."
    missing_deps=true
  fi
  
  # Verificar gcloud
  if ! command -v gcloud &> /dev/null; then
    log "ERROR" "gcloud no está disponible. Por favor, instálalo e inténtalo de nuevo."
    missing_deps=true
  fi
  
  # Verificar gsutil
  if ! command -v gsutil &> /dev/null; then
    log "ERROR" "gsutil no está disponible. Por favor, instálalo e inténtalo de nuevo."
    missing_deps=true
  fi
  
  # Verificar jq
  if ! command -v jq &> /dev/null; then
    log "ERROR" "jq no está disponible. Por favor, instálalo e inténtalo de nuevo."
    missing_deps=true
  fi
  
  if [[ "$missing_deps" == "true" ]]; then
    exit 1
  fi
  
  # Verificar acceso al cluster
  if ! kubectl get ns &> /dev/null; then
    log "ERROR" "No se puede acceder al cluster de Kubernetes. Verifica la configuración."
    exit 1
  fi
  
  # Verificar si el namespace existe
  if ! kubectl get ns $NAMESPACE &> /dev/null; then
    log "ERROR" "El namespace '$NAMESPACE' no existe."
    exit 1
  fi
  
  # Verificar acceso a GCP
  if ! gcloud auth print-access-token &> /dev/null; then
    log "ERROR" "No se puede autenticar con Google Cloud. Ejecuta 'gcloud auth login'."
    exit 1
  fi
  
  # Verificar acceso al bucket
  if ! gsutil ls $BACKUP_BUCKET &> /dev/null; then
    log "ERROR" "No se puede acceder al bucket de backups: $BACKUP_BUCKET"
    exit 1
  }
}

# Función para generar ID de backup
generate_backup_id() {
  echo "${BACKUP_PREFIX}-$(date '+%Y%m%d-%H%M%S')"
}

# Función para realizar backup de la base de datos
backup_database() {
  local backup_id=$1
  local backup_file="${backup_id}-database.sql.gz"
  local backup_path="${BACKUP_BUCKET}/${backup_file}"
  
  log "INFO" "Realizando backup de la base de datos..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando backup de base de datos a $backup_path"
    return 0
  fi
  
  # Exportar base de datos a Cloud Storage
  gcloud sql export sql $DB_INSTANCE $backup_path \
    --database=ngx_agents \
    --offload \
    --async
  
  # Esperar a que se complete la exportación
  local operation_id=$(gcloud sql operations list \
    --instance=$DB_INSTANCE \
    --filter="TYPE=EXPORT AND STATUS=RUNNING" \
    --format="value(name)" \
    | head -n 1)
  
  if [[ -n "$operation_id" ]]; then
    log "INFO" "Esperando a que se complete la exportación de la base de datos (operación: $operation_id)..."
    gcloud sql operations wait $operation_id --timeout=1800
  fi
  
  # Verificar que el archivo existe
  if gsutil stat $backup_path &> /dev/null; then
    log "SUCCESS" "Backup de base de datos completado: $backup_path"
    return 0
  else
    log "ERROR" "No se pudo crear el backup de la base de datos"
    return 1
  fi
}

# Función para realizar backup del estado de Redis
backup_redis() {
  local backup_id=$1
  local backup_file="${backup_id}-redis.rdb"
  local backup_path="${BACKUP_BUCKET}/${backup_file}"
  local temp_file="/tmp/${backup_file}"
  
  log "INFO" "Realizando backup del estado de Redis..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando backup de Redis a $backup_path"
    return 0
  fi
  
  # Ejecutar comando SAVE en Redis para forzar persistencia
  kubectl -n $NAMESPACE exec $REDIS_POD -- redis-cli SAVE
  
  # Copiar archivo RDB desde el pod
  kubectl -n $NAMESPACE cp ${REDIS_POD}:/data/dump.rdb $temp_file
  
  # Subir archivo a Cloud Storage
  gsutil cp $temp_file $backup_path
  
  # Eliminar archivo temporal
  rm -f $temp_file
  
  # Verificar que el archivo existe
  if gsutil stat $backup_path &> /dev/null; then
    log "SUCCESS" "Backup de Redis completado: $backup_path"
    return 0
  else
    log "ERROR" "No se pudo crear el backup de Redis"
    return 1
  fi
}

# Función para realizar backup de configuración
backup_config() {
  local backup_id=$1
  local backup_file="${backup_id}-config.json"
  local backup_path="${BACKUP_BUCKET}/${backup_file}"
  local temp_file="/tmp/${backup_file}"
  
  log "INFO" "Realizando backup de configuración..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando backup de configuración a $backup_path"
    return 0
  fi
  
  # Exportar ConfigMaps y Secrets
  kubectl -n $NAMESPACE get configmap vertex-ai-config -o json > $temp_file
  
  # Subir archivo a Cloud Storage
  gsutil cp $temp_file $backup_path
  
  # Eliminar archivo temporal
  rm -f $temp_file
  
  # Verificar que el archivo existe
  if gsutil stat $backup_path &> /dev/null; then
    log "SUCCESS" "Backup de configuración completado: $backup_path"
    return 0
  else
    log "ERROR" "No se pudo crear el backup de configuración"
    return 1
  fi
}

# Función para crear archivo de metadatos del backup
create_backup_metadata() {
  local backup_id=$1
  local backup_file="${backup_id}-metadata.json"
  local backup_path="${BACKUP_BUCKET}/${backup_file}"
  local temp_file="/tmp/${backup_file}"
  
  log "INFO" "Creando metadatos del backup..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando creación de metadatos a $backup_path"
    return 0
  fi
  
  # Crear archivo de metadatos
  cat > $temp_file << EOF
{
  "backup_id": "$backup_id",
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "namespace": "$NAMESPACE",
  "components": {
    "database": "${backup_id}-database.sql.gz",
    "redis": "${backup_id}-redis.rdb",
    "config": "${backup_id}-config.json"
  },
  "created_by": "$(whoami)",
  "version": "1.0"
}
EOF
  
  # Subir archivo a Cloud Storage
  gsutil cp $temp_file $backup_path
  
  # Eliminar archivo temporal
  rm -f $temp_file
  
  # Verificar que el archivo existe
  if gsutil stat $backup_path &> /dev/null; then
    log "SUCCESS" "Metadatos del backup creados: $backup_path"
    return 0
  else
    log "ERROR" "No se pudieron crear los metadatos del backup"
    return 1
  fi
}

# Función para realizar backup completo
perform_backup() {
  local backup_id=$(generate_backup_id)
  local success=true
  
  log "INFO" "Iniciando backup completo con ID: $backup_id"
  
  # Realizar backup de base de datos
  if ! backup_database $backup_id; then
    success=false
  fi
  
  # Realizar backup de Redis
  if ! backup_redis $backup_id; then
    success=false
  fi
  
  # Realizar backup de configuración
  if ! backup_config $backup_id; then
    success=false
  fi
  
  # Crear metadatos del backup
  if ! create_backup_metadata $backup_id; then
    success=false
  fi
  
  if [[ "$success" == "true" ]]; then
    log "SUCCESS" "Backup completo finalizado exitosamente con ID: $backup_id"
    
    # Limpiar backups antiguos
    cleanup_old_backups
    
    return 0
  else
    log "ERROR" "Backup completo finalizado con errores"
    return 1
  fi
}

# Función para limpiar backups antiguos
cleanup_old_backups() {
  local retention_date=$(date -d "$RETENTION_DAYS days ago" '+%Y%m%d')
  
  log "INFO" "Limpiando backups anteriores a $retention_date..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando limpieza de backups antiguos"
    return 0
  fi
  
  # Listar todos los backups
  local backups=$(gsutil ls "${BACKUP_BUCKET}/${BACKUP_PREFIX}-*.json" | grep -v metadata)
  
  for backup in $backups; do
    local backup_date=$(echo $backup | grep -o '[0-9]\{8\}')
    
    if [[ "$backup_date" < "$retention_date" ]]; then
      local backup_id=$(basename $backup .json)
      
      log "INFO" "Eliminando backup antiguo: $backup_id"
      
      # Eliminar archivos del backup
      gsutil rm "${BACKUP_BUCKET}/${backup_id}*" &> /dev/null || true
    fi
  done
  
  log "SUCCESS" "Limpieza de backups antiguos completada"
}

# Función para verificar integridad de un backup
verify_backup() {
  local backup_id=$1
  local metadata_file="${backup_id}-metadata.json"
  local metadata_path="${BACKUP_BUCKET}/${metadata_file}"
  local temp_file="/tmp/${metadata_file}"
  local success=true
  
  log "INFO" "Verificando integridad del backup: $backup_id"
  
  # Descargar archivo de metadatos
  if ! gsutil cp $metadata_path $temp_file &> /dev/null; then
    log "ERROR" "No se encontró el archivo de metadatos: $metadata_path"
    return 1
  fi
  
  # Leer componentes del backup
  local database_file=$(jq -r '.components.database' $temp_file)
  local redis_file=$(jq -r '.components.redis' $temp_file)
  local config_file=$(jq -r '.components.config' $temp_file)
  
  # Verificar que existen todos los archivos
  if ! gsutil stat "${BACKUP_BUCKET}/${database_file}" &> /dev/null; then
    log "ERROR" "Archivo de base de datos no encontrado: ${database_file}"
    success=false
  fi
  
  if ! gsutil stat "${BACKUP_BUCKET}/${redis_file}" &> /dev/null; then
    log "ERROR" "Archivo de Redis no encontrado: ${redis_file}"
    success=false
  fi
  
  if ! gsutil stat "${BACKUP_BUCKET}/${config_file}" &> /dev/null; then
    log "ERROR" "Archivo de configuración no encontrado: ${config_file}"
    success=false
  fi
  
  # Eliminar archivo temporal
  rm -f $temp_file
  
  if [[ "$success" == "true" ]]; then
    log "SUCCESS" "Verificación de integridad exitosa para el backup: $backup_id"
    return 0
  else
    log "ERROR" "Verificación de integridad fallida para el backup: $backup_id"
    return 1
  fi
}

# Función para restaurar un backup
restore_backup() {
  local backup_id=$1
  local metadata_file="${backup_id}-metadata.json"
  local metadata_path="${BACKUP_BUCKET}/${metadata_file}"
  local temp_dir="/tmp/${backup_id}"
  local success=true
  
  log "INFO" "Iniciando restauración del backup: $backup_id"
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando restauración del backup: $backup_id"
    return 0
  fi
  
  # Verificar integridad del backup
  if ! verify_backup $backup_id; then
    log "ERROR" "No se puede restaurar un backup con integridad comprometida"
    return 1
  fi
  
  # Crear directorio temporal
  mkdir -p $temp_dir
  
  # Descargar archivo de metadatos
  gsutil cp $metadata_path "${temp_dir}/${metadata_file}"
  
  # Leer componentes del backup
  local database_file=$(jq -r '.components.database' "${temp_dir}/${metadata_file}")
  local redis_file=$(jq -r '.components.redis' "${temp_dir}/${metadata_file}")
  local config_file=$(jq -r '.components.config' "${temp_dir}/${metadata_file}")
  
  # Descargar archivos
  gsutil cp "${BACKUP_BUCKET}/${database_file}" "${temp_dir}/${database_file}"
  gsutil cp "${BACKUP_BUCKET}/${redis_file}" "${temp_dir}/${redis_file}"
  gsutil cp "${BACKUP_BUCKET}/${config_file}" "${temp_dir}/${config_file}"
  
  # Restaurar base de datos
  log "INFO" "Restaurando base de datos..."
  gcloud sql import sql $DB_INSTANCE "${temp_dir}/${database_file}" \
    --database=ngx_agents \
    --quiet
  
  # Restaurar Redis
  log "INFO" "Restaurando estado de Redis..."
  kubectl -n $NAMESPACE scale deployment redis-cache --replicas=0
  sleep 10
  kubectl -n $NAMESPACE scale deployment redis-cache --replicas=1
  sleep 20
  kubectl -n $NAMESPACE cp "${temp_dir}/${redis_file}" ${REDIS_POD}:/data/dump.rdb
  kubectl -n $NAMESPACE exec $REDIS_POD -- redis-cli SHUTDOWN SAVE
  sleep 10
  
  # Restaurar configuración
  log "INFO" "Restaurando configuración..."
  kubectl -n $NAMESPACE apply -f "${temp_dir}/${config_file}"
  
  # Reiniciar servicios
  log "INFO" "Reiniciando servicios..."
  kubectl -n $NAMESPACE rollout restart deployment vertex-ai-optimizer
  
  # Limpiar archivos temporales
  rm -rf $temp_dir
  
  log "SUCCESS" "Restauración completada exitosamente desde el backup: $backup_id"
  log "INFO" "RTO (Recovery Time Objective) real: $(date -d @$SECONDS -u +%H:%M:%S)"
  
  return 0
}

# Función para listar backups disponibles
list_backups() {
  log "INFO" "Listando backups disponibles..."
  
  # Listar archivos de metadatos
  local metadata_files=$(gsutil ls "${BACKUP_BUCKET}/${BACKUP_PREFIX}-*-metadata.json" 2>/dev/null || echo "")
  
  if [[ -z "$metadata_files" ]]; then
    log "INFO" "No se encontraron backups disponibles"
    return 0
  fi
  
  echo -e "\nBackups disponibles:\n"
  echo -e "ID\t\t\t\tFecha\t\t\tTamaño\n"
  
  for file in $metadata_files; do
    local backup_id=$(basename $file -metadata.json)
    local timestamp=$(gsutil cat $file | jq -r '.timestamp')
    local date_formatted=$(date -d "$timestamp" '+%Y-%m-%d %H:%M:%S')
    
    # Calcular tamaño total del backup
    local size=0
    for component_file in $(gsutil ls "${BACKUP_BUCKET}/${backup_id}-*"); do
      local file_size=$(gsutil du $component_file | awk '{print $1}')
      size=$((size + file_size))
    done
    
    # Convertir a MB
    local size_mb=$(echo "scale=2; $size / 1024 / 1024" | bc)
    
    echo -e "${backup_id}\t${date_formatted}\t${size_mb} MB"
  done
  
  echo ""
}

# Función principal
main() {
  # Verificar dependencias
  check_dependencies
  
  case $ACTION in
    backup)
      perform_backup
      ;;
    restore)
      if [[ -z "$BACKUP_ID" ]]; then
        log "ERROR" "Se requiere un ID de backup para restaurar (--backup-id)"
        list_backups
        exit 1
      fi
      restore_backup $BACKUP_ID
      ;;
    verify)
      if [[ -z "$BACKUP_ID" ]]; then
        log "ERROR" "Se requiere un ID de backup para verificar (--backup-id)"
        list_backups
        exit 1
      fi
      verify_backup $BACKUP_ID
      ;;
    list)
      list_backups
      ;;
    *)
      log "ERROR" "Acción desconocida: $ACTION"
      echo "Acciones válidas: backup, restore, verify, list"
      exit 1
      ;;
  esac
}

# Ejecutar función principal
main