#!/bin/bash

# Script de herramientas de desarrollo para el sistema de backup InfluxDB
# Automatiza tareas comunes de desarrollo, testing y despliegue

set -e

PROJECT_NAME="backup-influxdb"
COMPOSE_FILE="docker-compose.yaml"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "InfluxDB Backup System - Herramientas de Desarrollo"
echo "=================================================="

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

show_help() {
    cat << EOF
Uso: $0 <comando>

Comandos disponibles:
  build-dev     Construir imagen de desarrollo
  build-prod    Construir imagen de producción
  build-all     Construir todas las imágenes
  dev-up        Levantar entorno de desarrollo
  dev-down      Parar entorno de desarrollo
  dev-shell     Acceder al shell del contenedor de desarrollo
  prod-up       Levantar entorno de producción
  prod-down     Parar entorno de producción
  clean         Limpiar imágenes y contenedores
  logs          Mostrar logs (usar: $0 logs [servicio])
  test          Ejecutar tests en contenedor
  help          Mostrar esta ayuda

Ejemplos:
  $0 build-dev
  $0 dev-up
  $0 logs backup-service
  $0 clean
EOF
}

build_dev() {
    log "Construyendo imagen de desarrollo..."
    docker-compose build --target development backup-service
    log "Imagen de desarrollo construida"
}

dev_up() {
    log "Levantando entorno de desarrollo..."
    docker-compose --profile development up -d
    log "Entorno de desarrollo activo"
    log "Usa '$0 dev-shell' para entrar al contenedor"
}

dev_down() {
    log "Parando entorno de desarrollo..."
    docker-compose --profile development down
    log "Entorno de desarrollo parado"
}

dev_shell() {
    docker-compose --profile development exec backup-service bash
}

build_prod() {
    log "Construyendo imagen de producción..."
    docker-compose build --target production-scheduler backup-service
    log "Imagen de producción construida"
}

prod_up() {
    log "Levantando entorno de producción..."
    docker-compose --profile production up -d
    log "Entorno de producción activo"
}

prod_down() {
    log "Parando entorno de producción..."
    docker-compose --profile production down
    log "Entorno de producción parado"
}

clean() {
    log "Limpiando imágenes y contenedores..."
    docker-compose down --volumes --remove-orphans
    docker system prune -f
    log "Limpieza completada"
}

show_logs() {
    SERVICE=${1:-""}
    log "Mostrando logs de $SERVICE..."
    if [ -z "$SERVICE" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$SERVICE"
    fi
}

run_tests() {
    log "Ejecutando tests en contenedor..."
    docker-compose --profile development exec backup-service python -m pytest test/ -v
}

build_all() {
    log "Construyendo todas las imágenes..."
    build_dev
    build_prod
    log "Todas las imágenes construidas"
}

# Función principal
main() {
    case "$1" in
        "build-dev")
            build_dev
            ;;
        "build-prod")
            build_prod
            ;;
        "build-all")
            build_all
            ;;
        "dev-up")
            dev_up
            ;;
        "dev-down")
            dev_down
            ;;
        "dev-shell")
            dev_shell
            ;;
        "prod-up")
            prod_up
            ;;
        "prod-down")
            prod_down
            ;;
        "clean")
            clean
            ;;
        "logs")
            show_logs "$2"
            ;;
        "test")
            run_tests
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            error "Comando no reconocido: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Verificar que docker esté disponible
if ! command -v docker &> /dev/null; then
    error "Docker no está instalado o no está en el PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose no está instalado o no está en el PATH"
    exit 1
fi

# Ejecutar función principal con todos los argumentos
main "$@"
