# Guía de Desarrollo

Sistema de backup para InfluxDB con Docker multi-stage y herramientas completas de desarrollo.

## Arquitectura Multi-Stage

El proyecto utiliza un Dockerfile multi-stage que permite diferentes niveles de optimización según el entorno.

### Stages Disponibles

- **development**: Entorno completo con todas las herramientas de desarrollo
- **testing**: Optimizado para ejecución de tests
- **production-base**: Base mínima de producción
- **production-scheduler**: Producción con scheduler incluido
- **production-cli**: Producción para ejecución manual

## Inicio Rápido

### Prerequisitos

```bash
# Docker y Docker Compose
docker --version
docker-compose --version

# Git configurado
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@example.com"
```

### Configuración Inicial

```bash
# 1. Configurar Git en el contenedor (opcional)
./scripts/setup-git-credentials.sh

# 2. Construir imagen de desarrollo
./scripts/dev-tools.sh build-dev

# 3. Levantar entorno completo
./scripts/dev-tools.sh dev-up

# 4. Acceder al contenedor de desarrollo
./scripts/dev-tools.sh dev-shell
```

## Herramientas Disponibles en Desarrollo

### Análisis de Código

```bash
# Dentro del contenedor o localmente
flake8 src/                    # Linting
black src/                     # Formateo automático
isort src/                     # Ordenamiento de imports
mypy src/                      # Type checking
bandit -r src/                 # Análisis de seguridad

# Herramientas combinadas
pre-commit run --all-files     # Ejecutar todos los hooks
```

### Testing

```bash
# Tests unitarios
python -m pytest test/unit/ -v

# Tests de integración (requiere InfluxDB)
python -m pytest test/integration/ -v

# Tests con coverage
python -m pytest test/ --cov=src --cov-report=html --cov-report=term

# Tests de rendimiento
python -m pytest test/performance/ -v --benchmark-only
```

### Editores

```bash
# Editores disponibles en el contenedor
vim                           # Vim con configuración básica
nano                          # Nano
code .                        # VS Code (si hay túnel SSH)
```

### Herramientas de sistema

```bash
# Monitoreo
htop                          # Monitor de procesos
iotop                         # Monitor de I/O
nethogs                       # Monitor de red por proceso
```

## Estructura de Volúmenes

El sistema utiliza volúmenes Docker para persistencia y desarrollo:

```yaml
volumes:
  - .:/app                    # Código fuente (desarrollo)
  - ./volumes/logs:/app/logs  # Logs persistentes
  - ./volumes/data:/app/data  # Datos de respaldo
  - influxdb-data:/var/lib/influxdb  # Datos InfluxDB
```

## Comandos Útiles

### Construcción y Despliegue

```bash
# Construir todas las imágenes
./scripts/dev-tools.sh build-all

# Construir solo producción
./scripts/dev-tools.sh build-prod

# Levantar entorno de desarrollo
./scripts/dev-tools.sh dev-up

# Levantar entorno de producción
./scripts/dev-tools.sh prod-up

# Ver logs
./scripts/dev-tools.sh logs [servicio]

# Limpiar todo
./scripts/dev-tools.sh clean
```

## Workflow de Desarrollo

### 1. Configuración del Entorno

```bash
# Clonar el repositorio
git clone <repository-url>
cd backup-influxdb

# Configurar Git (opcional)
./scripts/setup-git-credentials.sh

# Configurar archivo .env
cp .env.example .env
# Editar .env con tus configuraciones
```

### 2. Desarrollo

```bash
# Levantar entorno de desarrollo
./scripts/dev-tools.sh dev-up

# Acceder al contenedor
./scripts/dev-tools.sh dev-shell

# Dentro del contenedor - desarrollar normalmente
vim src/classes/backup_processor.py
python main.py --config config/backup_config.yaml
```

### 3. Testing

```bash
# Tests unitarios rápidos
python -m pytest test/unit/ -v

# Tests completos (incluye integración)
python test/run_tests.py

# Tests específicos
python -m pytest test/unit/test_backup_processor.py::TestBackupProcessor::test_specific_method -v
```

### 4. Quality Assurance

```bash
# Análisis completo de código
flake8 src/
black --check src/
isort --check-only src/
mypy src/
bandit -r src/

# Formateo automático
black src/
isort src/
```

### 5. Construcción de Producción

```bash
# Salir del contenedor de desarrollo
exit

# Construir imagen de producción
./scripts/dev-tools.sh build-prod

# Probar en producción
./scripts/dev-tools.sh prod-up
```

### 6. Despliegue

```bash
# Etiquetado para release
git tag v1.0.0
git push origin v1.0.0

# Build final
docker build --target production-scheduler -t backup-influxdb:v1.0.0 .
docker push your-registry/backup-influxdb:v1.0.0
```

## Consideraciones de Seguridad

- El archivo `.env` nunca debe subirse al repositorio
- Las credenciales deben manejarse como secretos en producción
- El contenedor de desarrollo incluye herramientas adicionales que no deben usarse en producción
- Revisar regularmente las dependencias con `safety check`

## Tips

### Desarrollo Eficiente

```bash
# Mantener el contenedor corriendo y usar exec para múltiples sesiones
docker-compose exec backup-dev bash

# Usar bind mount para desarrollo en tiempo real
# El código se actualiza automáticamente en el contenedor

# Usar .dockerignore para optimizar el contexto de build
```

### Debugging

```bash
# Logs detallados
python main.py --config config/backup_config.yaml --log-level DEBUG

# Debugging con pdb
python -m pdb main.py --config config/backup_config.yaml

# Profiling
python -m cProfile -s cumtime main.py --config config/backup_config.yaml
```

### Optimización

```bash
# Análisis de dependencias
pipdeptree

# Análisis de vulnerabilidades
safety check

# Optimización de imagen Docker
dive backup-influxdb:latest
```
