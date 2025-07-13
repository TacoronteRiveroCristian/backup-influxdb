#!/bin/bash

# =====================================================================================
# GESTOR COMPLETO - INFLUXDB BACKUP SYSTEM
# =====================================================================================
# Script todo-en-uno para gestionar el sistema de backup InfluxDB
#
# FUNCIONES DISPONIBLES:
#   ./scripts/quick-start.sh setup [development|production]     # Configuración inicial
#   ./scripts/quick-start.sh start [development|production]     # Iniciar servicios
#   ./scripts/quick-start.sh stop [development|production]      # Parar servicios
#   ./scripts/quick-start.sh restart [development|production]   # Reiniciar servicios
#   ./scripts/quick-start.sh logs [development|production]      # Ver logs
#   ./scripts/quick-start.sh status [development|production]    # Estado de servicios
#   ./scripts/quick-start.sh cleanup                           # Limpiar todo
#   ./scripts/quick-start.sh backup                            # Ejecutar backup manual
#   ./scripts/quick-start.sh shell [development|production]     # Acceder al contenedor
#   ./scripts/quick-start.sh validate                          # Validar configuración
#   ./scripts/quick-start.sh help                              # Mostrar ayuda

set -e

# Detectar si el terminal soporta colores
if [[ -t 1 ]] && [[ "${TERM:-}" != "dumb" ]] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1 && [[ $(tput colors) -ge 8 ]]; then
    # Terminal soporta colores
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
    USE_COLORS=true
else
    # Terminal no soporta colores o estamos redirigiendo output
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
    NC=''
    USE_COLORS=false
fi

# Función para logging
log() {
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    fi
}

success() {
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo "✓ $1"
    fi
}

warning() {
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "${YELLOW}⚠${NC} $1"
    else
        echo "⚠ $1"
    fi
}

error() {
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "${RED}✗${NC} $1"
    else
        echo "✗ $1"
    fi
    exit 1
}

info() {
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "${CYAN}ℹ${NC} $1"
    else
        echo "ℹ $1"
    fi
}

bold() {
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "${BOLD}$1${NC}"
    else
        echo "$1"
    fi
}

# Directorio del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Función para mostrar ayuda
show_help() {
    bold "GESTOR INFLUXDB BACKUP SYSTEM"
    echo ""
    echo "Uso: $0 <comando> [perfil] [archivo_config]"
    echo ""
    echo "📋 COMANDOS DISPONIBLES:"
    echo ""
    if [[ "$USE_COLORS" == "true" ]]; then
        echo -e "  ${CYAN}setup${NC} [development|production]     Configuración inicial completa"
        echo -e "  ${CYAN}start${NC} [development|production]     Iniciar servicios"
        echo -e "  ${CYAN}stop${NC} [development|production]      Parar servicios"
        echo -e "  ${CYAN}restart${NC} [development|production]   Reiniciar servicios"
        echo -e "  ${CYAN}logs${NC} [development|production]      Ver logs en tiempo real"
        echo -e "  ${CYAN}status${NC} [development|production]    Estado de servicios"
        echo -e "  ${CYAN}cleanup${NC}                           Limpiar todo (contenedores, volúmenes, redes)"
        echo -e "  ${CYAN}backup${NC} [archivo_config]           Ejecutar backup manual"
        echo -e "  ${CYAN}shell${NC} [development|production]     Acceder al contenedor interactivo"
        echo -e "  ${CYAN}validate${NC} [archivo_config]         Validar configuración específica"
        echo -e "  ${CYAN}list-configs${NC}                      Listar archivos de configuración disponibles"
        echo -e "  ${CYAN}help${NC}                              Mostrar esta ayuda"
    else
        echo "  setup [development|production]     Configuración inicial completa"
        echo "  start [development|production]     Iniciar servicios"
        echo "  stop [development|production]      Parar servicios"
        echo "  restart [development|production]   Reiniciar servicios"
        echo "  logs [development|production]      Ver logs en tiempo real"
        echo "  status [development|production]    Estado de servicios"
        echo "  cleanup                           Limpiar todo (contenedores, volúmenes, redes)"
        echo "  backup [archivo_config]           Ejecutar backup manual"
        echo "  shell [development|production]     Acceder al contenedor interactivo"
        echo "  validate [archivo_config]         Validar configuración específica"
        echo "  list-configs                      Listar archivos de configuración disponibles"
        echo "  help                              Mostrar esta ayuda"
    fi
    echo ""
    echo "🔧 EJEMPLOS:"
    echo ""
    echo "  $0 setup development               # Primera configuración para desarrollo"
    echo "  $0 start development               # Iniciar servicios de desarrollo"
    echo "  $0 list-configs                    # Ver configuraciones disponibles"
    echo "  $0 validate mi_config.yaml         # Validar configuración específica"
    echo "  $0 backup production_backup.yaml   # Backup con configuración específica"
    echo "  $0 cleanup                         # Limpiar todo el sistema"
    echo ""
    echo "📁 ARCHIVOS DE CONFIGURACIÓN:"
    echo ""
    echo "  El sistema busca archivos .yaml/.yml en config/"
    echo "  Si no especificas archivo, se muestra lista para elegir"
    echo ""
    echo "💡 PARA EXPERTOS:"
    echo ""
    echo "  También puedes usar docker-compose directamente:"
    echo "  docker-compose --profile development up -d"
    echo "  docker-compose --profile production up -d"
    echo ""
}

# Función para encontrar archivos de configuración
find_config_files() {
    find config/ -name "*.yaml" -o -name "*.yml" 2>/dev/null | sort
}

# Función para listar archivos de configuración
list_config_files() {
    log "Archivos de configuración disponibles:"
    echo ""

    local configs=($(find_config_files))

    if [[ ${#configs[@]} -eq 0 ]]; then
        warning "No se encontraron archivos de configuración (.yaml/.yml) en config/"
        echo ""
        echo "Para crear uno:"
        echo "  cp config/backup_config.yaml.example config/mi_config.yaml"
        echo "  cp config/backup_config.yaml.template config/mi_config.yaml"
        return 1
    fi

    echo "📁 Archivos encontrados:"
    for i in "${!configs[@]}"; do
        local file="${configs[$i]}"
        local filename=$(basename "$file")
        local size=$(du -h "$file" 2>/dev/null | cut -f1)
        echo "  [$((i+1))] $filename ($size)"
    done
    echo ""
    return 0
}



# Verificar argumentos
COMMAND=${1:-help}

# Para algunos comandos, el segundo argumento puede ser el archivo de configuración
if [[ "$COMMAND" == "validate" ]] || [[ "$COMMAND" == "backup" ]]; then
    # Para validate y backup, el segundo argumento puede ser el archivo de configuración
    if [[ -n "$2" ]] && [[ "$2" != "development" ]] && [[ "$2" != "production" ]]; then
        CONFIG_FILE="$2"
        PROFILE="development"  # default
    else
        PROFILE=${2:-development}
        CONFIG_FILE=${3:-""}
    fi
else
    PROFILE=${2:-development}
    CONFIG_FILE=${3:-""}
fi

if [[ "$PROFILE" != "development" && "$PROFILE" != "production" && "$COMMAND" != "cleanup" && "$COMMAND" != "backup" && "$COMMAND" != "validate" && "$COMMAND" != "help" && "$COMMAND" != "list-configs" ]]; then
    error "Perfil debe ser 'development' o 'production'"
fi

# Función para verificar dependencias
check_dependencies() {
    log "Verificando dependencias..."

    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        error "Docker no está instalado. Instala Docker y vuelve a intentar."
    fi

    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose no está instalado. Instala Docker Compose y vuelve a intentar."
    fi

    # Verificar que Docker esté corriendo
    if ! docker info &> /dev/null; then
        error "Docker no está corriendo. Inicia Docker y vuelve a intentar."
    fi

    success "Docker y Docker Compose disponibles"
}

# Función para crear directorios
create_directories() {
    log "Creando directorios de volúmenes..."

    mkdir -p volumes/backup_logs
    mkdir -p volumes/influxdb/data
    mkdir -p volumes/grafana/data
    mkdir -p volumes/loki/data
    mkdir -p volumes/loki/config

    # Configurar permisos
    chmod 755 volumes/backup_logs
    chmod 777 volumes/influxdb/data
    chmod 777 volumes/grafana/data
    chmod 777 volumes/loki/data

    success "Directorios de volúmenes creados"
}

# Función para configurar archivos
setup_configuration() {
    log "Configurando archivos de configuración..."

    # Configurar archivo de configuración principal
    if [[ ! -f "config/backup_config.yaml" ]]; then
        if [[ -f "config/backup_config.yaml.example" ]]; then
            cp config/backup_config.yaml.example config/backup_config.yaml
            success "Configuración copiada desde ejemplo"
        else
            cp config/backup_config.yaml.template config/backup_config.yaml
            warning "Configuración copiada desde template. Revisa y personaliza config/backup_config.yaml"
        fi
    else
        info "Archivo de configuración ya existe: config/backup_config.yaml"
    fi

    # Configurar variables de entorno
    if [[ ! -f ".env" ]]; then
        cat > .env << 'EOF'
# Configuración de red
INFLUXDB_NETWORK=influxdb-network

# Configuración de Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin

# Configuración de Git (solo para desarrollo)
GIT_USER_NAME=Developer
GIT_USER_EMAIL=dev@example.com
GIT_DEFAULT_BRANCH=main
EOF
        success "Archivo .env creado"
    else
        info "Archivo .env ya existe"
    fi
}

# Función para construir imágenes
build_images() {
    log "Construyendo imágenes Docker para $PROFILE..."

    if [[ "$PROFILE" == "development" ]]; then
        docker-compose build --target development sysadmintoolkit-backup-service-dev
    else
        docker-compose build --target production sysadmintoolkit-backup-service-prod
    fi

    success "Imágenes Docker construidas"
}

# Función para crear red
create_network() {
    log "Configurando red Docker..."

    if ! docker network ls | grep -q "influxdb-network"; then
        docker network create influxdb-network
        success "Red Docker 'influxdb-network' creada"
    else
        info "Red Docker 'influxdb-network' ya existe"
    fi
}

# Función para iniciar servicios
start_services() {
    log "Iniciando servicios para perfil: $PROFILE"

    # Verificar que existe al menos una configuración
    local configs=($(find_config_files))
    if [[ ${#configs[@]} -eq 0 ]]; then
        error "No hay archivos de configuración. Ejecuta: $0 setup $PROFILE"
    fi

    docker-compose --profile $PROFILE up -d

    # Esperar a que los servicios estén listos
    log "Esperando a que los servicios estén listos..."
    if [[ "$PROFILE" == "development" ]]; then
        sleep 30
    else
        sleep 15
    fi

    # Verificar servicios
    if docker-compose --profile $PROFILE ps | grep -q "Up"; then
        success "Servicios de $PROFILE iniciados"
        show_services_info
    else
        error "Error iniciando servicios de $PROFILE"
    fi
}

# Función para mostrar información de servicios
show_services_info() {
    if [[ "$PROFILE" == "development" ]]; then
        echo ""
        bold "🚀 SERVICIOS DE DESARROLLO ACTIVOS"
        echo ""
        echo "📊 Servicios disponibles:"
        echo "  • InfluxDB: http://localhost:8086"
        echo "  • Grafana: http://localhost:3000 (admin/admin)"
        echo "  • Loki: http://localhost:3100"
        echo "  • Backup Service: Contenedor interactivo"
        echo ""
        echo "🔧 Comandos útiles:"
        echo "  • Ver logs: $0 logs development"
        echo "  • Ejecutar backup: $0 backup"
        echo "  • Acceder al contenedor: $0 shell development"
        echo "  • Parar servicios: $0 stop development"
        echo ""
    else
        echo ""
        bold "🎯 SERVICIO DE PRODUCCIÓN ACTIVO"
        echo ""
        echo "📊 Servicio:"
        echo "  • Backup Service: Ejecutándose automáticamente"
        echo ""
        echo "🔧 Comandos útiles:"
        echo "  • Ver logs: $0 logs production"
        echo "  • Ejecutar backup manual: $0 backup"
        echo "  • Verificar estado: $0 status production"
        echo "  • Parar servicio: $0 stop production"
        echo ""
    fi
}

# Función para parar servicios
stop_services() {
    log "Parando servicios de $PROFILE..."

    docker-compose --profile $PROFILE down

    success "Servicios de $PROFILE parados"
}

# Función para reiniciar servicios
restart_services() {
    log "Reiniciando servicios de $PROFILE..."

    stop_services
    sleep 3
    start_services

    success "Servicios de $PROFILE reiniciados"
}

# Función para mostrar logs
show_logs() {
    log "Mostrando logs de $PROFILE..."
    echo ""
    info "Presiona Ctrl+C para salir"
    echo ""

    docker-compose --profile $PROFILE logs -f
}

# Función para mostrar estado
show_status() {
    log "Estado de servicios de $PROFILE:"
    echo ""

    docker-compose --profile $PROFILE ps
    echo ""

    # Mostrar uso de recursos
    if docker-compose --profile $PROFILE ps | grep -q "Up"; then
        echo "💾 Uso de recursos:"
        if [[ "$PROFILE" == "development" ]]; then
            docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
                sysadmintoolkit-influxdb-dev sysadmintoolkit-grafana-dev sysadmintoolkit-loki-dev sysadmintoolkit-backup-service-dev 2>/dev/null || true
        else
            docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
                sysadmintoolkit-backup-service-prod 2>/dev/null || true
        fi
    else
        warning "No hay servicios ejecutándose"
    fi
}

# Función para limpiar todo
cleanup_all() {
    log "Limpiando todo el sistema..."

    # Parar todos los servicios
    docker-compose --profile development down -v 2>/dev/null || true
    docker-compose --profile production down -v 2>/dev/null || true

    # Limpiar contenedores específicos
    docker rm -f sysadmintoolkit-influxdb-dev sysadmintoolkit-grafana-dev sysadmintoolkit-loki-dev sysadmintoolkit-backup-service-dev sysadmintoolkit-backup-service-prod 2>/dev/null || true

    # Limpiar red
    docker network rm influxdb-network 2>/dev/null || true

    # Limpiar volúmenes no utilizados
    docker volume prune -f 2>/dev/null || true

    # Limpiar imágenes no utilizadas
    docker image prune -f 2>/dev/null || true

    success "Sistema limpiado completamente"

    warning "Para empezar de nuevo, ejecuta: $0 setup [development|production]"
}

# Función para ejecutar backup
run_backup() {
    # Determinar qué archivo usar
    local config_file=""
    local filename=""

    if [[ -n "$CONFIG_FILE" ]]; then
        # Se especificó un archivo
        if [[ -f "config/$CONFIG_FILE" ]]; then
            config_file="config/$CONFIG_FILE"
            filename="$CONFIG_FILE"
        elif [[ -f "$CONFIG_FILE" ]]; then
            config_file="$CONFIG_FILE"
            filename=$(basename "$CONFIG_FILE")
        else
            error "Archivo de configuración no encontrado: $CONFIG_FILE"
        fi
    else
        # No se especificó archivo, buscar automáticamente
        local configs
        configs=($(find config/ -name "*.yaml" -o -name "*.yml" 2>/dev/null | sort))

        if [[ ${#configs[@]} -eq 0 ]]; then
            error "No hay archivos de configuración. Ejecuta: $0 setup [development|production]"
        elif [[ ${#configs[@]} -eq 1 ]]; then
            config_file="${configs[0]}"
            filename=$(basename "$config_file")
        else
            # Hay múltiples, mostrar lista
            list_config_files
            warning "Hay múltiples archivos de configuración. Especifica cuál usar para backup:"
            echo ""
            echo "Ejemplos:"
            for config in "${configs[@]}"; do
                local fname=$(basename "$config")
                echo "  $0 backup $fname"
            done
            echo ""
            exit 1
        fi
    fi

    log "Ejecutando backup manual con: $filename"

    # Determinar qué perfil está activo
    if docker-compose --profile development ps | grep -q "Up"; then
        ACTIVE_PROFILE="development"
        CONTAINER="sysadmintoolkit-backup-service-dev"
    elif docker-compose --profile production ps | grep -q "Up"; then
        ACTIVE_PROFILE="production"
        CONTAINER="sysadmintoolkit-backup-service-prod"
    else
        error "No hay servicios activos. Ejecuta: $0 start [development|production]"
    fi

    log "Ejecutando backup en perfil: $ACTIVE_PROFILE"

    docker-compose --profile $ACTIVE_PROFILE exec $CONTAINER python main.py --config /config/$filename

    success "Backup ejecutado con configuración: $filename"
}

# Función para acceder al shell
access_shell() {
    log "Accediendo al contenedor de $PROFILE..."

    if [[ "$PROFILE" == "development" ]]; then
        CONTAINER="sysadmintoolkit-backup-service-dev"
    else
        CONTAINER="sysadmintoolkit-backup-service-prod"
    fi

    if ! docker-compose --profile $PROFILE ps | grep -q "Up"; then
        error "Los servicios de $PROFILE no están activos. Ejecuta: $0 start $PROFILE"
    fi

    info "Accediendo al contenedor $CONTAINER"
    info "Comandos útiles dentro del contenedor:"
    info "  • python main.py --config /config        # Ejecutar backup"
    info "  • python main.py --validate-only         # Validar configuración"
    info "  • python test/run_tests.py               # Ejecutar tests"
    info "  • exit                                    # Salir del contenedor"
    echo ""

    docker-compose --profile $PROFILE exec $CONTAINER bash
}

# Función para validar configuración
validate_configuration() {
    # Determinar qué archivo usar
    local config_file=""
    local filename=""

    if [[ -n "$CONFIG_FILE" ]]; then
        # Se especificó un archivo
        if [[ -f "config/$CONFIG_FILE" ]]; then
            config_file="config/$CONFIG_FILE"
            filename="$CONFIG_FILE"
        elif [[ -f "$CONFIG_FILE" ]]; then
            config_file="$CONFIG_FILE"
            filename=$(basename "$CONFIG_FILE")
        else
            error "Archivo de configuración no encontrado: $CONFIG_FILE"
        fi
    else
        # No se especificó archivo, buscar automáticamente
        local configs
        configs=($(find config/ -name "*.yaml" -o -name "*.yml" 2>/dev/null | sort))

        if [[ ${#configs[@]} -eq 0 ]]; then
            error "No hay archivos de configuración. Ejecuta: $0 setup [development|production]"
        elif [[ ${#configs[@]} -eq 1 ]]; then
            config_file="${configs[0]}"
            filename=$(basename "$config_file")
        else
            # Hay múltiples, mostrar lista
            list_config_files
            warning "Hay múltiples archivos de configuración. Especifica cuál validar:"
            echo ""
            echo "Ejemplos:"
            for config in "${configs[@]}"; do
                local fname=$(basename "$config")
                echo "  $0 validate $fname"
            done
            echo ""
            exit 1
        fi
    fi

    log "Validando configuración: $filename"

    # Verificar sintaxis YAML
    if ! python -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
        error "Error en la sintaxis YAML de $filename"
    fi

    success "Sintaxis YAML válida: $filename"

    # Intentar validar con el sistema si está activo
    if docker-compose --profile development ps | grep -q "Up"; then
        log "Validando con sistema activo (development)..."
        docker-compose --profile development exec sysadmintoolkit-backup-service-dev python main.py --validate-only --config /config/$(basename "$config_file")
    elif docker-compose --profile production ps | grep -q "Up"; then
        log "Validando con sistema activo (production)..."
        docker-compose --profile production exec sysadmintoolkit-backup-service-prod python main.py --validate-only --config /config/$(basename "$config_file")
    else
        warning "No hay servicios activos. Validación básica completada."
        info "Para validación completa, ejecuta: $0 start [development|production]"
        echo ""
        info "Archivo validado: $config_file"
    fi
}

# Función principal para configuración inicial
setup_system() {
    log "Configuración inicial completa para perfil: $PROFILE"

    check_dependencies
    create_directories
    setup_configuration
    build_images
    create_network
    start_services

    echo ""
    bold "📋 PRÓXIMOS PASOS:"
    echo ""
    echo "1. Revisa y personaliza la configuración:"
    echo "   nano config/backup_config.yaml"
    echo ""
    echo "2. Valida la configuración:"
    echo "   $0 validate"
    echo ""
    echo "3. Ejecuta un backup de prueba:"
    echo "   $0 backup"
    echo ""
    echo "4. Consulta más comandos:"
    echo "   $0 help"
    echo ""

    success "Configuración inicial completada exitosamente"
}

# =====================================================================================
# LÓGICA PRINCIPAL
# =====================================================================================

case "$COMMAND" in
    "setup")
        setup_system
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup_all
        ;;
    "backup")
        run_backup
        ;;
    "shell")
        access_shell
        ;;
    "validate")
        validate_configuration
        ;;
    "list-configs")
        list_config_files
        ;;
    "help")
        show_help
        ;;
    *)
        # Mantener compatibilidad con versión anterior
        if [[ "$COMMAND" == "development" || "$COMMAND" == "production" ]]; then
            PROFILE="$COMMAND"
            warning "Uso obsoleto. Usa: $0 setup $PROFILE"
            setup_system
        else
            error "Comando desconocido: $COMMAND. Usa: $0 help"
        fi
        ;;
esac
