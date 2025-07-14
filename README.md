# InfluxDB Backup System

Sistema de backup profesional para InfluxDB con procesamiento campo por campo, paralelización configurable y soporte completo para entornos de desarrollo y producción usando Docker Compose.

## 🏗️ Arquitectura

- **Desarrollo**: Entorno completo con herramientas de desarrollo, testing y debugging
- **Producción**: Imagen mínima optimizada para ejecutar backups programados
- **Multi-stage Docker**: Separación clara entre dependencias de desarrollo y producción
- **Volúmenes persistentes**: Configuración y logs persistentes

## 📋 Requisitos Previos

- Docker 20.10+
- Docker Compose 2.0+
- Al menos 2GB de RAM libre
- Puertos disponibles: 8086, 3000, 3100

```bash
# Verificar versiones
docker --version
docker-compose --version
```

## 🧹 Limpiar Servicios Existentes

Si tienes otros servicios corriendo en los mismos puertos, debes limpiarlos antes:

```bash
# Parar todos los contenedores
docker stop $(docker ps -aq) 2>/dev/null || true

# Limpiar contenedores que usen los puertos
docker rm -f $(docker ps -aq --filter "expose=8086" --filter "expose=3000" --filter "expose=3100") 2>/dev/null || true

# Limpiar contenedores por nombre (si existen de instalaciones previas)
docker rm -f influxdb grafana loki backup-service 2>/dev/null || true

# Limpiar redes que puedan conflictuar
docker network rm influxdb-network 2>/dev/null || true

# Verificar que los puertos están libres
netstat -tlnp | grep -E ':8086|:3000|:3100' || echo "Puertos libres"

# Limpiar volúmenes no utilizados (opcional)
docker volume prune -f
```

## ⚙️ Configuración Inicial

### 1. Preparar el Archivo de Configuración

**OBLIGATORIO**: Antes de levantar cualquier servicio, debes crear tu archivo de configuración.

```bash
# Copiar el template de configuración
cp config/backup_config.yaml.template config/backup_config.yaml

# Editar la configuración según tus necesidades
nano config/backup_config.yaml
```

### 2. Crear Estructura de Directorios

```bash
# Crear estructura de directorios necesarios
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
```

### 3. Configuración Básica Mínima

Edita `config/backup_config.yaml` con al menos estos valores:

```yaml
# Configuración del servidor origen
source:
  url: http://backup-influxdb:8086  # Para desarrollo
  # url: http://tu-servidor-influxdb:8086        # Para producción

  databases:
    - name: metrics
      destination: metrics_backup
    - name: telegraf
      destination: telegraf_backup

  user: ""          # Usuario si tienes autenticación
  password: ""      # Contraseña si tienes autenticación

# Configuración del servidor destino
destination:
  url: http://backup-influxdb:8086  # Puede ser el mismo servidor
  user: ""
  password: ""

# Configuración de mediciones (opcional)
measurements:
  include: []       # Vacío = todas las mediciones
  exclude: []       # Mediciones a excluir
```

### 4. Crear Red Docker

```bash
# Crear red para comunicación entre contenedores
docker network create influxdb-network
```

## 🔧 Entorno de Desarrollo

### Levantar Servicios de Desarrollo

```bash
# Construir imágenes (solo la primera vez o cuando hay cambios)
docker-compose build --target development backup-service-dev

# Levantar todos los servicios de desarrollo
docker-compose --profile development up -d

# Verificar que los servicios estén corriendo
docker-compose --profile development ps
```

### Servicios Disponibles en Desarrollo

- **InfluxDB**: http://localhost:8086
- **Grafana**: http://localhost:3000 (admin/admin)
- **Loki**: http://localhost:3100
- **Backup Service**: Contenedor interactivo para desarrollo

### Comandos Útiles para Desarrollo

```bash
# Ver logs en tiempo real
docker-compose --profile development logs -f

# Ver logs de un servicio específico
docker-compose --profile development logs -f backup-service-dev
docker-compose --profile development logs -f backup-influxdb

# Acceder al contenedor de backup
docker-compose --profile development exec backup-service-dev bash

# Ejecutar backup manualmente
docker-compose --profile development exec backup-service-dev python main.py --config /config

# Validar configuración
docker-compose --profile development exec backup-service-dev python main.py --validate-only

# Ejecutar tests
docker-compose --profile development exec backup-service-dev python test/run_tests.py

# Parar servicios de desarrollo
docker-compose --profile development down

# Parar y eliminar volúmenes
docker-compose --profile development down -v
```

### Reconstruir Imagen de Desarrollo

```bash
# Si has hecho cambios en el código
docker-compose build --no-cache --target development backup-service-dev
docker-compose --profile development up -d backup-service-dev
```

## 🚀 Entorno de Producción

### Levantar Servicio de Producción

```bash
# Construir imagen de producción (solo la primera vez o cuando hay cambios)
docker-compose build --target production backup-service-prod

# Levantar solo el servicio de backup en producción
docker-compose --profile production up -d

# Verificar estado
docker-compose --profile production ps
```

### Características de Producción

El servicio de producción:
- Usa una imagen mínima optimizada
- Ejecuta backups automáticamente según la configuración
- Reinicia automáticamente si falla
- Solo incluye las dependencias necesarias

### Comandos para Producción

```bash
# Ver logs de producción
docker-compose --profile production logs -f

# Ejecutar backup manual en producción
docker-compose --profile production exec backup-service-prod python main.py --config /config

# Acceder al contenedor (para debugging)
docker-compose --profile production exec backup-service-prod bash

# Parar servicio de producción
docker-compose --profile production down

# Reconstruir imagen de producción
docker-compose build --no-cache --target production backup-service-prod
```

## 📊 Configuración Avanzada

### Configuración por Campos Específicos

```yaml
# En config/backup_config.yaml
measurements:
  specific:
    cpu:
      fields:
        include: [usage_user, usage_system, usage_idle]
        exclude: []
        types: [numeric, string, boolean]

    memory:
      fields:
        include: []  # Todos los campos
        exclude: [buffer, cached, slab]
        types: [numeric]
```

### Configuración de Paralelización

```yaml
# Configuración de workers
parallel:
  workers: 4                    # Número de workers paralelos
  chunk_size: 1000             # Registros por chunk
  max_retries: 3               # Reintentos por error
  timeout: 300                 # Timeout por operación
```

### Configuración de Horarios

```yaml
# Programación de backups
schedule:
  enabled: true
  interval: "0 2 * * *"        # Diario a las 2 AM (cron format)
  timezone: "UTC"
  overlapping: false           # No permitir backups simultáneos
```

## 🗂️ Estructura de Archivos

```
proyecto/
├── config/
│   ├── backup_config.yaml.template    # Template de configuración
│   └── backup_config.yaml            # Tu configuración (crear)
├── volumes/
│   ├── backup_logs/                  # Logs persistentes
│   ├── influxdb/data/               # Datos InfluxDB dev
│   ├── grafana/data/                # Datos Grafana
│   └── loki/data/                   # Datos Loki
├── src/                             # Código fuente
├── test/                            # Sistema de testing
├── docker-compose.yaml              # Configuración servicios
├── Dockerfile                       # Multi-stage build
└── README.md                        # Este archivo
```

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error: "No se encontró archivo de configuración"
```bash
# Verificar que existe el archivo
ls -la config/backup_config.yaml

# Si no existe, crear desde template
cp config/backup_config.yaml.template config/backup_config.yaml
```

#### 2. Error: "No se puede conectar a InfluxDB"
```bash
# Verificar que InfluxDB está corriendo
curl -i http://localhost:8086/ping

# Verificar configuración de red
docker network ls
docker network inspect influxdb-network

# Ver logs de InfluxDB
docker-compose --profile development logs backup-influxdb
```

#### 3. Error: "Puerto ya en uso"
```bash
# Ver qué proceso usa el puerto
netstat -tlnp | grep 8086

# Parar el proceso si es necesario y limpiar
docker stop $(docker ps -q --filter "publish=8086")
```

#### 4. Servicios no inician
```bash
# Ver logs detallados
docker-compose --profile development logs

# Limpiar todo y empezar de nuevo
docker-compose --profile development down -v
docker system prune -f
docker network create influxdb-network
docker-compose --profile development up -d
```

### Comandos de Diagnóstico

```bash
# Verificar configuración dentro del contenedor
docker-compose --profile development exec backup-service-dev python main.py --validate-only

# Test de conectividad
docker-compose --profile development exec backup-service-dev python main.py --test-connection

# Ver información del sistema
docker-compose --profile development exec backup-service-dev python main.py --info

# Verificar espacio en disco
docker system df

# Ver uso de recursos
docker stats --no-stream
```

## 📖 Ejemplos de Uso

### Ejemplo 1: Backup Básico en Desarrollo

```bash
# 1. Preparar configuración
cp config/backup_config.yaml.template config/backup_config.yaml
nano config/backup_config.yaml

# 2. Crear directorios y red
mkdir -p volumes/{backup_logs,influxdb/data,grafana/data,loki/data}
docker network create influxdb-network

# 3. Levantar desarrollo
docker-compose --profile development up -d

# 4. Ejecutar backup
docker-compose --profile development exec backup-service-dev python main.py --config /config
```

### Ejemplo 2: Backup de Producción Programado

```bash
# 1. Configurar backup programado
cp config/backup_config.yaml.template config/backup_config.yaml

# 2. Editar para habilitar schedule
nano config/backup_config.yaml
# Añadir:
# schedule:
#   enabled: true
#   interval: "0 2 * * *"

# 3. Levantar producción
docker network create influxdb-network
docker-compose --profile production up -d

# 4. Verificar logs
docker-compose --profile production logs -f
```

### Ejemplo 3: Desarrollo con Testing

```bash
# 1. Levantar desarrollo
docker-compose --profile development up -d

# 2. Acceder al contenedor
docker-compose --profile development exec backup-service-dev bash

# 3. Dentro del contenedor:
python test/run_tests.py              # Ejecutar tests
python main.py --validate-only       # Validar configuración
python main.py --config /config      # Ejecutar backup
exit
```

## 🛡️ Seguridad

### Mejores Prácticas

1. **Usar secrets para contraseñas**:
```yaml
# docker-compose.yaml
secrets:
  influxdb_password:
    file: ./secrets/influxdb_password.txt
```

2. **Configurar SSL/TLS**:
```yaml
# config/backup_config.yaml
source:
  url: https://influxdb.ejemplo.com:8086
  ssl: true
  verify_ssl: true
```

3. **Limitar acceso a red**:
```bash
# Crear red interna
docker network create --internal backup-network
```

## 📈 Monitoreo

### Métricas Disponibles

- Tiempo de ejecución de backup
- Número de registros procesados
- Errores y reintentos
- Uso de memoria y CPU
- Estado de conectividad

### Comandos de Monitoreo

```bash
# Ver logs en tiempo real
docker-compose --profile development logs -f

# Ver logs específicos del backup
tail -f volumes/backup_logs/backup_$(date +%Y%m%d).log

# Buscar errores
grep -i error volumes/backup_logs/backup_*.log

# Ver recursos en tiempo real
docker stats

# Estado de contenedores
docker-compose --profile development ps
```

## 🔄 Actualización

### Actualizar el Sistema

```bash
# 1. Parar servicios
docker-compose --profile development down

# 2. Actualizar código
git pull origin main

# 3. Reconstruir imágenes
docker-compose build --no-cache

# 4. Levantar servicios
docker-compose --profile development up -d
```

### Backup de Configuración

```bash
# Hacer backup de configuración antes de actualizar
cp config/backup_config.yaml config/backup_config.yaml.backup

# Comparar con template después de actualizar
diff config/backup_config.yaml config/backup_config.yaml.template
```

## 🆘 Comandos de Referencia Rápida

### Gestión Básica
```bash
# Desarrollo
docker-compose --profile development up -d      # Levantar
docker-compose --profile development down       # Parar
docker-compose --profile development logs -f    # Ver logs

# Producción
docker-compose --profile production up -d       # Levantar
docker-compose --profile production down        # Parar
docker-compose --profile production logs -f     # Ver logs
```

### Operaciones de Backup
```bash
# Ejecutar backup
docker-compose --profile development exec backup-service-dev python main.py --config /config

# Validar configuración
docker-compose --profile development exec backup-service-dev python main.py --validate-only

# Acceder al contenedor
docker-compose --profile development exec backup-service-dev bash
```

### Mantenimiento
```bash
# Limpiar todo
docker-compose down -v
docker system prune -f
docker network rm influxdb-network

# Reconstruir desde cero
docker-compose build --no-cache
docker network create influxdb-network
docker-compose --profile development up -d
```

### Recursos Adicionales

- **Testing**: `docker-compose --profile development exec backup-service-dev python test/run_tests.py`
- **Documentación**: `docs/`
- **Logs**: `volumes/backup_logs/`
- **Configuración**: `config/backup_config.yaml.template`

---

**Sistema de backup robusto y escalable usando comandos Docker estándar. Perfecto para integración en pipelines CI/CD y automatización.**
