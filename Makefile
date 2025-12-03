DOCKER_IMAGE ?= backup-config-validator
DOCKER_TAG ?= latest
PROFILE ?= development
CONFIG_DIR ?= $(PWD)/config

.PHONY: help
help:
	@echo "Targets disponibles:"
	@echo "  make docker-build  - Construye la imagen validadora ($(DOCKER_IMAGE):$(DOCKER_TAG))"
	@echo "  make validate      - Valida todos los .yaml en $(CONFIG_DIR) con la imagen validadora"
	@echo "  make up            - Levanta solo los InfluxDB (source/dest) con docker-compose (perfil $(PROFILE))"
	@echo "  make gen-data      - Levanta source/dest + data-generator para poblar el Influx de origen"
	@echo "  make down          - Hace down de la stack docker-compose (perfil $(PROFILE))"

.PHONY: docker-build
docker-build:
	@docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

.PHONY: validate
validate: docker-build
	@docker run --rm -v $(CONFIG_DIR):/config $(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: up
up:
	@docker compose --profile $(PROFILE) up -d influxdb-source influxdb-dest

.PHONY: gen-data
gen-data:
	@docker compose --profile $(PROFILE) up -d influxdb-source data-generator

.PHONY: down
down:
	@docker compose --profile $(PROFILE) down
