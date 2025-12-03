# Docker: Paso a Paso (Instalación → Backup)

Este documento es una **guía práctica** de principio a fin para instalar Docker y ejecutar tu primer backup.

---

## Paso 1: Descargar e Instalar Docker

### Windows

1. Ve a https://www.docker.com/products/docker-desktop
2. Descarga **Docker Desktop for Windows**
3. Ejecuta el instalador
4. Sigue el asistente (usa opciones por defecto)
5. Se pedirá reiniciar la máquina
6. Reinicia

### macOS

```bash
# Opción A: Homebrew
brew install docker

# Opción B: Descargar Docker Desktop
# https://www.docker.com/products/docker-desktop
```

### Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Logout y login para que funcione
```

---

## Paso 2: Verificar que Docker está instalado

Abre **PowerShell** (Windows) y ejecuta:

```powershell
docker --version
```

Deberías ver algo como:
```
Docker version 27.0.3, build 8604954
```

Si ves un error, Docker no está en el PATH. Reinicia PowerShell o la máquina.

---

## Paso 3: Construir la imagen Docker

Abre **PowerShell** y navega a la carpeta del proyecto:

```powershell
cd C:\Users\Justin\dbbackup\Backup_Script_maqueta
```

Construye la imagen:

```powershell
make build-image
```

O si no tienes `make` instalado:

```powershell
docker build -t backup_script:local .
```

**¿Qué sucede?**
- Docker descarga una imagen base con Python
- Instala paquetes del sistema (postgres-client, mysql-client, etc.)
- Instala dependencias Python (requests, typer, etc.)
- Copia tu código dentro
- Construye la imagen final (~600-800 MB)

**Tiempo**: 3-5 minutos la primera vez. Después se cachea.

**Espera hasta ver**: `Successfully tagged backup_script:local`

---

## Paso 4: Verificar que la imagen se construyó

```powershell
docker images | Select-String "backup_script"
```

Deberías ver:
```
backup_script   local   abc123def...   5 minutes ago   650MB
```

Si lo ves, ¡bien! La imagen está lista.

---

## Paso 5: Ejecutar tu primer backup

Ahora vamos a respaldar una base de datos usando el script PowerShell.

### Caso A: Si tienes Postgres en tu máquina local

```powershell
.\scripts\run_backup_docker.ps1 -DbType postgres -Database postgres -User postgres
```

Sigue los pasos:
1. Te pide contraseña (escríbela, no se mostrará)
2. El script verifica/construye imagen
3. Ejecuta el backup dentro del contenedor
4. Muestra progreso en vivo
5. Al terminar: `✅ Backup completado exitosamente`

### Caso B: Si tienes MySQL en tu máquina local

```powershell
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mysql -User root
```

### Caso C: Si tienes MongoDB en tu máquina local

```powershell
.\scripts\run_backup_docker.ps1 -DbType mongo -Database test -User admin
```

### Caso D: Usar la BD de prueba incluida (docker-compose)

Si no tienes BD instalada localmente, puedes levantar BDs de prueba en contenedores:

```powershell
docker-compose up -d
# Espera 10 segundos

# Ahora ejecuta backup de la Postgres de prueba
.\scripts\run_backup_docker.ps1 -DbType postgres -Database sampledb -User test -Host postgres
# O MongoDB:
.\scripts\run_backup_docker.ps1 -DbType mongo -Database sampledb -User test -Host mongo
```

Después, para detener:
```powershell
docker-compose down
```

---

## Paso 6: Verificar el backup

Si todo funcionó, deberías ver:

```powershell
cd .\backups
ls  # Ver archivos
```

Archivo del backup:
```
postgres_postgres_20251203_104438.dump
mysql_mysql_20251203_104439.dump.sql
mongo_test_20251203_104440.dump
```

También se registró en el historial:
```powershell
python src/cli.py history show
```

---

## ¿Qué sucede dentro del script?

El script PowerShell (`run_backup_docker.ps1`) hace esto automáticamente:

```
1. Pide contraseña sin mostrarla en pantalla
   └─ $Password = Read-Host -AsSecureString
   
2. Verifica que Docker está corriendo
   └─ docker ps (revisa estado)
   
3. Verifica si la imagen existe
   └─ docker images | grep backup_script
   
4. Si no existe, la construye
   └─ docker build -t backup_script:local .
   
5. Ejecuta contenedor con credenciales inyectadas
   └─ docker run -e PGPASSWORD=$Password ...
   
6. Dentro del contenedor, ejecuta backup
   └─ backup run --dbtype postgres ...
   
7. Mapea carpeta ./backups
   └─ -v ${PWD}/backups:/app/backups
   
8. Muestra output en vivo
   └─ Ves el progreso en PowerShell
   
9. Limpia variables sensibles
   └─ Remove-Item Env:PGPASSWORD
   
10. Archivo está en tu ./backups
```

---

## Opciones del Script

El script acepta parámetros. Ejemplos:

```powershell
# Básico
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# Con compresión
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip

# Con notificación webhook
.\scripts\run_backup_docker.ps1 -DbType mongo -Database mydb -User admin -NotifySlack

# Host personalizado (si tu BD está en otro servidor)
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -Host 192.168.1.50

# Puerto personalizado
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -Port 5433

# Todos juntos
.\scripts\run_backup_docker.ps1 `
  -DbType postgres `
  -Database production_db `
  -User backupuser `
  -Host 192.168.1.100 `
  -Port 5432 `
  -Compress zip `
  -Cloud s3 `
  -NotifySlack
```

---

## Conectar a Base de Datos Local desde Contenedor

### Problema

Dentro del contenedor, `localhost` = el contenedor, no tu PC.

### Solución

Usa `host.docker.internal` (Windows/Mac) o IP de tu red (Linux):

```powershell
# Windows/Mac: automático en el script, pero si ejecutas manual:
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -Host host.docker.internal

# Linux: usa IP de tu máquina
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -Host 192.168.1.10
```

El script usa `host.docker.internal` por defecto, así que no hay que hacer nada.

---

## Seguridad: ¿Dónde queda la contraseña?

### ✅ Seguro (lo que hace el script)

```powershell
# 1. Se pide sin mostrar en pantalla
$Password = Read-Host -Prompt "Password" -AsSecureString

# 2. Se inyecta solo al contenedor (no en línea de comandos visible)
docker run --rm -it -e PGPASSWORD=$Password ...

# 3. Se limpia inmediatamente después
Remove-Item Env:PGPASSWORD
```

**Resultado**: La contraseña nunca aparece en:
- Pantalla
- Historial de PowerShell
- Procesos visibles
- Archivos de log
- Archivos de config

### ❌ Inseguro (nunca hagas esto)

```powershell
# MAL: contraseña visible en historial
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -Password "MiPassword123"

# MAL: escrita en archivo
echo "docker run ... --password MiPassword123" > script.ps1

# MAL: en comando directo
docker run backup_script:local backup run --password "MiPassword123" ...
```

---

## Troubleshooting

### Error: `docker: command not found`

Docker no está en el PATH. Soluciones:

```powershell
# Opción A: Reinicia PowerShell
# Cierra PowerShell completamente
# Reabre

# Opción B: Reinicia tu PC

# Opción C: Verifica instalación
# Abre Docker Desktop manualmente
# Espera a que esté listo
# Reabre PowerShell
```

### Error: `permission denied while trying to connect to Docker daemon`

Solo en Linux. Solución:

```bash
# Agrega tu usuario al grupo docker
sudo usermod -aG docker $USER

# Logout y login (o reinicia)
logout
```

### Error: `container exited with error code 1`

El backup falló. Causas comunes:

- Contraseña incorrecta → Intenta manualmente
- BD no está corriendo → Levanta BD primero
- Host incorrecto → Verifica con `ping`
- Usuario no existe → Crea usuario en BD

Ejemplo para debuggear:

```powershell
# Abre shell interactivo en el contenedor
docker run -it backup_script:local bash

# Dentro del contenedor, prueba conectar
psql -h host.docker.internal -U postgres -c "SELECT 1"
mysql -h host.docker.internal -u root -p
```

### Error: `image not found`

La imagen no se construyó. Solución:

```powershell
make build-image
# o:
docker build -t backup_script:local .
```

### Contenedor sigue corriendo (no termina)

Presiona `Ctrl+C` para detener.

### Quiero ver qué hace el contenedor en vivo

El script ya muestra output. Pero si quieres más detalle:

```powershell
docker run -it backup_script:local bash
# Dentro, ejecuta comandos manualmente:
cd /app
python src/cli.py backup run --help
```

---

## Verificar Backup Guardado

```powershell
# Ver archivos guardados
ls .\backups

# Ver historial
python src/cli.py history show

# Ver último backup
python src/cli.py history show --limit 1
```

---

## Ejecutar Backups Regularmente (Automatización)

### Opción A: Task Scheduler (Windows)

```powershell
# Crear tarea que ejecuta el script cada día a las 2 AM
$action = New-ScheduledTaskAction `
  -Execute "PowerShell.exe" `
  -Argument "-File C:\ruta\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres"

$trigger = New-ScheduledTaskTrigger -Daily -At 2am

Register-ScheduledTask -TaskName "DailyBackupPostgres" -Action $action -Trigger $trigger
```

### Opción B: Cron (macOS/Linux)

```bash
# Editar crontab
crontab -e

# Añadir línea (backup diario a las 2 AM)
0 2 * * * cd /ruta/proyecto && ./scripts/run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres >> backup.log 2>&1
```

---

## Resumen: Desde 0 hasta Backup

| Paso | Comando | Tiempo |
|------|---------|--------|
| 1 | Descargar Docker | 5 min |
| 2 | Instalar Docker | 10 min |
| 3 | `make build-image` | 5 min |
| 4 | `.\scripts\run_backup_docker.ps1 ...` | 1-5 min |
| 5 | Backup guardado en `./backups` | ✅ |

**Total**: ~30 minutos la primera vez.
**Siguientes**: Solo 1-5 minutos por backup.

---

## Próximos Pasos

1. ✅ Instala Docker
2. ✅ Ejecuta `make build-image`
3. ✅ Ejecuta el script PowerShell
4. ✅ Verifica backup en `./backups`
5. ⏭️ Configura notificaciones (opcional)
6. ⏭️ Automatiza con Task Scheduler o Cron

¿Listo? ¡Sigue el Paso 1 en tu terminal!
