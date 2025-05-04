#!/bin/bash
# Script para iniciar el entorno de desarrollo de NGX Agents
# Inicia el servidor A2A, los agentes y la API FastAPI en procesos separados

# Colores para los mensajes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directorio base del proyecto
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR" || exit 1

# Verificar que Poetry esté instalado
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: Poetry no está instalado.${NC}"
    echo "Instala Poetry siguiendo las instrucciones en https://python-poetry.org/docs/#installation"
    exit 1
fi

# Verificar que el entorno virtual esté activado
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Activando entorno virtual de Poetry...${NC}"
    eval "$(poetry env info --path)/bin/activate" || {
        echo -e "${RED}Error: No se pudo activar el entorno virtual.${NC}"
        echo "Ejecuta 'poetry shell' antes de ejecutar este script."
        exit 1
    }
fi

# Cargar variables de entorno
if [ -f .env ]; then
    echo -e "${BLUE}Cargando variables de entorno desde .env${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${YELLOW}Archivo .env no encontrado. Usando valores por defecto.${NC}"
fi

# Función para matar todos los procesos al salir
cleanup() {
    echo -e "\n${YELLOW}Deteniendo todos los procesos...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Registrar la función de limpieza para señales de terminación
trap cleanup SIGINT SIGTERM

# Iniciar el servidor A2A
echo -e "${GREEN}Iniciando servidor A2A...${NC}"
python -m infrastructure.a2a_server &
A2A_PID=$!
echo -e "${BLUE}Servidor A2A iniciado con PID: $A2A_PID${NC}"

# Esperar a que el servidor A2A esté listo (5 segundos)
echo -e "${YELLOW}Esperando a que el servidor A2A esté listo...${NC}"
sleep 5

# Iniciar los agentes principales
echo -e "${GREEN}Iniciando agentes...${NC}"

# Agente Orchestrator
echo -e "${BLUE}Iniciando Orchestrator...${NC}"
python -m agents.orchestrator.run &
ORCHESTRATOR_PID=$!
echo -e "${BLUE}Orchestrator iniciado con PID: $ORCHESTRATOR_PID${NC}"

# Agente ProgressTracker
echo -e "${BLUE}Iniciando ProgressTracker...${NC}"
python -m agents.progress_tracker.run &
PROGRESS_TRACKER_PID=$!
echo -e "${BLUE}ProgressTracker iniciado con PID: $PROGRESS_TRACKER_PID${NC}"

# Agente GeminiTrainingAssistant
echo -e "${BLUE}Iniciando GeminiTrainingAssistant...${NC}"
python -m agents.gemini_training_assistant.run &
TRAINING_ASSISTANT_PID=$!
echo -e "${BLUE}GeminiTrainingAssistant iniciado con PID: $TRAINING_ASSISTANT_PID${NC}"

# Agente MotivationBehaviorCoach
echo -e "${BLUE}Iniciando MotivationBehaviorCoach...${NC}"
python -m agents.motivation_behavior_coach.run &
MOTIVATION_COACH_PID=$!
echo -e "${BLUE}MotivationBehaviorCoach iniciado con PID: $MOTIVATION_COACH_PID${NC}"

# Iniciar la API FastAPI
echo -e "${GREEN}Iniciando API FastAPI...${NC}"
uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --reload &
API_PID=$!
echo -e "${BLUE}API FastAPI iniciada con PID: $API_PID${NC}"

# Mostrar mensaje de éxito
echo -e "\n${GREEN}¡Entorno de desarrollo iniciado correctamente!${NC}"
echo -e "${BLUE}Servidor A2A:${NC} http://localhost:9000"
echo -e "${BLUE}API FastAPI:${NC} http://localhost:${PORT:-8000}"
echo -e "${YELLOW}Presiona Ctrl+C para detener todos los procesos${NC}\n"

# Esperar a que el usuario presione Ctrl+C
wait
