#!/bin/bash

# Script para configurar credenciales de Git en el contenedor
# Uso: ./scripts/setup-git-credentials.sh

set -e

echo "=== Configuración de Credenciales de Git ==="
echo ""

# Verificar si existe el archivo .env
if [ ! -f .env ]; then
    echo "❌ No se encontró el archivo .env"
    echo "📝 Creando .env desde .env.example..."

    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env creado desde .env.example"
    else
        echo "📝 Creando .env básico..."
        cat > .env << 'EOF'
# Configuración de Git para el contenedor de desarrollo
GIT_USER_NAME="Tu Nombre"
GIT_USER_EMAIL="tu.email@example.com"
GIT_DEFAULT_BRANCH="main"
GIT_TOKEN=""

# Otras variables de entorno
INFLUXDB_NETWORK=influxdb-network
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
EOF
        echo "✅ .env básico creado"
    fi
    echo ""
fi

echo "📋 Configuración actual del .env:"
echo "--------------------------------"
grep -E "^(GIT_|INFLUXDB_|GF_)" .env || echo "No hay variables configuradas"
echo ""

echo "🔧 Para configurar Git:"
echo "1. Edita el archivo .env"
echo "2. Configura las variables GIT_*"
echo "3. Para el GIT_TOKEN, usa un Personal Access Token de GitHub"
echo ""

echo "🚀 Para aplicar los cambios:"
echo "docker-compose build sysadmintoolkit-backup-service-dev"
echo "docker-compose --profile development up -d"
echo ""

echo "🔍 Para verificar la configuración:"
echo "docker-compose --profile development exec sysadmintoolkit-backup-service-dev git config --list --global"
echo ""

echo "⚠️  IMPORTANTE: Nunca subas el archivo .env al repositorio"
echo "   El .env ya está en .gitignore por seguridad"
echo ""
