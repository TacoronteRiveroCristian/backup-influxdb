# InfluxDB Backup System

Sistema de backup profesional para InfluxDB con procesamiento campo por campo, paralelización configurable y soporte completo para entornos de desarrollo y producción usando Docker Compose.

## 🏗️ Arquitectura

- **Desarrollo**: Entorno completo con herramientas de desarrollo, testing y debugging
- **Producción**: Imagen mínima optimizada para ejecutar backups programados
- **Multi-stage Docker**: Separación clara entre dependencias de desarrollo y producción
- **Volúmenes persistentes**: Configuración y logs persistentes

## 🚀 Inicio Rápido

### Gestor Automático (Recomendado)

El script `quick-start.sh` proporciona un gestor todo-en-uno que simplifica todas las operaciones:

```bash
# 📋 Ver todos los comandos disponibles
./scripts/quick-start.sh help

# 🔧 Configuración inicial completa (solo la primera vez)
./scripts/quick-start.sh setup development    # Para desarrollo
./scripts/quick-start.sh setup production     # Para producción
```

### Comandos Principales

#### Gestión de Servicios
```bash
# Iniciar servicios
./scripts/quick-start.sh start development
./scripts/quick-start.sh start production

# Parar servicios
./scripts/quick-start.sh stop development
./scripts/quick-start.sh stop production

# Reiniciar servicios
./scripts/quick-start.sh restart development
./scripts/quick-start.sh restart production

# Estado y recursos del sistema
./scripts/quick-start.sh status development
./scripts/quick-start.sh status production
```

#### Monitoreo y Logs
```bash
# Ver logs en tiempo real
./scripts/quick-start.sh logs development
./scripts/quick-start.sh logs production
```

#### Backup y Validación
```bash
# Listar configuraciones disponibles
./scripts/quick-start.sh list-configs

# Ejecutar backup manual
./scripts/quick-start.sh backup                    # Usa configuración por defecto
./scripts/quick-start.sh backup mi_config.yaml     # Usa configuración específica

# Validar configuración
./scripts/quick-start.sh validate                  # Valida configuración por defecto
./scripts/quick-start.sh validate mi_config.yaml   # Valida configuración específica
```

#### Acceso al Sistema
```bash
# Acceder al contenedor interactivo
./scripts/quick-start.sh shell development
./scripts/quick-start.sh shell production
```

#### Mantenimiento
```bash
# Limpiar todo el sistema (contenedores, volúmenes, redes)
./scripts/quick-start.sh cleanup
```

### Para Expertos en Docker

Si prefieres usar Docker Compose directamente:

```bash
# Levantar servicios
docker-compose --profile development up -d
docker-compose --profile production up -d

# Parar servicios
docker-compose --profile development down
docker-compose --profile production down
```

---

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

## ⚙️ Configuración Inicial

### 1. Preparar el Archivo de Configuración

**OBLIGATORIO**: Antes de levantar cualquier servicio, debes crear tu archivo de configuración.

```bash
# Copiar el template de configuración
cp config/backup_config.yaml.template config/backup_config.yaml

# Editar la configuración según tus necesidades
nano config/backup_config.yaml
```

### 2. Configuración Básica Mínima

Edita `config/backup_config.yaml` con al menos estos valores:

```yaml
# Configuración del servidor origen
source:
  url: http://sysadmintoolkit-influxdb-dev:8086  # Para desarrollo
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
  url: http://sysadmintoolkit-influxdb-dev:8086  # Puede ser el mismo servidor
  user: ""
  password: ""

# Configuración de mediciones (opcional)
measurements:
  include: []       # Vacío = todas las mediciones
  exclude: []       # Mediciones a excluir
```

### 3. Configuración Automática Completa

```bash
# Ejecutar configuración inicial completa
./scripts/quick-start.sh setup development

# Esto automáticamente:
# - Verifica dependencias (Docker, Docker Compose)
# - Crea directorios de volúmenes
# - Configura archivos de configuración
# - Construye imágenes Docker
# - Crea la red Docker
# - Inicia los servicios
```

## 🔧 Entorno de Desarrollo

### Configuración y Uso

```bash
# Configuración inicial completa
./scripts/quick-start.sh setup development

# Iniciar servicios
./scripts/quick-start.sh start development

# Ver estado
./scripts/quick-start.sh status development
```

### Servicios Disponibles en Desarrollo

- **InfluxDB**: http://localhost:8086
- **Grafana**: http://localhost:3000 (admin/admin)
- **Loki**: http://localhost:3100
- **Backup Service**: Contenedor interactivo para desarrollo

### Comandos Útiles para Desarrollo

```bash
# Ver logs en tiempo real
./scripts/quick-start.sh logs development

# Acceder al contenedor de desarrollo
./scripts/quick-start.sh shell development

# Ejecutar backup manualmente
./scripts/quick-start.sh backup

# Validar configuración
./scripts/quick-start.sh validate

# Parar servicios de desarrollo
./scripts/quick-start.sh stop development
```

## 🚀 Entorno de Producción

### Configuración y Uso

```bash
# Configuración inicial completa
./scripts/quick-start.sh setup production

# Iniciar servicio
./scripts/quick-start.sh start production

# Ver estado
./scripts/quick-start.sh status production
```

### Características de Producción

El servicio de producción:
- Usa una imagen mínima optimizada
- Ejecuta backups automáticamente según la configuración
- Reinicia automáticamente si falla
- Solo incluye las dependencias necesarias

### Monitoreo en Producción

```bash
# Ver logs de producción
./scripts/quick-start.sh logs production

# Verificar estado del contenedor
./scripts/quick-start.sh status production

# Ejecutar backup manual en producción
./scripts/quick-start.sh backup
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
├── scripts/
│   └── quick-start.sh               # Gestor automático
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
```

#### 3. Error: "Permission denied en volúmenes"
```bash
# Limpiar y reconfigurar
./scripts/quick-start.sh cleanup
./scripts/quick-start.sh setup development
```

#### 4. Servicios no inician
```bash
# Ver logs detallados
./scripts/quick-start.sh logs development

# Verificar estado
./scripts/quick-start.sh status development

# Limpiar y empezar de nuevo
./scripts/quick-start.sh cleanup
./scripts/quick-start.sh setup development
```

### Comandos de Diagnóstico

```bash
# Verificar configuración
./scripts/quick-start.sh validate

# Acceder al contenedor para diagnóstico
./scripts/quick-start.sh shell development

# Dentro del contenedor:
python main.py --validate-only
python main.py --test-connection
python main.py --info
```

## 📖 Ejemplos de Uso

### Ejemplo 1: Backup Básico

```yaml
# config/backup_config.yaml
source:
  url: http://sysadmintoolkit-influxdb-dev:8086
  databases:
    - name: metrics
      destination: metrics_backup

destination:
  url: http://sysadmintoolkit-influxdb-dev:8086
```

```bash
# Configurar y ejecutar
./scripts/quick-start.sh setup development
./scripts/quick-start.sh backup
```

### Ejemplo 2: Backup de Producción con Horarios

```yaml
# config/backup_config.yaml
schedule:
  enabled: true
  interval: "0 2 * * *"  # Diario a las 2 AM

source:
  url: http://influxdb-production:8086
  databases:
    - name: production_metrics
      destination: production_metrics_backup

destination:
  url: http://influxdb-backup:8086
```

```bash
# Configurar y ejecutar
./scripts/quick-start.sh setup production
./scripts/quick-start.sh start production
```

### Ejemplo 3: Backup con Configuración Específica

```bash
# Crear configuración específica
cp config/backup_config.yaml.template config/mi_backup.yaml

# Editar configuración
nano config/mi_backup.yaml

# Validar configuración
./scripts/quick-start.sh validate mi_backup.yaml

# Ejecutar backup con configuración específica
./scripts/quick-start.sh backup mi_backup.yaml
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
```yaml
# docker-compose.yaml
networks:
  backup-network:
    driver: bridge
    internal: true  # Solo comunicación interna
```

## 📈 Monitoreo

### Métricas Disponibles

- Tiempo de ejecución de backup
- Número de registros procesados
- Errores y reintentos
- Uso de memoria y CPU
- Estado de conectividad

### Logs Estructurados

```bash
# Ver logs en tiempo real
./scripts/quick-start.sh logs development

# Ver logs específicos
tail -f volumes/backup_logs/backup_$(date +%Y%m%d).log

# Buscar errores
grep -i error volumes/backup_logs/backup_*.log
```

## 🔄 Actualización

### Actualizar el Sistema

```bash
# Parar servicios
./scripts/quick-start.sh stop development

# Actualizar código
git pull origin main

# Reconstruir y reiniciar
./scripts/quick-start.sh setup development
```

### Migración de Configuración

```bash
# Comparar configuraciones
diff config/backup_config.yaml config/backup_config.yaml.template

# Backup de configuración actual
cp config/backup_config.yaml config/backup_config.yaml.backup
```

## 🆘 Soporte

### Flujo de Trabajo de Diagnóstico

1. **Verificar estado**:
   ```bash
   ./scripts/quick-start.sh status development
   ```

2. **Validar configuración**:
   ```bash
   ./scripts/quick-start.sh validate
   ```

3. **Ver logs**:
   ```bash
   ./scripts/quick-start.sh logs development
   ```

4. **Acceder al contenedor**:
   ```bash
   ./scripts/quick-start.sh shell development
   ```

5. **Limpiar si es necesario**:
   ```bash
   ./scripts/quick-start.sh cleanup
   ./scripts/quick-start.sh setup development
   ```

### Recursos Adicionales

- **Testing**: `python test/run_tests.py`
- **Documentación**: `docs/`
- **Logs**: `volumes/backup_logs/`
- **Configuración**: `config/backup_config.yaml.template`

---

**El sistema está diseñado para ser robusto, escalable y fácil de mantener. Con el gestor automático `quick-start.sh` tendrás un sistema de backup profesional funcionando en minutos.**
