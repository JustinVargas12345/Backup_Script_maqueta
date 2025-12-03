# Guía de Instalación y Uso: Backup_Script con Docker

**⏱️ ¿Sin tiempo? Lee primero**: `DOCKER_PASO_A_PASO.md` (guía paso a paso de instalación)

Este documento es tu **punto de partida** para entender y ejecutar la aplicación.

## 🎯 Resumen Rápido

### Opción 1: Ejecutar con Docker (RECOMENDADO - sin instalar nada)

```powershell
# 1. Construir imagen (solo una vez, ~5 minutos)
make build-image

# 2. Ejecutar backup
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres
# Se pide contraseña de forma segura (sin mostrar)
# Los backups se guardan en ./backups
```

**Para la guía completa paso a paso** → Abre `DOCKER_PASO_A_PASO.md`

### Opción 2: Ejecutar localmente (requiere instalar binarios)

```powershell
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Instalar clientes de BD (Postgres, MySQL, MongoDB, SQL Server)
# Ver sección "Instalación de Binarios" abajo

# 3. Ejecutar
python src/cli.py backup run --dbtype postgres --host localhost --user postgres --password "<PASSWORD>" --database mydb
```

---

## 📦 Opción 1: Docker (Recomendado)

### Requisitos

Solo necesitas **Docker** instalado. Descárgalo de https://www.docker.com

### Paso 1: Construir la imagen

```powershell
cd C:\ruta\al\proyecto

# Opción A (si tienes Make instalado)
make build-image

# Opción B (con Docker directamente)
docker build -t backup_script:local .
```

Esto:
1. Descarga imagen base Python con Linux.
2. Instala postgres-client, mysql-client, herramientas comunes.
3. Instala dependencias Python (requests, typer, etc.).
4. Copia tu código dentro de la imagen.

**Tiempo**: 3-5 minutos la primera vez. Rerun posteriores se cachean.

### Paso 2: Ejecutar backups

Usa el script PowerShell que solicita contraseña de forma segura:

```powershell
# Postgres
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# MySQL con compresión
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip

# MongoDB con notificación webhook
.\scripts\run_backup_docker.ps1 -DbType mongo -Database Algoritmo -User admin -NotifySlack
```

**Flujo del script**:
1. Pide contraseña sin mostrarla (seguro).
2. Verifica/construye imagen si falta.
3. Ejecuta contenedor con las credenciales inyectadas.
4. Guarda backups en `./backups`.
5. Limpia variables sensibles después.

### Paso 3 (Opcional): Subir a Docker Hub

```powershell
# 1. Crear repo en https://hub.docker.com

# 2. Login
docker login
# Pide usuario y contraseña de Docker Hub

# 3. Tag y push
docker tag backup_script:local tusuario/backup_script:latest
docker push tusuario/backup_script:latest
```

Otros usuarios pueden usar:
```powershell
docker pull tusuario/backup_script:latest
docker run --rm -it -v ${PWD}/backups:/app/backups tusuario/backup_script:latest backup run ...
```

---

## 💻 Opción 2: Instalación Local

### Requisitos

- **Python 3.9+** (https://www.python.org)
- **Binarios de BD** (postgres, mysql, mongo, etc.)

### Paso 1: Instalar dependencias Python

```powershell
pip install -r requirements.txt
```

### Paso 2: Instalar binarios

#### Windows (Chocolatey)

```powershell
# Si no tienes Chocolatey: https://chocolatey.org/install

choco install postgresql      # Instala psql, pg_restore
choco install mysql           # Instala mysql
choco install mongodb         # Instala mongorestore, mongosh
choco install mssql-tools14   # Instala sqlcmd (SQL Server)
```

#### macOS (Homebrew)

```bash
brew install libpq           # Postgres
brew install mysql           # MySQL
brew tap mongodb/brew && brew install mongodb-database-tools  # MongoDB
```

#### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y postgresql-client default-mysql-client mongodb-clients
```

### Paso 3: Usar la aplicación

```powershell
# Ver ayuda
python src/cli.py --help

# Backup Postgres
python src/cli.py backup run \
  --dbtype postgres \
  --host localhost \
  --port 5432 \
  --user postgres \
  --password "password" \
  --database mydb \
  --backup-type full

# Backup MySQL
python src/cli.py backup run \
  --dbtype mysql \
  --host localhost \
  --port 3306 \
  --user root \
  --password "password" \
  --database mydb \
  --compress zip
```

---

## 🔍 Verificar Binarios

```powershell
# Con Docker (no necesario, ya están dentro)
docker run --rm backup_script:local utils check-binaries

# Localmente
python src/cli.py utils check-binaries
```

Te mostrará qué binarios encontró y cuáles faltan.

---

## 🔐 Seguridad: Manejar Contraseñas

### ✅ Forma Segura (recomendada)

Usa el script PowerShell o patrón "solicitar → inyectar → limpiar":

```powershell
# El script hace esto por ti:
$Password = Read-Host -Prompt "Password" -AsSecureString
# → No aparece en pantalla ni en historial
docker run -e PGPASSWORD=$PlainPassword ...
# → Se inyecta solo al contenedor
Remove-Item Env:PGPASSWORD
# → Se limpia después
```

### ❌ Forma INSEGURA (nunca hagas esto)

```powershell
# BAD: la contraseña queda en historial de PowerShell
python src/cli.py backup run --password "MiPassword123" ...

# BAD: aparece en `ps auxww`
docker run backup_script:local backup run --password "MiPassword123" ...
```

---

## 🌐 Webhooks y Notificaciones

Configurar notificaciones POST (p. ej. a Slack, tu servidor, etc.):

```powershell
# 1. Configurar URL
python src/cli.py config notify-set --url "https://webhook.example.com/notify"

# 2. Configurar método de autenticación (sin almacenar secreto)
python src/cli.py config notify-auth-set --method env --token-type jwt --env-var NOTIFY_SECRET

# 3. Antes de ejecutar, inyectar secreto
$env:NOTIFY_SECRET = 'tu_secret'

# 4. Ejecutar con --notify-slack
python src/cli.py backup run --dbtype postgres ... --notify-slack

# 5. Limpiar
Remove-Item Env:NOTIFY_SECRET
```

Se enviará un POST JSON con el resultado del backup.

---

## 📁 Estructura de Carpetas

```
Backup_Script_maqueta/
├── Dockerfile                    # Receta para construir imagen Docker
├── .dockerignore                 # Archivos a excluir del build
├── .gitignore                    # Archivos a no comitear
├── README.md                     # Documentación principal
├── DOCKER.md                     # Guía Docker detallada
├── SETUP_GUIDE.md               # Este archivo
├── makefile                      # Comandos útiles (make build-image, etc.)
├── requirements.txt              # Dependencias Python
├── config/
│   ├── config.toml              # ⚠️ NO COMITEES: contiene credenciales
│   ├── example.env              # Plantilla de variables de entorno
│   └── loggin.conf              # Configuración de logs
├── src/
│   ├── cli.py                   # Punto de entrada principal
│   ├── cli/                     # Subcomandos (backup, restore, config, etc.)
│   ├── db_connectors/           # Conectores para Postgres, MySQL, Mongo, SQL Server
│   ├── utils/                   # Utilidades (logger, notify, compress, etc.)
│   └── ...
├── scripts/
│   ├── run_backup_docker.ps1    # ✅ Script PowerShell para ejecutar con Docker
│   └── ...
├── backups/                      # 📁 Aquí se guardan los backups
├── docker-compose.yml            # Servicios de BD locales (para desarrollo)
└── ...
```

---

## ❓ Preguntas Frecuentes

### P: ¿Necesito instalar binarios (psql, mysql) si uso Docker?

**R**: No. Docker los instala dentro del contenedor. Solo necesitas Docker.

### P: ¿Cómo conecto a una BD en mi máquina local desde el contenedor?

**R**: Usa `host.docker.internal` en lugar de `localhost`:

```powershell
docker run ... backup_script:local backup run --host host.docker.internal ...
```

### P: ¿Dónde se guardan los backups?

**R**: En la carpeta `./backups` del repositorio. El script mapea esa carpeta al contenedor.

### P: ¿Puedo ejecutar la app en un servidor sin Docker?

**R**: Sí, pero necesitas instalar todos los binarios en el servidor. Docker es más simple.

### P: ¿Cómo limpio las imágenes viejas?

**R**: 
```powershell
docker images
docker rmi backup_script:local
docker system prune -a   # Limpia todo sin usar
```

### P: ¿Es seguro guardar la contraseña en `config.toml`?

**R**: No. Usa variables de entorno o el script PowerShell que solicita en tiempo de ejecución.

---

## 🚀 Próximos Pasos

1. **Instala Docker** (si vas a usar Opción 1).
2. **Construye la imagen** (`make build-image`).
3. **Ejecuta un backup de prueba** (usa el script PowerShell).
4. **Revisa el historial** (`python src/cli.py history show`).
5. **Configura notificaciones** si lo necesitas.
6. **Automatiza** en CI/CD o tu scheduler favorito.

---

## 📚 Documentación Adicional

- **README.md** — Documentación completa, ejemplos de todos los comandos.
- **DOCKER.md** — Guía específica de Docker, troubleshooting.
- **config/example.env** — Variables de entorno recomendadas.

¿Preguntas? Revisa README.md o DOCKER.md. ¡Estamos aquí para ayudar! 🎉
