FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Dependencias basicas
RUN apt-get update && apt-get install -y \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar solo lo necesario para validar config
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar codigo minimo
COPY src/ ./src/
COPY main.py .
COPY config/backup-config.yaml.template ./config/backup-config.yaml.template

VOLUME ["/config"]

# Validacion de configs en /config/*.yaml como healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python main.py --config /config --validate-only || exit 1

CMD ["python", "main.py", "--config", "/config", "--validate-only"]
