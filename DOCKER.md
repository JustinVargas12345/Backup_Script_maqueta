# Guía Docker: Empaquetar y ejecutar Backup_Script

## ¿Qué es Docker?

Docker es como un "contenedor" que empaqueta tu aplicación **junto con todo lo que necesita** para funcionar:
- Sistema operativo base (Linux)
- Librerías del sistema (psql, mysql, mongosh, etc.)
- Dependencias Python (requests, typer, etc.)
- El código de tu aplicación

**Ventajas**:
1. No necesitas instalar nada en tu máquina local (excepto Docker).
2. Funciona igual en tu PC, en un servidor, en la nube.
3. Aislado: no contamina tu sistema.

## Instalación de Docker

### Windows

Descarga e instala **Docker Desktop**:
- https://www.docker.com/products/docker-desktop
- Requiere Hyper-V o WSL 2 activado.
- Verifica: abre PowerShell y ejecuta `docker --version`

### macOS

```bash
brew install docker
# o descarga Docker Desktop: https://www.docker.com/products/docker-desktop
```

### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Necesitarás hacer logout y login para que funcione
```

## Flujo Completo: Build → Run

### 1️⃣ Construir la imagen (BUILD)

La primera vez, necesitas "compilar" la imagen Docker. Esto descarga la base (`python:3.11`), instala paquetes (postgres-client, mysql-client, etc.) e incluye tu código.

```powershell
cd C:\path\to\Backup_Script_maqueta

# Opción A: con Make (si está instalado)
make build-image

# Opción B: con Docker directamente
docker build -t backup_script:local .

# Opción C: Incluir MongoDB tools (aumenta tamaño ~200MB)
docker build --build-arg INSTALL_MONGO=true -t backup_script:local .
```

**¿Qué hace?**
1. Lee el archivo `Dockerfile` (receta de instrucciones).
2. Descarga imagen base `python:3.11-slim` (~150 MB).
3. Instala paquetes del sistema (postgres-client, mysql-client, etc.) (~200 MB).
4. Instala dependencias Python (`pip install -r requirements.txt`) (~100 MB).
5. Copia el código fuente dentro de la imagen.
6. Resultado: imagen comprimida `backup_script:local` (~600 MB, ~800 MB con Mongo tools).

**Tiempo**: 3-5 minutos la primera vez (después se cachea y es más rápido).

### 2️⃣ Ejecutar backups (RUN)

Una vez que tienes la imagen, ejecutas contenedores (instancias) a partir de ella:

#### Opción A: Usar el script PowerShell ✅ RECOMENDADO

```powershell
# Postgres
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# MySQL con compresión
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip

# MongoDB con notificación
.\scripts\run_backup_docker.ps1 -DbType mongo -Database Algoritmo -User admin -NotifySlack
```

**¿Qué hace el script?**
1. Solicita contraseña de forma segura (sin mostrar en pantalla).
2. Verifica que la imagen existe; si no, la construye.
3. Crea un contenedor y ejecuta el backup dentro.
4. Mapea carpeta `./backups` local al contenedor.
5. Limpia variables sensibles después.

#### Opción B: Manual (para entendidos)

```powershell
# Postgres directo
$env:PGPASSWORD = 'tu_password'

docker run --rm -it `
  -e PGPASSWORD `
  -v ${PWD}/backups:/app/backups `
  -w /app `
  backup_script:local `
  backup run --dbtype postgres --host host.docker.internal --port 5432 --user postgres --password '<PASSWORD>' --database mydb

# Limpiar después
Remove-Item Env:PGPASSWORD
```

## ¿Cómo funciona el mapeo de carpetas?

```
-v ${PWD}/backups:/app/backups
    ↑                ↑
    Tu máquina      Dentro del contenedor
    
Tu PC: C:\backup_script\backups          → Contenedor: /app/backups
Si guardas archivo en /app/backups      → Aparece en C:\backup_script\backups
```

Esto permite que los backups se guarden en tu máquina.

## Conectar a bases de datos locales desde el contenedor

### Caso 1: BD está en tu máquina (localhost)

Desde el contenedor **NO** puedes usar `localhost` ni `127.0.0.1` (eso es el contenedor mismo, no tu host).

**Usa `host.docker.internal`**:

```powershell
docker run ... backup_script:local backup run --host host.docker.internal --dbtype postgres ...
```

### Caso 2: BD está en otro servidor/contenedor Docker

Usa el IP o nombre del host directamente:

```powershell
# Si la BD está en 192.168.1.50
docker run ... backup_script:local backup run --host 192.168.1.50 --dbtype postgres ...

# Si usas docker-compose con servicios (postgres, mysql, mongo)
docker-compose up -d  # Levanta BD
docker run ... --host host.docker.internal ... # o el nombre del servicio
```

## Imágenes multitag: compatible con Docker Hub

Si quieres publicar en Docker Hub, primero regístrate en https://hub.docker.com y crea un repositorio.

```powershell
# Tag la imagen con tu repo
docker tag backup_script:local youruser/backup_script:latest

# Push (requiere `docker login` primero)
docker login
docker push youruser/backup_script:latest
```

Otros usuarios pueden descargar e usar:
```powershell
docker run --rm -it -v ${PWD}/backups:/app/backups youruser/backup_script:latest backup run ...
```

## Tamaño y optimización

- **Tamaño actual**: ~600-800 MB (Python + postgres-client + mysql-client + deps).
- **Con MongoDB tools**: ~1 GB (heredado, deshabilitado por defecto).
- **Con mssql-tools**: ~1.2 GB (requiere Microsoft repos, deshabilitado por defecto).

Si necesitas una imagen más ligera, puedes:
1. Usar multi-stage build (builder → runtime).
2. Usar imagen base `alpine` en lugar de `slim` (más pequeña, menos tooling).
3. Arquitectura de contenedores separados (orquestador + worker containers).

## Troubleshooting

### Error: `docker: command not found`

Docker no está instalado o no está en el PATH. Reinstala Docker Desktop y asegúrate de reiniciar PowerShell.

### Error: `cannot create container: name already in use`

Un contenedor anterior no se eliminó. Limpia:
```powershell
docker ps -a                    # Ver todos los contenedores
docker rm <container_id>        # Eliminar un contenedor
docker rm $(docker ps -a -q)    # Eliminar todos (cuidado!)
```

### Error: `no route to host`

No puedes conectar a BD en tu máquina local. Usa `host.docker.internal` en lugar de `localhost`.

### Error: `password authentication failed`

Verifica credenciales (usuario, contraseña, BD). Recuerda que dentro del contenedor, tu BD local está en `host.docker.internal`, no `localhost`.

### Imagen tarda mucho en descargarse/construirse

Es normal la primera vez. Docker cachea capas, así que rebuild posteriores son más rápidos.

### Quiero ver lo que hace el contenedor en tiempo real

Usa `-it` (interactivo + terminal):
```powershell
docker run -it backup_script:local bash
# Dentro del contenedor, eres root. Puedes explorar:
# ls /app
# which psql
# python --version
# exit para salir
```

## Resumen de comandos útiles

```powershell
# Construir
docker build -t backup_script:local .
make build-image

# Listar imágenes
docker images

# Ejecutar backup (script)
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# Ejecutar backup (manual)
docker run --rm -it -v ${PWD}/backups:/app/backups backup_script:local backup run ...

# Ver contenedores activos
docker ps

# Ver todos los contenedores (incluso stopped)
docker ps -a

# Eliminar imagen
docker rmi backup_script:local

# Limpiar todo (cuidado!)
docker system prune -a

# Login a Docker Hub
docker login

# Push a Docker Hub
docker tag backup_script:local youruser/backup_script:latest
docker push youruser/backup_script:latest
```

## Próximos pasos

1. **Ejecutar el primer backup con Docker** usando el script PowerShell.
2. **Probar diferentes BD** (postgres, mysql, mongo).
3. **Configurar notificaciones** (webhook) si la necesitas.
4. **Publicar en Docker Hub** si quieres compartir la imagen.
5. **Integrar en CI/CD** (GitHub Actions, GitLab CI, Jenkins) para automatizar backups.

¿Preguntas? Revisa el `README.md` principal o la sección "Docker: construir imagen" en README.
