# Configuración del Sistema de Backup

Esta carpeta contiene los archivos de configuración necesarios para el sistema de backup InfluxDB.

## 📁 Archivos Disponibles

- **`backup_config.yaml.template`** - Template completo con todas las opciones disponibles
- **`backup_config.yaml.example`** - Ejemplo básico para empezar rápidamente
- **`backup_config.yaml`** - Tu configuración personalizada (crear a partir de los anteriores)

## 🚀 Configuración Rápida

### Opción 1: Usar el Script de Inicio Rápido
```bash
# Desde la raíz del proyecto
./scripts/quick-start.sh development
```

### Opción 2: Configuración Manual
```bash
# Copiar ejemplo básico
cp config/backup_config.yaml.example config/backup_config.yaml

# O copiar template completo
cp config/backup_config.yaml.template config/backup_config.yaml

# Editar configuración
nano config/backup_config.yaml
```

## ⚙️ Configuraciones Básicas

### Configuración Mínima para Desarrollo
```yaml
source:
  url: http://sysadmintoolkit-influxdb-dev:8086
  databases:
    - name: metrics
      destination: metrics_backup

destination:
  url: http://sysadmintoolkit-influxdb-dev:8086
```

### Configuración para Producción
```yaml
source:
  url: http://influxdb-production:8086
  databases:
    - name: production_metrics
      destination: production_metrics_backup
  user: "admin"
  password: "secure_password"

destination:
  url: http://influxdb-backup:8086
  user: "admin"
  password: "secure_password"

schedule:
  enabled: true
  interval: "0 2 * * *"  # Diario a las 2 AM
```

## 🔧 Configuraciones Avanzadas

### Backup Selectivo por Campos
```yaml
measurements:
  specific:
    cpu:
      fields:
        include: [usage_user, usage_system, usage_idle]
        exclude: []
        types: [numeric]

    memory:
      fields:
        include: [used, available, total]
        exclude: [buffer, cached, slab]
        types: [numeric]
```

### Configuración de Rendimiento
```yaml
parallel:
  workers: 8              # Más workers para mejor rendimiento
  chunk_size: 5000        # Chunks más grandes para menos overhead
  timeout: 600            # Timeout mayor para datasets grandes
```

### Configuración de Logging
```yaml
logging:
  level: DEBUG            # Para troubleshooting
  file: "/var/log/backup_influxdb/backup.log"
  rotate: true
  max_size: 50MB
  backup_count: 10
```

## 🛡️ Mejores Prácticas

### Seguridad
- Usa variables de entorno para contraseñas sensibles
- Configura SSL/TLS para conexiones remotas
- Limita permisos de archivos de configuración

### Rendimiento
- Ajusta `workers` según tu CPU (4-8 workers típico)
- Aumenta `chunk_size` para datasets grandes
- Usa `group_by` para optimizar consultas

### Monitoreo
- Habilita logs detallados durante la configuración inicial
- Configura notificaciones para errores críticos
- Revisa métricas de rendimiento regularmente

## 🔍 Validación de Configuración

```bash
# Validar configuración en desarrollo
docker-compose --profile development exec sysadmintoolkit-backup-service-dev python main.py --validate-only

# Validar configuración en producción
docker-compose --profile production exec sysadmintoolkit-backup-service-prod python main.py --validate-only
```

## 📝 Ejemplos por Caso de Uso

### Caso 1: Backup de Métricas de Sistema
```yaml
source:
  url: http://telegraf-influxdb:8086
  databases:
    - name: telegraf
      destination: telegraf_backup

measurements:
  include: [cpu, memory, disk, network]
  exclude: [debug, temp_metrics]
```

### Caso 2: Backup de Datos IoT
```yaml
source:
  url: http://iot-influxdb:8086
  databases:
    - name: sensors
      destination: sensors_backup

measurements:
  specific:
    temperature:
      fields:
        include: [value, location, device_id]
        types: [numeric, string]

    humidity:
      fields:
        include: [value, location, device_id]
        types: [numeric, string]
```

### Caso 3: Backup Programado con Notificaciones
```yaml
schedule:
  enabled: true
  interval: "0 1 * * *"  # Diario a la 1 AM
  timezone: "America/New_York"

notifications:
  enabled: true
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "backup@empresa.com"
    password: "app_password"
    from: "backup@empresa.com"
    to: ["admin@empresa.com"]
```

## 🆘 Troubleshooting

### Problemas Comunes

**Error: "Configuration file not found"**
```bash
# Verificar que el archivo existe
ls -la config/backup_config.yaml

# Crear desde template
cp config/backup_config.yaml.template config/backup_config.yaml
```

**Error: "Invalid YAML syntax"**
```bash
# Validar sintaxis YAML
python -c "import yaml; yaml.safe_load(open('config/backup_config.yaml'))"
```

**Error: "Cannot connect to InfluxDB"**
```bash
# Verificar URLs y credenciales en la configuración
# Probar conectividad manualmente
curl -i http://localhost:8086/ping
```

## 📚 Referencias

- [Documentación InfluxDB](https://docs.influxdata.com/influxdb/)
- [Sintaxis YAML](https://yaml.org/spec/1.2/spec.html)
- [Expresiones Cron](https://crontab.guru/)
- [Docker Compose](https://docs.docker.com/compose/)

---

**Recuerda:** Siempre valida tu configuración antes de ejecutar backups en producción.
