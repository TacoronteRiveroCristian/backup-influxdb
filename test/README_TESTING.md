# Guía de Testing

Documentación completa del sistema de testing para el sistema de backup InfluxDB.

## Resumen del Sistema

Este proyecto incluye un sistema completo de testing con:
- **Tests Unitarios** (52 tests) - Sin dependencias externas
- **Tests de Integración** (7 tests) - Con InfluxDB real
- **Tests Docker** (7 tests) - En contenedores aislados

### Estructura de Directorios

```
test/
├── unit/                     # Tests unitarios
│   ├── test_backup_processor.py
│   ├── test_config_manager.py
│   ├── test_influxdb_client.py
│   └── test_logger_manager.py
├── integration/              # Tests de integración
│   ├── test_full_backup_cycle.py
│   └── test_docker_integration.py
├── docker/                   # Tests específicos de Docker
│   └── test_containers.py
├── performance/              # Tests de rendimiento
│   └── test_benchmarks.py
├── data/                     # Datos de test y utilidades
│   ├── test_datasets.py
│   └── data_generator.py
├── utils/                    # Utilidades de testing
│   └── test_helpers.py
└── run_tests.py             # Script principal
```

## Ejecución Rápida

### Todos los Tests

```bash
# Ejecutar todo el suite de tests
python test/run_tests.py

# Con output detallado
python test/run_tests.py --verbose

# Solo tests unitarios (rápido)
python test/run_tests.py --unit-only
```

### Tests Específicos

```bash
# Solo unitarios
python -m pytest test/unit/ -v

# Solo integración
python -m pytest test/integration/ -v

# Solo Docker
python -m pytest test/docker/ -v

# Test específico
python -m pytest test/unit/test_backup_processor.py -v

# Test específico con método
python -m pytest test/unit/test_backup_processor.py::TestBackupProcessor::test_process_measurement -v
```

## Tests Unitarios

Los tests unitarios no requieren dependencias externas y se ejecutan rápidamente.

### Cobertura Actual

- **ConfigManager**: 95% - Configuración YAML y validación
- **BackupProcessor**: 90% - Lógica de procesamiento principal
- **InfluxDBClient**: 88% - Cliente InfluxDB con mocks
- **LoggerManager**: 92% - Sistema de logging

### Ejecutar Solo Unitarios

```bash
python -m pytest test/unit/ -v --tb=short
```

### Con Reporte de Cobertura

```bash
python -m pytest test/unit/ --cov=src --cov-config=test/.coveragerc --cov-report=html --cov-report=term
```

## Tests de Integración

Requieren instancias reales de InfluxDB para probar el flujo completo.

### Configuración Automática

El sistema automáticamente:
1. Detecta si Docker está disponible
2. Levanta contenedores de InfluxDB de test
3. Ejecuta los tests de integración
4. Limpia los contenedores

### Configuración Manual

Si prefieres configurar InfluxDB manualmente:

```bash
# Variables de entorno
export INFLUXDB_SOURCE_URL="http://localhost:8086"
export INFLUXDB_DESTINATION_URL="http://localhost:8087"
export INFLUXDB_USER="admin"
export INFLUXDB_PASSWORD="password"

# Ejecutar tests
python -m pytest test/integration/ -v
```

### Tests Incluidos

1. **test_full_backup_cycle.py**
   - Backup completo de múltiples mediciones
   - Verificación de integridad de datos
   - Tests de rendimiento con datasets grandes

2. **test_docker_integration.py**
   - Integración con contenedores Docker
   - Tests de networking entre contenedores
   - Verificación de persistencia de datos

## Tests Docker

Tests específicos para funcionalidad Docker y contenedores.

### Requisitos

- Docker instalado y ejecutándose
- Docker Compose disponible
- Permisos para ejecutar comandos Docker

### Ejecución

```bash
# Con contenedores automáticos
python test/run_tests.py

# O manualmente
python -m pytest test/docker/ -v
```

## Tests de Rendimiento

Benchmarks y tests de performance para medir eficiencia del sistema.

### Métricas

- Throughput (registros/segundo)
- Uso de memoria
- Tiempo de respuesta
- Eficiencia de paralelización

### Ejecución

```bash
python -m pytest test/performance/ -v --benchmark-only
```

## Configuración del Entorno

### Variables de Entorno

```bash
# Archivo .env.test (opcional)
TESTING=true
LOG_LEVEL=DEBUG
INFLUXDB_SOURCE_URL=http://localhost:8086
INFLUXDB_DESTINATION_URL=http://localhost:8087
INFLUXDB_USER=admin
INFLUXDB_PASSWORD=password
```

### Docker Compose para Testing

```yaml
# test/docker/docker-compose.test.yml
version: '3.8'
services:
  test_influxdb:
    image: influxdb:1.8
    ports:
      - "8086:8086"
    environment:
      - INFLUXDB_DB=test_db
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=password
```

## Datos de Test

### Generación Automática

El sistema incluye generadores de datos de test:

```python
from test.data.data_generator import DataGenerator

generator = DataGenerator(seed=42)
dataset = generator.generate_iot_data(
    start_time=datetime.now() - timedelta(hours=24),
    end_time=datetime.now(),
    measurements=['temperature', 'humidity'],
    interval='1m'
)
```

### Datasets Predefinidos

- **IoT Sensors**: Temperatura, humedad, presión
- **Weather Data**: Datos meteorológicos completos
- **System Metrics**: CPU, memoria, red, disco
- **Industrial**: Sensores industriales y alarmas

## Mocking y Fixtures

### InfluxDB Mock

```python
@pytest.fixture
def mock_influxdb_client():
    with patch('src.classes.influxdb_client.InfluxDBClient') as mock:
        mock_instance = mock.return_value
        mock_instance.ping.return_value = True
        mock_instance.query.return_value = []
        yield mock_instance
```

### Datos de Test

```python
@pytest.fixture
def sample_config():
    return {
        'databases': {
            'source': {
                'host': 'localhost',
                'port': 8086,
                'database': 'test_source'
            },
            'backup': {
                'host': 'localhost',
                'port': 8087,
                'database': 'test_backup'
            }
        }
    }
```

## Debugging Tests

### Logging Detallado

```bash
# Habilitar logs de debug en tests
python -m pytest test/ -v -s --log-cli-level=DEBUG
```

### Test Individual con Debug

```bash
python -m pytest test/integration/test_full_backup_cycle.py::TestFullBackupCycle::test_iot_dataset_backup_cycle -v -s
```

### Mantener Contenedores

```bash
# Para debug, mantener contenedores activos
KEEP_TEST_CONTAINERS=true python test/run_tests.py
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python test/run_tests.py --no-performance
```

### Reporte de Cobertura

```bash
# Generar reporte para CI
python -m pytest test/ --cov=src --cov-report=xml --cov-report=term
```

## Troubleshooting

### Problemas Comunes

1. **InfluxDB no disponible**
```
ERROR: Could not connect to InfluxDB
```
**Solución**: Verificar que InfluxDB esté corriendo
```bash
curl -i http://localhost:8086/ping
```

2. **Docker no disponible**
```
ERROR: Docker no está instalado
```
**Solución**: Instalar Docker y verificar que esté corriendo
```bash
docker --version && docker ps
```

3. **Tests lentos**
```
WARNING: Tests taking too long
```
**Solución**: Ejecutar solo tests unitarios
```bash
python test/run_tests.py --unit-only
```

### Limpiar Estado

```bash
# Limpiar contenedores Docker
docker-compose -f test/docker/docker-compose.test.yml down

# Limpiar archivos de test
rm -rf test/test_result/
```

## Métricas y Reportes

### Reporte HTML

Después de ejecutar tests, se genera un reporte HTML en:
```
test/test_result/final_report.html
```

### Métricas JSON

Datos detallados en:
```
test/test_result/final_report.json
```

### Cobertura

Reporte de cobertura en:
```
test/test_result/coverage_html/index.html
```

## Contribuir a los Tests

### Agregar Nuevo Test Unitario

1. Crear archivo en `test/unit/test_nueva_clase.py`
2. Seguir convenciones de naming: `test_metodo_escenario`
3. Usar fixtures y mocks apropiados
4. Verificar cobertura

### Agregar Test de Integración

1. Crear en `test/integration/`
2. Asegurar que use datos de test reales
3. Limpiar estado después del test
4. Documentar dependencias externas

### Convenciones

- Tests deben ser independientes
- Usar nombres descriptivos
- Incluir docstrings
- Manejar setup/teardown apropiadamente
- Verificar tanto éxito como fallos

## Anexos

### Comandos Útiles

```bash
# Test específico con patrón
python -m pytest -k "test_backup" -v

# Test con marca específica
python -m pytest -m "integration" -v

# Tests que fallaron en la última ejecución
python -m pytest --lf -v

# Tests más lentos
python -m pytest --durations=10
```

### Referencias

- [pytest Documentation](https://docs.pytest.org/)
- [Docker Testing Patterns](https://docs.docker.com/develop/dev-best-practices/)
- [InfluxDB Testing Guide](https://docs.influxdata.com/influxdb/v1.8/)
