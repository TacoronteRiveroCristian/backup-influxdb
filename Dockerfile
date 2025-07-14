# InfluxDB Backup System Dockerfile
# ==================================
#
# Multi-stage build para separar dependencias de desarrollo y producción
# Stage development: Incluye git, docker, herramientas de testing
# Stage production: Imagen mínima para producción

# =====================================
# Stage Base: Dependencias comunes
# =====================================
FROM python:3.11-slim AS base

# Metadata
LABEL maintainer="InfluxDB Backup System"
LABEL description="Multi-process InfluxDB backup system with YAML configuration"
LABEL version="1.0.0"

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias básicas del sistema
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios necesarios
RUN mkdir -p /app /config /var/log/backup-influxdb

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python básicas
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# =====================================
# Stage Development: Con herramientas de desarrollo
# =====================================
FROM base AS development

# Variables de construcción para configuración de Git
ARG GIT_USER_NAME="Developer"
ARG GIT_USER_EMAIL="dev@example.com"
ARG GIT_DEFAULT_BRANCH="main"
ARG GIT_TOKEN=""

# Instalar herramientas de desarrollo
RUN apt-get update && apt-get install -y \
    git \
    docker.io \
    docker-compose \
    build-essential \
    nano \
    vim \
    procps \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de testing
COPY test/requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Configurar Git usando las variables ARG
RUN git config --global user.name "${GIT_USER_NAME}" \
    && git config --global user.email "${GIT_USER_EMAIL}" \
    && git config --global init.defaultBranch "${GIT_DEFAULT_BRANCH}" \
    && git config --global credential.helper store

# Configurar token de Git si se proporciona
RUN if [ -n "${GIT_TOKEN}" ]; then \
        echo "https://${GIT_USER_NAME}:${GIT_TOKEN}@github.com" > /root/.git-credentials \
        && chmod 600 /root/.git-credentials; \
    fi

# Crear usuario para desarrollo (opcional, más seguro que root)
RUN useradd -m -s /bin/bash devuser \
    && usermod -aG docker devuser

# Copiar todo el código fuente (incluyendo tests)
COPY . .

# Configurar permisos
RUN chmod +x main.py \
    && chmod +x test/scripts/*.sh 2>/dev/null || true

# Punto de montaje para desarrollo
VOLUME ["/config", "/var/log/backup-influxdb", "/app"]

# Healthcheck para desarrollo
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python main.py --validate-only || exit 1

# Comando por defecto para desarrollo (mantener vivo)
CMD ["sleep", "infinity"]

# =====================================
# Stage Production: Imagen mínima
# =====================================
FROM base AS production

# Copiar solo el código fuente necesario (sin tests)
COPY src/ ./src/
COPY main.py .

# Hacer ejecutable el script principal
RUN chmod +x main.py

# Crear punto de montaje para configuraciones
VOLUME ["/config", "/var/log/backup-influxdb"]

# Healthcheck para producción
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python main.py --validate-only || exit 1

# Comando por defecto para producción
CMD ["python", "main.py", "--config", "/app/config"]
