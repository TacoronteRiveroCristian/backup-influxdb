#!/bin/bash

# Script para configurar credenciales de Git en el contenedor de desarrollo
# Este script facilita la configuración inicial del entorno de desarrollo

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verificar si existe .env
if [ ! -f ".env" ]; then
    echo "No se encontró el archivo .env"
    echo "Creando .env desde .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Archivo .env creado desde .env.example"
    else
        echo "Creando .env básico..."
        cat > .env << 'EOF'
# Configuración de Git para desarrollo
GIT_USER_NAME="Developer"
GIT_USER_EMAIL="developer@example.com"

# Configuración opcional de InfluxDB para desarrollo
INFLUX_HOST=localhost
INFLUX_PORT=8086
INFLUX_USER=admin
INFLUX_PASS=password
INFLUX_DB=test_db

# Configuración de logs
LOG_LEVEL=INFO
LOG_FILE_PATH=./volumes/logs/
EOF
        echo "Archivo .env básico creado"
    fi
fi

echo ""
echo "Configuración actual del .env:"
echo "==============================================="
cat .env | grep -E "^(GIT_|#)" || true
echo "==============================================="

echo ""
echo "Para configurar Git:"
echo "  1. Edita el archivo .env"
echo "  2. Cambia GIT_USER_NAME y GIT_USER_EMAIL"
echo "  3. Guarda el archivo"
echo ""
echo "Para aplicar los cambios:"
echo "  ./scripts/dev-tools.sh dev-down"
echo "  ./scripts/dev-tools.sh dev-up"
echo ""
echo "Para verificar la configuración:"
echo "  ./scripts/dev-tools.sh dev-shell"
echo "  git config --list"
echo ""
echo "IMPORTANTE: Nunca subas el archivo .env al repositorio"
