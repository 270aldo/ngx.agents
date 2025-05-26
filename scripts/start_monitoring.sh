#!/bin/bash

# Script para iniciar el stack de monitoreo de NGX Agents

set -e

echo "🚀 Iniciando stack de monitoreo para NGX Agents..."

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

# Verificar que docker-compose esté instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose no está instalado. Por favor instala docker-compose primero."
    exit 1
fi

# Cambiar al directorio de monitoreo
cd "$(dirname "$0")/../monitoring"

# Verificar si los servicios ya están corriendo
if docker-compose ps | grep -q "Up"; then
    echo "⚠️  Algunos servicios ya están corriendo. Deteniéndolos primero..."
    docker-compose down
fi

# Iniciar servicios
echo "📦 Iniciando servicios de monitoreo..."
docker-compose up -d

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

# Verificar que los servicios estén corriendo
echo "✅ Verificando servicios..."
docker-compose ps

# Mostrar URLs de acceso
echo ""
echo "🎉 Stack de monitoreo iniciado exitosamente!"
echo ""
echo "📊 URLs de acceso:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Alertmanager: http://localhost:9093"
echo ""
echo "📈 Dashboards disponibles en Grafana:"
echo "  - NGX Agents Overview"
echo ""
echo "💡 Para ver los logs:"
echo "  docker-compose logs -f [servicio]"
echo ""
echo "🛑 Para detener los servicios:"
echo "  cd monitoring && docker-compose down"