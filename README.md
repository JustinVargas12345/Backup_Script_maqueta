# Backup_Script_maqueta

Herramienta para backups y restauraciones de bases de datos (Postgres, MySQL, MongoDB, SQL Server).

## Requisitos del sistema (binarios)

Esta aplicación depende de varios clientes nativos que deben estar disponibles en el PATH del sistema:

- PostgreSQL: `psql`, `pg_restore`
- MySQL: `mysql`, `mysqladmin`
- MongoDB: `mongorestore`, `mongosh` (o `mongo` en versiones antiguas)
- SQL Server: `sqlcmd`, `bcp` (si se usan herramientas de SQL Server)

Instalación (ejemplos):

- Debian / Ubuntu (ejemplo):

```bash
sudo apt-get update
sudo apt-get install -y postgresql-client default-mysql-client mongodb-clients
```

- macOS (Homebrew):

```bash
brew install libpq
brew link --force libpq
brew install mysql
brew tap mongodb/brew && brew install mongodb-database-tools
```

- Windows (Chocolatey):

```powershell
choco install postgresql
choco install mysql
choco install mongodb
choco install microsoft-odbc-driver-preview # o mssql-tools según necesidad
```

Nota: los comandos pueden variar según versión y distribución; revisa la documentación oficial de cada proveedor.

## Dependencias Python

Las dependencias Python están listadas en `requirements.txt`. Algunas librerías son opcionales según uso de cloud:

- Recomendadas si vas a usar subida a la nube: `boto3`, `google-cloud-storage`, `azure-storage-blob`.

Instalar rápidamente:

```bash
pip install -r requirements.txt
```

## Uso en Docker (recomendado para evitar problemas de binarios)

### ¿Qué es Docker y por qué usarlo?

Docker te permite empaquetar la aplicación **junto con todos los binarios** (psql, mysql, mongorestore, etc.) en una **imagen** que se ejecuta en un **contenedor** aislado. Ventajas:

1. **Sin depender del host**: No necesitas instalar psql, mysql, mongosh en tu máquina — Docker los instala dentro del contenedor.
2. **Reproducible**: La misma imagen funciona igual en tu PC, en un servidor, en CI/CD, etc.
3. **Limpio**: No contaminas tu sistema instalando herramientas en el PATH.
4. **Fácil de desplegar**: Solo necesitas Docker instalado en el host.

### ¿Cómo funciona el empaquetamiento?

**El Dockerfile**:
- Base: `python:3.11-slim` (Linux con Python preinstalado).
- Instala binarios: `postgresql-client`, `default-mysql-client`, herramientas comunes (zip, tar, curl).
- Instala dependencias Python: `pip install -r requirements.txt`.
- Copia el código fuente de la app dentro de la imagen.
- Define punto de entrada: `python src/cli.py` (cuando ejecutas el contenedor, llama al CLI).

**El proceso de build**:
```
1. docker build -t backup_script:local .  (lee Dockerfile, crea imagen)
   ↓
2. Docker descarga imagen base Python
   ↓
3. Instala paquetes apt (postgres-client, mysql-client, etc.)
   ↓
4. Instala paquetes Python (requests, typer, etc.)
   ↓
5. Copia código fuente (/app)
   ↓
6. Imagen lista (backup_script:local) ~ 800-1000 MB
```

**Ejecutar un comando dentro del contenedor**:
```powershell
docker run --rm -it -v ${PWD}/backups:/app/backups backup_script:local backup run --dbtype postgres ...
       ↑      ↑  ↑  ↑                    ↑                       ↑
       │      │  │  └─ Mapea carpeta local ↔ contenedor          └─ Comando a ejecutar dentro
       │      │  └─ Interactivo (pedir input, ver output en vivo)
       │      └─ Elimina contenedor después (no deja basura)
       └─ Ejecuta la imagen
```

### Paso 1: Construir la imagen (solo una vez)

```powershell
make build-image
# o directamente:
docker build -t backup_script:local .
```

Isso descargas/instala todo. La primera vez tarda 2-5 minutos (depende de conexión).

### Paso 2: Ejecutar backups (opción A — Script PowerShell recomendado)

Usamos el script `scripts/run_backup_docker.ps1` que maneja contraseñas y variables sensibles de forma segura:

```powershell
# Postgres
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# MySQL con compresión
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip

# MongoDB con notificación webhook
.\scripts\run_backup_docker.ps1 -DbType mongo -Database Algoritmo -User admin -NotifySlack
```

El script:
1. **Solicita contraseña** de forma segura (sin mostrar en pantalla).
2. **Construye imagen** si no existe.
3. **Ejecuta contenedor** inyectando variables de entorno (contraseña, etc.).
4. **Limpia variables** después (no quedan en el entorno).
5. **Guarda backup** en `./backups` (mapeado desde el contenedor).

### Paso 2b: Ejecutar backups (opción B — Línea de comandos manual)

Si prefieres no usar el script:

```powershell
# Postgres
$env:PGPASSWORD = 'mi_password'
docker run --rm -it `
  -e PGPASSWORD `
  -v ${PWD}/backups:/app/backups `
  -w /app `
  backup_script:local `
  backup run --dbtype postgres --host host.docker.internal --port 5432 --user postgres --password '<PASSWORD>' --database mydb
Remove-Item Env:PGPASSWORD

# MySQL
docker run --rm -it `
  -v ${PWD}/backups:/app/backups `
  backup_script:local `
  backup run --dbtype mysql --host host.docker.internal --user root --password 'mypass' --database mydb --compress zip
```

**Nota sobre `host.docker.internal`**: dentro del contenedor, para conectar a BD en tu máquina local, usa `host.docker.internal` en lugar de `localhost`.

### Contenedores separados para binarios pesados (arquitectura avanzada)

Si quieres reducir tamaño de imagen o tener control granular, puedes:

1. **Imagen app ligera**: solo Python + deps (300 MB).
2. **Contenedor Postgres**: imagen oficial `postgres:16` (para backups/restore de Postgres).
3. **Contenedor MongoDB**: imagen oficial `mongo:7` (para backups/restore de Mongo).
4. **Orquestador**: tu app llama a esos contenedores con `docker exec` o `docker run` cuando necesita un binario.

Por ahora la solución "todo-en-uno" (Dockerfile actual) es más simple. Si necesitas esa arquitectura avanzada, avísame.

### Seguridad: cómo manejar contraseñas y secretos en Docker

**IMPORTANTE**: Nunca pases contraseñas en línea de comandos visible o las escribas en scripts sin protección. Docker permite inyectar variables de entorno de forma segura:

**✅ Forma SEGURA** (usa `scripts/run_backup_docker.ps1` o patrón similar):
```powershell
# 1. Solicitar contraseña sin echo (no aparece en pantalla ni en historial)
$Password = Read-Host -Prompt "Password" -AsSecureString
$PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))

# 2. Inyectar como variable de entorno al contenedor (no en línea de comandos)
docker run --rm -it -e PGPASSWORD=$PlainPassword backup_script:local backup run ...

# 3. Limpiar variable después
Remove-Item Env:PGPASSWORD
```

**❌ Forma INSEGURA** (nunca hagas esto):
```powershell
# BAD: la contraseña aparece en:
# - historial de PowerShell
# - log de Docker
# - procesos visibles (ps auxww)
docker run --rm -it backup_script:local backup run --password 'MiPassword123' ...
```

**Recomendaciones**:
- Usa `scripts/run_backup_docker.ps1` que implementa esto correctamente.
- O si ejecutas manualmente, sigue el patrón "solicitar → inyectar → limpiar" arriba.
- Para CI/CD (GitHub Actions, GitLab CI, etc.), usa Docker secrets o variables de secreto de la plataforma.
- En Kubernetes, usa `Secret` resources.

## Comprobación de binarios

Hay un comando CLI para comprobar la presencia de los binarios necesarios:

```bash
python -m cli.app utils check-binaries
```

O también puedes ejecutar `src/utils/bin_checker.py` directamente:

```bash
python src/utils/bin_checker.py
```

## Recomendaciones

- Para despliegues reproducibles, usa Docker y publica la imagen con los clientes incluidos.
- Mantén los binarios del motor en versiones compatibles con tus bases de datos.
- Si prefieres no depender de binarios en el host, crea contenedores específicos para cada operación (p. ej. un contenedor con `pg_restore`) y ejecuta dichos contenedores desde la app.

---

Si quieres, puedo:
- Añadir un comando que verifique versiones de cada cliente (`psql --version`, etc.).
- Ajustar el `Dockerfile` para incluir herramientas de SQL Server y/o versiones específicas.
- Crear un script de instalación cross-platform (PowerShell + Bash) que intente instalar lo básico.

## Ejemplos prácticos de uso (comandos exactos)

Los ejemplos siguientes están escritos para ejecutarse desde la raíz del repositorio usando PowerShell.

- Nota general: el entrypoint del CLI es `python src/cli.py <grupo> <comando> ...`.


---

### 1) Backup — Ejemplo (sin compresión)

Postgres (sin compresión):
```powershell
# Evita exponer contraseñas en ejemplos; usa variables de entorno o placeholders
python src/cli.py backup run --dbtype postgres --host "localhost" --port 5432 --user "postgres" --password "<PASSWORD>" --database "postgres" --backup-type full
```

MySQL (sin compresión):
```powershell
python src/cli.py backup run --dbtype mysql --host "localhost" --port 3306 --user "root" --password "<PASSWORD>" --database "mi_db" --backup-type full
```

MongoDB (sin compresión):
```powershell
python src/cli.py backup run --dbtype mongo --host "localhost" --port 27017 --user "admin" --password "<PASSWORD>" --database "Algoritmo" --backup-type full
```


### 2) Backup — Ejemplo (con compresión)

Puedes usar la opción `--compress` con valores comunes como `zip`, `tar` o `gz` / `tar.gz` (según tu preferencia y la utilidad `auto_compress` disponible en el proyecto):

Postgres + ZIP:
```powershell
python src/cli.py backup run --dbtype postgres --host "localhost" --port 5432 --user "postgres" --password "<PASSWORD>" --database "postgres" --backup-type full --compress zip
```

MySQL + TAR.GZ:
```powershell
python src/cli.py backup run --dbtype mysql --host "localhost" --port 3306 --user "root" --password "<PASSWORD>" --database "mi_db" --backup-type full --compress tar
```

Mongo + gzip (ejemplo):
```powershell
python src/cli.py backup run --dbtype mongo --host "localhost" --port 27017 --user "admin" --password "<PASSWORD>" --database "Algoritmo" --backup-type full --compress gz
```

Si quieres omitir la verificación de binarios en ambientes donde sabes que todo está instalado, añade `--skip-binary-check` al comando `backup run`.


### 3) Restore — Método `run` (nuevo, recomendado)

El comando `restore run` es el nuevo método implementado que:
- Busca automáticamente el backup más reciente si no especificas archivo.
- Valida conexión a la base antes de restaurar (opcional con `--skip-connection-check`).
- Extrae archivos comprimidos (.zip, .tar.gz, .tgz, .tar) automáticamente.
- Registra operación en historial (`backup_history.json`).
- Maneja autenticación robusta con múltiples intentos según tipo de BD.

#### Restore MongoDB (con manejo de múltiples mecanismos de autenticación)

El método replica la lógica del `MongoConnector` e intenta conexión sin auth primero, luego con usuario/contraseña y diferentes mecanismos SCRAM-SHA-256 / SCRAM-SHA-1:

Restaurar Mongo a base nueva (modo automático — busca último backup):
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password '<PASSWORD>'
```

Restaurar Mongo especificando archivo:
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password 'Laboratorio1' --backup-file "backups\mongo_Algoritmo_20251203_104438.dump"
```

Con verificación de hash:
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password '<PASSWORD>' --backup-file "backups\mongo_Algoritmo_20251203_104438.dump" --verify-hash
```

Omitir validación de conexión (si hay problemas de permisos):
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password 'Laboratorio1' --skip-connection-check
```

**Notas MongoDB:**
- Maneja automáticamente archivos `.dump.tar.gz` (extrae y detecta directorio/marcador).
- Intenta 4 mecanismos en orden: sin auth → con auth + authSource → SCRAM-SHA-256 → SCRAM-SHA-1.
- Si `Script.bson` está vacío, la colección se crea pero sin documentos (normal si el backup no contenía datos).
- Usa `mongosh` con credenciales `admin/Laboratorio1` para verificar: `use Algoritmo; db.Script.countDocuments();`.

#### Restore PostgreSQL (con PGPASSWORD env var y shell execution)

El método replica la ejecución del `PostgresConnector` usando comando shell con PGPASSWORD:

Restaurar Postgres a base nueva (modo automático):
```powershell
# Usar variables de entorno para evitar exponer contraseñas en el listado de procesos
$env:PGPASSWORD = '<PASSWORD>'
python src/cli.py restore run --dbtype postgres --database test_restore_pg --host localhost --port 5432 --user postgres --password '<PASSWORD>'
Remove-Item Env:PGPASSWORD
```

Restaurar Postgres especificando archivo:
```powershell
$env:PGPASSWORD = 'TuPassword'
python src/cli.py restore run --dbtype postgres --database test_restore_pg --host localhost --port 5432 --user postgres --password 'TuPassword' --backup-file "backups\postgres_postgres_20251201_094150.dump"
Remove-Item Env:PGPASSWORD
```

**Notas PostgreSQL:**
- Detecta automáticamente si el archivo es `.sql` (usa `psql`) o binario (usa `pg_restore`).
- Usa `shell=True` y variable de entorno `PGPASSWORD` para evitar prompts interactivos.
- Captura stdout/stderr para logging detallado en `backup_master_log.txt`.

#### Restore MySQL (con conector detallado)

El método usa la ruta detectada por `MySQLConnector` y soporta logging ampliado:

Restaurar MySQL a base nueva (modo automático):
```powershell
python src/cli.py restore run --dbtype mysql --database test_restore_mysql --host localhost --port 3306 --user root --password 'miPassword'
```

Restaurar MySQL especificando archivo:
```powershell
python src/cli.py restore run --dbtype mysql --database test_restore_mysql --host localhost --port 3306 --user root --password 'miPassword' --backup-file "backups\mysql_mysql_20251201_141236.dump.sql"
```

**Notas MySQL:**
- Requiere archivo `.sql` (no carpetas).
- Usa el cliente `mysql` detectado automáticamente por el conector.
- Lee el archivo como texto (UTF-8) para evitar problemas de codificación en Windows.
- Captura y registra stdout/stderr del comando.

#### Restore SQL Server

Restaurar SQL Server a base nueva (modo automático):
```powershell
python src/cli.py restore run --dbtype sqlserver --database test_restore_mssql --host localhost --port 1433 --user sa --password 'TuSaPassword'
```

Restaurar SQL Server especificando archivo:
```powershell
python src/cli.py restore run --dbtype sqlserver --database test_restore_mssql --host localhost --port 1433 --user sa --password 'TuSaPassword' --backup-file "backups\nombre_backup.bak"
```

**Notas SQL Server:**
- Usa `sqlcmd` para ejecutar comandos T-SQL `RESTORE DATABASE`.
- Usa flags `WITH REPLACE` para sobrescribir BD existente.
- Requiere que los archivos lógicos (`.mdf`, `.ldf`) estén en rutas válidas; verifica configuración según tu instalación.

---

### 3b) Opciones comunes para `restore run`

Parámetros disponibles:

| Parámetro | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `--dbtype` | str | *requerido* | `postgres`, `mysql`, `mongo`, `sqlserver` |
| `--database` | str | *requerido* | Nombre de la BD destino |
| `--host` | str | `localhost` | Host del servidor |
| `--port` | int | según BD | Puerto (5432 postgres, 3306 mysql, 27017 mongo, 1433 sqlserver) |
| `--user` | str | *requerido* | Usuario |
| `--password` | str | *requerido* | Contraseña |
| `--backup-file` | str | None | (Opcional) Ruta exacta del archivo; si no especifica, busca automáticamente |
| `--verify-hash` | flag | False | Calcula y registra SHA256 del backup |
| `--skip-binary-check` | flag | False | Omite verificación de binarios disponibles |
| `--skip-connection-check` | flag | False | Omite validación de conexión previa |

Ejemplos con combinaciones útiles:

Restaurar con hash verificación y omitir validación de conexión:
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password 'Laboratorio1' --verify-hash --skip-connection-check
```

Restaurar múltiples BDs en secuencia (script PowerShell):
```powershell
# Restaurar todas las BDs de una sola vez
foreach ($db in @('Algoritmo', 'otra_db')) {
    python src/cli.py restore run --dbtype mongo --database $db --host localhost --port 27017 --user admin --password 'Laboratorio1'
}
```

---

### 3c) Restauración manual (comandos shell, si prefieres no usar CLI)

Si prefieres ejecutar comandos directamente sin pasar por la CLI:

MongoDB (con verbose para ver qué se restaura):
```powershell
& "C:\Program Files\MongoDB\Tools\bin\mongorestore.EXE" `
  --host=localhost --port=27017 `
  --username=admin --password='Laboratorio1' --authenticationDatabase=admin `
  --drop --verbose "backups\mongo_Algoritmo_20251203_104438"
```

PostgreSQL (con PGPASSWORD):
```powershell
$env:PGPASSWORD = '<PASSWORD>'
& "C:\Program Files\PostgreSQL\15\bin\pg_restore.exe" `
  -h localhost -p 5432 -U postgres `
  -d test_db "backups\postgres_postgres_20251201_094150.dump"
Remove-Item Env:PGPASSWORD
```

MySQL (piping archivo SQL):
```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" `
  -h localhost -P 3306 -u root -p'miPassword' test_db < "backups\mysql_mysql_20251201_141236.dump.sql"
```

---

### 3d) Verificación post-restauración

Tras restaurar, verifica que los datos llegaron correctamente:

MongoDB — contar documentos:
```powershell
& "C:\Program Files\MongoDB\mongosh\bin\mongosh.exe" --host localhost --port 27017 -u 'admin' -p '<PASSWORD>' --authenticationDatabase 'admin' --eval "use Algoritmo; db.Script.countDocuments();"
```

PostgreSQL — listar tablas:
```powershell
$env:PGPASSWORD = 'TuPassword'
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d test_db -c "\dt"
Remove-Item Env:PGPASSWORD
```

MySQL — listar tablas:
```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -h localhost -P 3306 -u root -p'miPassword' test_db -e "SHOW TABLES;"
```

---

Puedes añadir `--verify-hash` al comando `restore run` para que el programa calcule y muestre el SHA256 del archivo antes de proceder.


### 4) Comandos `utils` (ejemplos)

Calcular hash SHA256:
```powershell
python src/cli.py utils hash backups/postgres_postgres_20251202_154821.dump --method sha256
```

Comprimir un archivo (comando utilitario directo):
```powershell
python src/cli.py utils compress backups/postgres_postgres_20251202_154821.dump --format zip
```

Subir un archivo a la nube (ejemplo AWS S3):
```powershell
python src/cli.py utils upload backups/postgres_postgres_20251202_154821.dump --provider aws --bucket mi-bucket --destination backups/postgres.dump
```

Comprobar binarios necesarios (te muestra la ruta encontrada):
```powershell
python src/cli.py utils check-binaries
```


### 5) Historial

Mostrar historial (los registros se guardan en `data/backup_history.json`):
```powershell
python src/cli.py history show --limit 100
```

Filtrar historial por operación (backup o restore):
```powershell
python src/cli.py history show --op backup
```

Eliminar una entrada del historial (por `id`):
```powershell
python src/cli.py history delete <record_id>
```


### 6) Configuración

Ver configuración actual (archivo `config/config.toml`):
```powershell
python src/cli.py config show
```

Modificar una clave de la config:
```powershell
python src/cli.py config set postgres host 192.168.1.10
```

Configurar proveedor de nube en `config` (ejemplo AWS):
```powershell
python src/cli.py config cloud --provider aws --bucket mi-bucket --access-key ABC --secret-key XYZ --region us-east-1
```

## Notificaciones (Webhook)

Puedes configurar que la aplicación envíe una notificación POST a una URL (webhook) cada vez que finalice un backup exitoso. El payload es el mismo objeto que se guarda en el historial (`backup_history.json`) y contiene campos como `id`, `operation`, `db_type`, `database`, `file_path`, `hash`, `status`, `message`, `cloud_url`, `timestamp`.

IMPORTANTE: por seguridad la aplicación NO almacena secretos/token en texto claro dentro de `config/config.toml`.
Separa la configuración de la URL del método de autenticación. Los métodos soportados son:

- `none` : no se envía encabezado `Authorization`.
- `env`  : se lee el secreto/token desde una variable de entorno (no se guarda el valor).
- `prompt`: se solicita el secreto/token al usuario en tiempo de ejecución (no se guarda).

Además puede indicar el tipo de token:
- `jwt` : se interpreta el valor como un *secret* para generar un JWT HS256 (se firma y se envía como `Bearer <jwt>`).
- `bearer` : se interpreta el valor como un token ya firmado (se envía tal cual en `Authorization: Bearer <token>`).

Comandos y ejemplos exactos (PowerShell):

- Configurar sólo la URL del webhook (no guarda secretos):
```powershell
python src/cli.py config notify-set --url "https://webhook.example.com/notify"
```

- Configurar método de autenticación: (no se almacena ningún secreto)

  *Usar variable de entorno* (ejemplo: la variable `NOTIFY_SECRET` contendrá el secret o token):
```powershell
python src/cli.py config notify-auth-set --method env --token-type jwt --env-var NOTIFY_SECRET
# Desde PowerShell antes de ejecutar el backup:
$env:NOTIFY_SECRET = 'mi_secret_para_firmar'
python src/cli.py backup run --dbtype postgres --host localhost --user postgres --password '<PASSWORD>' --database postgres --notify-slack
Remove-Item Env:NOTIFY_SECRET
```

  *Pedir el secreto en tiempo de ejecución (prompt)*:
```powershell
python src/cli.py config notify-auth-set --method prompt --token-type bearer
# Al ejecutar el backup se pedirá el token de forma segura (no se mostrará en pantalla):
python src/cli.py backup run --dbtype mysql --host localhost --user root --password '<PASSWORD>' --database mi_db --notify-slack
```

  *Sin autenticación* (no Authorization header):
```powershell
python src/cli.py config notify-auth-set --method none
python src/cli.py config notify-set --url "https://webhook.example.com/notify"
python src/cli.py backup run --dbtype mongo --host localhost --user admin --password '<PASSWORD>' --database Algoritmo --notify-slack
```

Mostrar la configuración de notificaciones (NO mostrará secretos):
```powershell
python src/cli.py config notify-show
python src/cli.py config notify-auth-show
```

Notas de seguridad y buenas prácticas:

- Nunca guardes secretos, tokens ni claves en `config/config.toml`.
- Si usas el método `env`, establece la variable de entorno en el proceso que ejecuta el backup y elimínala inmediatamente después (ejemplo con PowerShell mostrado arriba).
- Si usas `prompt`, el valor nunca se guarda en disco y se solicita cada ejecución.
- `token_type=jwt` asume que el valor es un *secret* y generará un JWT HS256; `token_type=bearer` enviará el valor tal cual.

Estos comandos permiten operar sin escribir secretos en archivos del proyecto.

Opciones de autenticación:
- Sin autenticación: guarda sólo la `url` y no configures `secret`.
- Con autenticación simple: guarda un `secret` que será convertido en un JWT HS256 y enviado en el header `Authorization: Bearer <token>`.

Comandos de ejemplo:

- Guardar la URL (sin secreto):
```powershell
python src/cli.py config notify-set --url https://example.com/hooks/backup
```

- Guardar la URL con secreto (se almacenará en `config/config.toml` como texto; recomendamos usar variables de entorno si prefieres no guardarlo):
```powershell
python src/cli.py config notify-set --url https://example.com/hooks/backup --secret MyWebhookSecret
```

- Ver la configuración actual de notificaciones:
```powershell
python src/cli.py config notify-show
```

Uso recomendado (no almacenar secretos en disco):
- Guarda la URL con `config notify-set` pero deja `secret` vacío.
- Exporta el secreto en la sesión si prefieres no guardarlo en `config`:
```powershell
#$env:NOTIFY_SECRET = 'MyWebhookSecret'
python src/cli.py backup run --dbtype postgres --host localhost --user postgres --password '<PASSWORD>' --database mydb --notify-slack
```

Nota: si configuras el `secret` vía `config notify-set`, el CLI usará ese valor automáticamente; si además defines `NOTIFY_SECRET` en el entorno, el comportamiento actual prioriza el `secret` guardado en `config`.

Ejemplo de payload (JSON) enviado al webhook:
```json
{
  "id": "6f8d3c2a-...",
  "operation": "backup",
  "db_type": "postgres",
  "database": "mydb",
  "file_path": "backups/postgres_mydb_20251203_104438.dump",
  "hash": "<sha256>",
  "status": "success",
  "message": null,
  "cloud_url": null,
  "timestamp": "2025-12-03T10:44:38"
}
```

Comportamiento en el CLI:
- Para enviar la notificación tras el backup añade la opción `--notify-slack` al comando `backup run`.
- Si la URL no está configurada (`config notify-set`), se registrará una advertencia en el log y no se intentará el POST.

Seguridad y recomendaciones:
- Evita almacenar secretos en `config/config.toml` si el repositorio está en control de versiones. Usa variables de entorno o mecanismos secretos del sistema (Azure Key Vault, AWS Secrets Manager, etc.).
- Si necesitas un encabezado o esquema de autenticación distinto (p. ej. `X-Signature`), puedo añadirlo y soportarlo en `config notify-set`.


## Docker: construir imagen de la aplicación

Se proporciona un `Dockerfile` listo para construir una imagen que incluye la aplicación Python y clientes comunes (Postgres, MySQL). Algunos clientes más pesados (p. ej. MongoDB Database Tools o `mssql-tools`) están disponibles como opciones de build—habilítalos explícitamente, ver notas abajo.

Construir imagen básica (clientes comunes incluidos):
```powershell
make build-image
```

Construir imagen "full" incluyendo herramientas opcionales (más pesada):
```powershell
make build-image-full
# o directamente:
docker build --build-arg INSTALL_MONGO=true --build-arg INSTALL_MSSQL=false -t backup_script:full .
```

Pushing a Docker Hub:
```powershell
# Establece tu repo en la variable DOCKERHUB_REPO, por ejemplo:
$env:DOCKERHUB_REPO = 'youruser/backup_script'
make build-image
make push-image
```

Notas importantes sobre binarios y tamaño de imagen:
- El `Dockerfile` instala por defecto `postgresql-client` y `default-mysql-client`, además de utilidades básicas (`curl`, `wget`, `tar`, `zip`).
- Herramientas como `mssql-tools` requieren añadir el repositorio de Microsoft y tienden a aumentar mucho el tamaño de la imagen; por eso están deshabilitadas por defecto. Si las necesitas, habilítalas con `--build-arg INSTALL_MSSQL=true` y sigue las instrucciones del README para añadir los repositorios oficiales (puede requerir pasos adicionales por versión y SO base).
- MongoDB Database Tools (`mongorestore`, `mongosh`) pueden no estar disponibles en la misma forma en todas las distros; la opción `INSTALL_MONGO` intenta instalar un paquete disponible (`mongodb-clients`) pero revisa la salida del build en caso de error.

Optimización y consejos:
- Para entornos de producción donde quieras minimizar la imagen, considera construir dos imágenes separadas: una "builder" que ejecute backups dentro de contenedores que tengan los clientes, y otra "orquestadora" ligera que sólo coordine y llame a esos contenedores. Esto permite mantener imágenes pequeñas y declarar dependencias explícitas.
- Usa `--squash` o una etapa de build multi-stage si necesitas reducir tamaño adicional.
- Revisa y limpia secretos: los valores sensibles deben inyectarse como variables de entorno en tiempo de ejecución o gestionarse mediante un secreto de CI/CD.

*** End Patch
```

2. Si la configuración de nube requiere credenciales específicas, configúralas primero con `config cloud` o editando `config/config.toml`.


---

Si quieres, adapto estos ejemplos a tu estilo (por ejemplo PowerShell vs Bash), añado más ejemplos de `restore` (p.ej. usando `pg_restore` con opciones), o incluyo un ejemplo de `Docker run` para ejecutar un flujo completo dentro del contenedor.
