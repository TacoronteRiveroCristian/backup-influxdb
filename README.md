# InfluxDB Backup System
## Sistema de Backup Campo por Campo con Paralelización Configurable

Sistema robusto de backup para InfluxDB 1.8 que implementa **procesamiento campo por campo independiente** con **paralelización configurable** para máxima seguridad e integridad de datos.

## 🎯 **Características Principales**

### ✅ **Seguridad Máxima**
- **Procesamiento campo por campo**: Cada campo se procesa independientemente
- **Prevención de contaminación cruzada**: Timestamps específicos por campo
- **Aislamiento completo**: Errores en un campo no afectan otros
- **Validación granular**: Verificación independiente por campo

### ⚡ **Alto Rendimiento**
- **Paralelización configurable**: 1-16+ workers simultáneos
- **ThreadPoolExecutor**: Gestión eficiente de hilos
- **Métricas en tiempo real**: Monitoreo de eficiencia paralela
- **Optimización automática**: Balanceo de carga dinámico

### 🔧 **Configuración Flexible**
- **Archivos YAML independientes**: Un archivo por proceso de backup
- **Filtrado avanzado**: Por medición, campo y tipo de dato
- **Modos de backup**: Incremental con scheduler y range específico
- **Logging avanzado**: Thread-safe con identificadores únicos

---

## 🏗️ **Arquitectura del Sistema**

### **Diagrama General**

```mermaid
graph TB
    subgraph "Sistema Principal"
        A[main.py<br/>Orchestrator]
        B[ConfigManager<br/>Validación YAML]
        C[BackupProcessor<br/>Coordinador]
    end

    subgraph "Procesamiento Paralelo"
        D[ThreadPoolExecutor]
        E1[Worker Thread T01<br/>Campo: Irradiance]
        E2[Worker Thread T02<br/>Campo: Temperature]
        E3[Worker Thread T03<br/>Campo: Humidity]
        En[Worker Thread Tn<br/>Campo: N]
    end

    subgraph "Clientes InfluxDB"
        F[InfluxDBClient Source]
        G[InfluxDBClient Destination]
    end

    subgraph "Datos"
        H[(InfluxDB Source<br/>Gomera_Alojera)]
        I[(InfluxDB Destination<br/>Gomera_Alojera)]
    end

    A --> B
    B --> C
    C --> D
    D --> E1
    D --> E2
    D --> E3
    D --> En
    E1 --> F
    E2 --> F
    E3 --> F
    En --> F
    E1 --> G
    E2 --> G
    E3 --> G
    En --> G
    F --> H
    G --> I

    style E1 fill:#e1f5fe
    style E2 fill:#f3e5f5
    style E3 fill:#e8f5e8
    style En fill:#fff3e0
```

### **Flujo de Procesamiento Campo por Campo**

```mermaid
sequenceDiagram
    participant M as main.py
    participant CM as ConfigManager
    participant BP as BackupProcessor
    participant TPE as ThreadPoolExecutor
    participant T1 as Thread T01<br/>(Campo 1)
    participant T2 as Thread T02<br/>(Campo 2)
    participant SC as SourceClient
    participant DC as DestClient

    Note over M: 1. Inicio del Sistema
    M->>CM: Cargar irr.yaml
    CM->>CM: Validar configuración
    CM->>BP: Crear BackupProcessor

    Note over BP: 2. Preparación del Backup
    BP->>SC: Conectar a Source InfluxDB
    BP->>DC: Conectar a Dest InfluxDB
    BP->>DC: Crear base de datos destino

    Note over BP: 3. Análisis de Medición
    BP->>SC: get_field_keys("ForecastingWeather")
    SC-->>BP: {WRF_continuous_Irradiance_W_m2: numeric, WRF_continuous_Temperature_2m_degC: numeric}
    BP->>BP: _filter_fields() → Solo campos configurados

    Note over BP: 4. Procesamiento Paralelo
    BP->>TPE: Crear ThreadPoolExecutor(max_workers=4)

    loop Para cada campo filtrado
        BP->>TPE: submit(_backup_single_field, campo, T_ID)
    end

    Note over T1, T2: 5. Procesamiento Independiente por Campo

    par Campo 1: WRF_continuous_Irradiance_W_m2
        T1->>DC: get_field_last_timestamp("Irradiance")
        DC-->>T1: 2023-12-01T10:30:00Z
        T1->>T1: Calcular start_time = timestamp + 1μs
        T1->>SC: query_data(campo="Irradiance", start_time)
        SC-->>T1: [datos desde 2023-12-01T10:30:00.000001Z]
        T1->>DC: write_data(datos)
        T1-->>TPE: SUCCESS: 1500 registros
    and Campo 2: WRF_continuous_Temperature_2m_degC
        T2->>DC: get_field_last_timestamp("Temperature")
        DC-->>T2: 2023-11-28T15:45:00Z
        T2->>T2: Calcular start_time = timestamp + 1μs
        T2->>SC: query_data(campo="Temperature", start_time)
        SC-->>T2: [datos desde 2023-11-28T15:45:00.000001Z]
        T2->>DC: write_data(datos)
        T2-->>TPE: SUCCESS: 2300 registros
    end

    Note over TPE: 6. Recolección de Resultados
    TPE->>BP: as_completed() → Resultados por campo
    BP->>BP: _update_parallel_stats()
    BP->>BP: Generar resumen

    Note over BP: 7. Finalización
    BP-->>M: {success: true, stats: {...}}
    M->>M: Mostrar resumen final
```

---

## 🔧 **Configuración Detallada**

### **Estructura de Proyecto**

```
backup-influxdb/
├── main.py                          # Orchestrator principal
├── src/                            # Módulos del sistema
│   ├── backup_processor.py         # Procesador campo por campo
│   ├── config_manager.py          # Gestor de configuración
│   ├── influxdb_client.py         # Cliente InfluxDB con get_field_last_timestamp()
│   ├── logger_manager.py          # Logging thread-safe
│   ├── apscheduler_backup.py      # Scheduler para modo incremental
│   └── utils.py                   # Utilidades
├── config/                        # Configuraciones independientes
│   ├── irr.yaml                   # Backup de campo Irradiance
│   ├── temp.yaml                  # Backup de campo Temperature
│   └── backup_config.yaml.template # Template para nuevas configuraciones
├── volumes/
│   └── logs/                      # Logs con identificadores por thread
└── README.md                      # Esta documentación
```

### **Configuraciones Actuales**

#### **irr.yaml** - Backup de Irradiancia
```yaml
measurements:
  specific:
    ForecastingWeather:
      fields:
        include: [WRF_continuous_Irradiance_W_m2]  # Solo irradiancia

options:
  backup_mode: incremental
  parallel_workers: 1                             # 1 campo = 1 worker
  incremental:
    schedule: "* * * * *"                         # Cada minuto
  loki:
    tags:
      config: "irr.yaml"                          # Tag único para logs
```

#### **temp.yaml** - Backup de Temperatura
```yaml
measurements:
  specific:
    ForecastingWeather:
      fields:
        include: [WRF_continuous_Temperature_2m_degC]  # Solo temperatura

options:
  backup_mode: incremental
  parallel_workers: 1                               # 1 campo = 1 worker
  incremental:
    schedule: "* * * * *"                           # Cada minuto
  loki:
    tags:
      config: "temp.yaml"                           # Tag único para logs
```

### **Parámetros de Paralelización**

| Parámetro | Descripción | Valores Recomendados |
|-----------|-------------|---------------------|
| `parallel_workers` | Número de hilos para procesar campos | `1`: Secuencial (máxima seguridad)<br/>`2-4`: Sistemas normales<br/>`4-8`: Servidores potentes<br/>`8-16`: Hardware dedicado |

---

## 🔍 **Prevención de Contaminación Cruzada**

### **Problema Original Resuelto**

**❌ ANTES** (Contaminación):
```mermaid
sequenceDiagram
    participant I as irr.yaml
    participant T as temp.yaml
    participant DB as InfluxDB

    Note over I, T: Problema: Timestamps globales por medición

    I->>DB: get_last_timestamp("ForecastingWeather")
    Note right of DB: Devuelve timestamp de CUALQUIER campo
    DB-->>I: 2023-12-01T10:30:00Z (del campo Temperature)
    I->>I: Inicia desde timestamp de Temperature ❌

    T->>DB: get_last_timestamp("ForecastingWeather")
    DB-->>T: 2023-12-01T10:30:00Z (actualizado por irr.yaml)
    T->>T: Se salta datos de Temperature ❌
```

**✅ AHORA** (Aislamiento Completo):
```mermaid
sequenceDiagram
    participant I as irr.yaml
    participant T as temp.yaml
    participant DB as InfluxDB

    Note over I, T: Solución: Timestamps específicos por campo

    I->>DB: get_field_last_timestamp("ForecastingWeather", "WRF_continuous_Irradiance_W_m2")
    DB-->>I: 2023-12-01T10:30:00Z (solo Irradiance) ✅
    I->>I: Procesa solo desde su último timestamp

    T->>DB: get_field_last_timestamp("ForecastingWeather", "WRF_continuous_Temperature_2m_degC")
    DB-->>T: 2023-11-28T15:45:00Z (solo Temperature) ✅
    T->>T: Procesa desde su propio timestamp independiente
```

### **Funcionamiento del Aislamiento**

```mermaid
graph TB
    subgraph "Configuración irr.yaml"
        A1[Campo: WRF_continuous_Irradiance_W_m2]
        A2[Timestamp específico: 2023-12-01T10:30:00Z]
        A3[Procesa desde: 2023-12-01T10:30:00.000001Z]
    end

    subgraph "Configuración temp.yaml"
        B1[Campo: WRF_continuous_Temperature_2m_degC]
        B2[Timestamp específico: 2023-11-28T15:45:00Z]
        B3[Procesa desde: 2023-11-28T15:45:00.000001Z]
    end

    subgraph "Base de Datos Destino"
        C[ForecastingWeather]
        C1[Irradiance: último = 2023-12-01T10:30:00Z]
        C2[Temperature: último = 2023-11-28T15:45:00Z]
        C3[Humidity: último = 2023-12-10T08:15:00Z]
    end

    A1 --> A2
    A2 --> A3
    B1 --> B2
    B2 --> B3

    A2 -.->|get_field_last_timestamp| C1
    B2 -.->|get_field_last_timestamp| C2

    style A1 fill:#e1f5fe
    style B1 fill:#f3e5f5
    style C1 fill:#e1f5fe
    style C2 fill:#f3e5f5
    style C3 fill:#e8f5e8
```

---

## ⚡ **Procesamiento Paralelo Campo por Campo**

### **Diagrama de Threads Independientes**

```mermaid
gantt
    title Procesamiento Paralelo de Campos (parallel_workers: 4)
    dateFormat X
    axisFormat %s

    section Thread T01
    Campo: Irradiance     :active, t1, 0, 8

    section Thread T02
    Campo: Temperature    :active, t2, 1, 6

    section Thread T03
    Campo: Humidity       :active, t3, 2, 7

    section Thread T04
    Campo: Pressure       :active, t4, 3, 5

    section Secuencial (sin paralelización)
    Todos los campos      :crit, seq, 0, 26
```

### **Métricas de Paralelización**

El sistema genera automáticamente métricas detalladas:

```
Parallelization metrics:
  • Workers used: 4/4
  • Avg processing time: 6.2s
  • Parallel efficiency: 78.5%
  • Thread utilization: [T01, T02, T03, T04]

Field Results Summary:
  • Total fields: 4
  • Processed: 4
  • Skipped: 0
  • Failed: 0
  • Total records: 15,847
```

---

## 🚀 **Guía de Uso**

### **1. Instalación**

```bash
# Clonar repositorio
git clone <repository-url>
cd backup-influxdb

# Crear estructura de directorios
mkdir -p volumes/logs

# Instalar dependencias
pip install -r requirements.txt
```

### **2. Configuración**

```bash
# Copiar template para nueva configuración
cp config/backup_config.yaml.template config/mi_backup.yaml

# Editar configuración
vim config/mi_backup.yaml
```

### **3. Ejecución**

#### **Modo Desarrollo** (validar configuraciones)
```bash
python main.py --validate-only
```

#### **Modo Producción** (ejecutar backups)
```bash
python main.py --config /config --verbose
```

#### **Con Docker**
```bash
docker-compose up -d
```

### **4. Monitoreo**

#### **Logs por Thread**
```bash
# Ver logs de configuración específica
tail -f volumes/logs/irr.yaml/backup.log

# Buscar logs de thread específico
grep "\[T01\]" volumes/logs/temp.yaml/backup.log
```

#### **Métricas en Grafana**
- URL: `http://localhost:3000`
- Usuario: `admin`
- Contraseña: `password`
- Dashboard: "InfluxDB Backup Metrics"

---

## 📊 **Ejemplos de Configuración**

### **Configuración de Alto Rendimiento** (Múltiples Campos)

```yaml
# config/high_performance.yaml
measurements:
  specific:
    WeatherData:
      fields:
        include: [
          temperature, humidity, pressure, wind_speed,
          wind_direction, rainfall, solar_radiation, uv_index
        ]

options:
  parallel_workers: 8          # 8 campos en paralelo
  days_of_pagination: 1        # Chunks pequeños para mayor seguridad
  field_obsolete_threshold: "3M"

  incremental:
    schedule: "0 */6 * * *"     # Cada 6 horas
```

### **Configuración de Máxima Seguridad** (Campo Individual)

```yaml
# config/critical_data.yaml
measurements:
  specific:
    CriticalMetrics:
      fields:
        include: [critical_sensor_reading]  # Solo un campo crítico

options:
  parallel_workers: 1          # Procesamiento secuencial
  days_of_pagination: 1        # Chunks de 1 día
  retries: 5                   # 5 intentos en caso de error

  incremental:
    schedule: "* * * * *"       # Cada minuto
```

### **Configuración por Rango** (Backup Histórico)

```yaml
# config/historical_backup.yaml
options:
  backup_mode: range
  parallel_workers: 16         # Máximo paralelismo para histórico

  range:
    start_date: "2023-01-01T00:00:00Z"
    end_date: "2023-12-31T23:59:59Z"
```

---

## 🔧 **Configuración Avanzada**

### **Parámetros de Rendimiento**

| Parámetro | Descripción | Valor por Defecto | Recomendación |
|-----------|-------------|-------------------|---------------|
| `parallel_workers` | Hilos para campos | `4` | = Número de campos a procesar |
| `days_of_pagination` | Días por chunk | `7` | `1-7` según volumen de datos |
| `timeout_client` | Timeout HTTP (seg) | `20` | `20-60` según latencia |
| `retries` | Reintentos por error | `3` | `3-5` para entornos inestables |

### **Optimización por Escenario**

#### **Pocos Campos, Alto Volumen**
```yaml
parallel_workers: 2-4        # Pocos threads pero eficientes
days_of_pagination: 1        # Chunks pequeños
timeout_client: 60           # Timeout largo para grandes consultas
```

#### **Muchos Campos, Bajo Volumen**
```yaml
parallel_workers: 8-16       # Muchos threads para paralelismo
days_of_pagination: 30       # Chunks grandes
timeout_client: 20           # Timeout normal
```

#### **Datos Críticos**
```yaml
parallel_workers: 1          # Secuencial para máxima seguridad
retries: 5                   # Muchos reintentos
field_obsolete_threshold: "" # Sin filtrado por obsolescencia
```

---

## 🔍 **Troubleshooting**

### **Problemas Comunes**

#### **1. Contaminación entre Configuraciones**
```bash
# Síntoma: Configuraciones se saltan datos
# Causa: Tags de Loki duplicados o nombres de campos incorrectos

# Solución:
# 1. Verificar tags únicos en loki.tags.config
# 2. Verificar campos específicos en measurements.specific.*.fields.include
```

#### **2. Bajo Rendimiento**
```bash
# Síntoma: Procesamiento lento
# Causa: parallel_workers demasiado bajo

# Solución:
# 1. Aumentar parallel_workers según número de campos
# 2. Monitorear uso de CPU y memoria
# 3. Ajustar days_of_pagination
```

#### **3. Errores de Conexión**
```bash
# Síntoma: "Failed to establish connections"
# Causa: InfluxDB no disponible

# Solución:
# 1. Verificar conectividad: curl http://influxdb:8086/ping
# 2. Revisar credenciales en configuración
# 3. Aumentar initial_connection_retry_delay
```

### **Logs de Depuración**

```bash
# Habilitar debug completo
python main.py --verbose

# Ver threads específicos
grep "\[T01\]" volumes/logs/*/backup.log

# Monitorear estadísticas de paralelización
grep "Parallelization metrics" volumes/logs/*/backup.log
```

---

## 📈 **Monitoreo y Métricas**

### **Dashboard de Grafana**

El sistema incluye dashboards preconfigurados:

1. **Backup Overview**: Estado general de todos los procesos
2. **Field Processing**: Métricas por campo individual
3. **Parallel Efficiency**: Estadísticas de paralelización
4. **Error Analysis**: Análisis de fallos por thread

### **Métricas Clave**

- **Records Transferred**: Registros transferidos por configuración
- **Parallel Efficiency**: Eficiencia del paralelismo (0-100%)
- **Thread Utilization**: Uso de threads por proceso
- **Field Processing Time**: Tiempo promedio por campo
- **Error Rate**: Porcentaje de errores por configuración

---

## 🔄 **Flujo de Desarrollo**

### **Agregar Nueva Configuración**

1. **Crear archivo de configuración**:
   ```bash
   cp config/backup_config.yaml.template config/nueva_config.yaml
   ```

2. **Configurar campos específicos**:
   ```yaml
   measurements:
     specific:
       TuMedicion:
         fields:
           include: [tu_campo_especifico]
   ```

3. **Configurar paralelización**:
   ```yaml
   options:
     parallel_workers: 2  # Según número de campos
   ```

4. **Validar configuración**:
   ```bash
   python main.py --validate-only
   ```

5. **Ejecutar en modo test**:
   ```bash
   python main.py --config /config
   ```

### **Testing**

```bash
# Tests unitarios
pytest test/unit/

# Tests de integración
pytest test/integration/

# Test completo del sistema
python test/run_tests.py
```

---

## 📚 **Referencias Técnicas**

### **Tecnologías Utilizadas**

- **Python 3.8+**: Lenguaje principal
- **InfluxDB 1.8**: Base de datos temporal
- **ThreadPoolExecutor**: Paralelización de threads
- **APScheduler**: Programación de tareas
- **PyYAML**: Parsing de configuraciones
- **Docker/Docker Compose**: Containerización
- **Grafana**: Visualización de métricas
- **Loki**: Logging centralizado

### **Algoritmos Implementados**

1. **Timestamp Field-Specific**: `get_field_last_timestamp(db, measurement, field)`
2. **Parallel Field Processing**: ThreadPoolExecutor con as_completed()
3. **Cross-Contamination Prevention**: Timestamps independientes por campo
4. **Parallel Efficiency Calculation**: (sequential_time / parallel_time / workers) * 100

### **Patrones de Diseño**

- **Factory Pattern**: Creación de clientes InfluxDB
- **Observer Pattern**: Sistema de logging con múltiples handlers
- **Strategy Pattern**: Diferentes modos de backup (incremental/range)
- **Template Pattern**: Estructura común de configuración YAML

---

## 📄 **Licencia**

Este proyecto está licenciado bajo la [MIT License](LICENSE).

---

## 🤝 **Contribución**

1. Fork del proyecto
2. Crear rama para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📞 **Soporte**

- **Documentación**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Wiki**: [GitHub Wiki](https://github.com/your-repo/wiki)

---

**🚀 Sistema de Backup InfluxDB - Procesamiento Campo por Campo con Paralelización Avanzada**
