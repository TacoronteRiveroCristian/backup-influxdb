#!/bin/bash

# Script para limpiar servicios Docker de testing
# Uso: ./test/cleanup_test_services.sh

set -e

echo "🧹 Limpiando servicios Docker de testing..."

# Navegar al directorio de Docker
cd "$(dirname "$0")/docker"

echo "  → Parando contenedores con docker-compose..."
docker-compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || echo "    (docker-compose no encontró contenedores activos)"

echo "  → Eliminando contenedores específicos por nombre..."
CONTAINERS=("influxdb_source_test" "influxdb_destination_test" "influxdb_extra_test" "influxdb_test_runner")

for container in "${CONTAINERS[@]}"; do
    if docker ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
        echo "    Eliminando: $container"
        docker rm -f "$container" 2>/dev/null || echo "    (no se pudo eliminar $container)"
    fi
done

echo "  → Limpiando redes de test..."
docker network rm influxdb_test_network 2>/dev/null || echo "    (red influxdb_test_network ya eliminada o no existe)"

# Para docker_influxdb_test_network, verificar si tiene contenedores de desarrollo conectados
if docker network inspect docker_influxdb_test_network >/dev/null 2>&1; then
    if docker network inspect docker_influxdb_test_network | grep -q "sysadmintoolkit\|dev"; then
        echo "    (manteniendo red docker_influxdb_test_network - contiene contenedor de desarrollo)"
    else
        docker network rm docker_influxdb_test_network 2>/dev/null || echo "    (no se pudo eliminar red docker_influxdb_test_network)"
    fi
else
    echo "    (red docker_influxdb_test_network ya eliminada o no existe)"
fi

echo "  → Limpiando volúmenes no utilizados..."
docker volume prune -f 2>/dev/null || echo "    (sin volúmenes para limpiar)"

echo "  → Verificando contenedores activos..."
REMAINING=$(docker ps --filter "name=test" --format "{{.Names}}" 2>/dev/null || true)

if [ -n "$REMAINING" ]; then
    echo "  ⚠️  WARNING: Contenedores aún activos: $REMAINING"
else
    echo "  ✅ Todos los contenedores de test eliminados"
fi

echo ""
echo "✅ Limpieza Docker completada"
echo ""
echo "Para verificar que no hay contenedores activos:"
echo "  docker ps --filter 'name=test'"
echo ""
echo "Para eliminar TODOS los contenedores y volúmenes (¡CUIDADO!):"
echo "  docker system prune -a --volumes"
