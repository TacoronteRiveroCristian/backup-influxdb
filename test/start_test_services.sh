#!/bin/bash

# Script para iniciar los servicios de testing de InfluxDB
# Uso: ./test/start_test_services.sh

set -e

echo "🐳 Iniciando servicios de testing de InfluxDB..."

# Navegar al directorio de Docker
cd "$(dirname "$0")/docker"

# Limpiar contenedores anteriores
echo "🧹 Limpiando contenedores anteriores..."
docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true

# Levantar los servicios
echo "⚡ Levantando servicios..."
docker-compose -f docker-compose.test.yml up -d

# Esperar a que estén healthy
echo "⏳ Esperando a que los servicios estén listos..."
for i in {1..30}; do
    if docker-compose -f docker-compose.test.yml ps | grep -q "Up (healthy).*Up (healthy).*Up (healthy)"; then
        echo "✅ Servicios listos!"
        break
    fi
    echo "   Intento $i/30..."
    sleep 2
done

# Verificar conectividad
echo "🔍 Verificando conectividad..."
if docker exec influxdb_test_runner curl -f http://influxdb_source_test:8086/ping >/dev/null 2>&1 && \
   docker exec influxdb_test_runner curl -f http://influxdb_destination_test:8086/ping >/dev/null 2>&1; then
    echo "✅ Servicios disponibles y funcionando correctamente"
    echo ""
    echo "📋 Variables de entorno recomendadas:"
    echo "export INFLUXDB_SOURCE_URL=http://influxdb_source_test:8086"
    echo "export INFLUXDB_DESTINATION_URL=http://influxdb_destination_test:8086"
    echo "export INFLUXDB_USER=admin"
    echo "export INFLUXDB_PASSWORD=password"
    echo "export TESTING=true"
    echo ""
    echo "🚀 Para ejecutar tests:"
    echo "python test/run_tests.py"
else
    echo "❌ Error: Los servicios no responden correctamente"
    exit 1
fi
