#!/bin/bash

# Script de herramientas de desarrollo para InfluxDB Backup System
# Facilita el manejo de contenedores de desarrollo y producción

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo "📦 InfluxDB Backup System - Herramientas de Desarrollo"
    echo ""
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponibles:"
    echo "  dev-build     Construir imagen de desarrollo"
    echo "  dev-up        Levantar entorno de desarrollo"
    echo "  dev-shell     Entrar al shell del contenedor de desarrollo"
    echo "  dev-test      Ejecutar tests en el contenedor de desarrollo"
    echo "  dev-down      Parar entorno de desarrollo"
    echo ""
    echo "  prod-build    Construir imagen de producción"
    echo "  prod-up       Levantar entorno de producción"
    echo "  prod-down     Parar entorno de producción"
    echo ""
    echo "  clean         Limpiar imágenes no utilizadas"
    echo "  logs          Ver logs del servicio"
    echo "  help          Mostrar esta ayuda"
}

# Función para logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Verificar que estamos en el directorio del proyecto
if [[ ! -f "docker-compose.yaml" ]]; then
    error "Este script debe ejecutarse desde el directorio raíz del proyecto"
    exit 1
fi

case "$1" in
    "dev-build")
        log "🔨 Construyendo imagen de desarrollo..."
        docker-compose build --no-cache sysadmintoolkit-backup-service-dev
        log "✅ Imagen de desarrollo construida"
        ;;

    "dev-up")
        log "🚀 Levantando entorno de desarrollo..."
        docker-compose --profile development up -d
        log "✅ Entorno de desarrollo activo"
        log "💡 Usa '$0 dev-shell' para entrar al contenedor"
        ;;

    "dev-shell")
        log "🐚 Entrando al shell del contenedor de desarrollo..."
        docker-compose exec sysadmintoolkit-backup-service-dev bash
        ;;

    "dev-test")
        log "🧪 Ejecutando tests en el contenedor de desarrollo..."
        docker-compose exec sysadmintoolkit-backup-service-dev python -m pytest test/ -v
        ;;

    "dev-down")
        log "⬇️ Parando entorno de desarrollo..."
        docker-compose --profile development down
        log "✅ Entorno de desarrollo parado"
        ;;

    "prod-build")
        log "🔨 Construyendo imagen de producción..."
        docker-compose build --no-cache sysadmintoolkit-backup-service-prod
        log "✅ Imagen de producción construida"
        ;;

    "prod-up")
        log "🚀 Levantando entorno de producción..."
        docker-compose --profile production up -d
        log "✅ Entorno de producción activo"
        ;;

    "prod-down")
        log "⬇️ Parando entorno de producción..."
        docker-compose --profile production down
        log "✅ Entorno de producción parado"
        ;;

    "clean")
        log "🧹 Limpiando imágenes no utilizadas..."
        docker system prune -f
        docker image prune -f
        log "✅ Limpieza completada"
        ;;

    "logs")
        SERVICE=${2:-sysadmintoolkit-backup-service-dev}
        log "📋 Mostrando logs de $SERVICE..."
        docker-compose logs -f $SERVICE
        ;;

    "help"|"--help"|"-h"|"")
        show_help
        ;;

    *)
        error "Comando desconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
