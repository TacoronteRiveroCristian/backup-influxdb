# 🛠️ Guía de Desarrollo

Esta guía explica cómo trabajar con el entorno de desarrollo del sistema de backup de InfluxDB.

## 🏗️ Arquitectura Multi-Stage

El proyecto utiliza un **Dockerfile multi-stage** que separa las dependencias de desarrollo y producción:

### 📦 Stages Disponibles

| Stage | Descripción | Incluye |
|-------|-------------|---------|
| `base` | Dependencias comunes | Python 3.11, dependencias básicas |
| `development` | Entorno de desarrollo | Git, Docker, herramientas de testing, editor |
| `production` | Imagen mínima para producción | Solo código necesario |

## 🚀 Inicio Rápido

### 1. Levantar entorno de desarrollo

```bash
# Opción 1: Usar el script de herramientas
./scripts/dev-tools.sh dev-up

# Opción 2: Docker Compose directo
docker-compose --profile development up -d
```

### 2. Acceder al contenedor

```bash
# Entrar al shell del contenedor
./scripts/dev-tools.sh dev-shell

# O directamente
docker-compose exec sysadmintoolkit-backup-service-dev bash
```

### 3. Ejecutar tests

```bash
# Desde fuera del contenedor
./scripts/dev-tools.sh dev-test

# Desde dentro del contenedor
python -m pytest test/ -v
```

## 🔧 Herramientas Disponibles en Desarrollo

Dentro del contenedor de desarrollo tienes acceso a:

### 🐙 Git
```bash
# Git ya está configurado con valores por defecto
git --version
git config --list
```

### 🐳 Docker
```bash
# Acceso completo a Docker desde dentro del contenedor
docker --version
docker ps
docker images
```

### 🧪 Testing
```bash
# Todas las herramientas de testing están instaladas
pytest --version
coverage --version
```

### 📝 Editores
```bash
# Editores disponibles
nano archivo.py
vim archivo.py
```

### 🔍 Herramientas de sistema
```bash
# Monitoring y debugging
htop
ps aux
```

## 📂 Estructura de Volúmenes

### Desarrollo
```yaml
volumes:
  - ./:/app/                                    # Todo el proyecto montado
  - ./volumes/backup_logs:/var/log/backup_influxdb  # Logs
  - /var/run/docker.sock:/var/run/docker.sock   # Acceso a Docker
```

### Producción
```yaml
volumes:
  - ./config:/app/config                        # Solo configuración
  - ./volumes/backup_logs:/var/log/backup_influxdb  # Solo logs
```

## 🎯 Comandos Útiles

### Script de Herramientas (`./scripts/dev-tools.sh`)

```bash
# Desarrollo
./scripts/dev-tools.sh dev-build     # Construir imagen de desarrollo
./scripts/dev-tools.sh dev-up        # Levantar entorno
./scripts/dev-tools.sh dev-shell     # Entrar al contenedor
./scripts/dev-tools.sh dev-test      # Ejecutar tests
./scripts/dev-tools.sh dev-down      # Parar entorno

# Producción
./scripts/dev-tools.sh prod-build    # Construir imagen de producción
./scripts/dev-tools.sh prod-up       # Levantar producción
./scripts/dev-tools.sh prod-down     # Parar producción

# Utilidades
./scripts/dev-tools.sh clean         # Limpiar imágenes
./scripts/dev-tools.sh logs          # Ver logs
./scripts/dev-tools.sh help          # Ayuda
```

## 🔄 Workflow de Desarrollo

### 1. Desarrollar y testear
```bash
# Levantar entorno
./scripts/dev-tools.sh dev-up

# Entrar al contenedor
./scripts/dev-tools.sh dev-shell

# Dentro del contenedor, trabajar normalmente
cd /app
python main.py --help
git status
docker ps
pytest test/
```

### 2. Hacer commits
```bash
# Desde dentro del contenedor (o desde fuera)
git add .
git commit -m "feat: nueva funcionalidad"
git push
```

### 3. Probar en producción
```bash
# Construir imagen de producción
./scripts/dev-tools.sh prod-build

# Probar en modo producción
./scripts/dev-tools.sh prod-up
```

## 🐞 Debug y Troubleshooting

### Ver logs en tiempo real
```bash
./scripts/dev-tools.sh logs
```

### Acceder con privilegios de root
```bash
docker-compose exec --user root sysadmintoolkit-backup-service-dev bash
```

### Reconstruir completamente
```bash
# Parar todo
docker-compose down

# Limpiar
./scripts/dev-tools.sh clean

# Reconstruir
./scripts/dev-tools.sh dev-build
./scripts/dev-tools.sh dev-up
```

## 🔒 Consideraciones de Seguridad

- El contenedor de desarrollo tiene acceso a Docker (`privileged: true`)
- Solo usar el entorno de desarrollo para desarrollo local
- La imagen de producción es mínima y segura
- No exponer el puerto de Docker en producción

## 💡 Tips

1. **Hot Reload**: Los cambios en el código se reflejan automáticamente (volumen montado)
2. **Persistencia**: Los datos de desarrollo persisten entre reinicios
3. **Aislamiento**: Cada entorno está completamente aislado
4. **Performance**: La imagen de producción es ~60% más pequeña que la de desarrollo

## 🆘 Ayuda

Si tienes problemas:
1. Revisa los logs: `./scripts/dev-tools.sh logs`
2. Reinicia el entorno: `./scripts/dev-tools.sh dev-down && ./scripts/dev-tools.sh dev-up`
3. Limpia y reconstruye: `./scripts/dev-tools.sh clean && ./scripts/dev-tools.sh dev-build`
