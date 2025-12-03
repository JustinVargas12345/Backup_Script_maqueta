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

Se incluye un `Dockerfile` ejemplo que instala los clientes más comunes y las dependencias Python. Para construir la imagen:

```bash
make build-image
```

Para ejecutar la CLI dentro del contenedor:

```bash
docker run --rm -it -v $(pwd)/data:/app/data backup_script:local restore --help
```

(Ajusta `-v` para mapear directorios que quieras persistir.)

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
python src/cli.py backup run --dbtype postgres --host "localhost" --port 5432 --user "postgres" --password "Laboratorio1" --database "postgres" --backup-type full
```

MySQL (sin compresión):
```powershell
python src/cli.py backup run --dbtype mysql --host "localhost" --port 3306 --user "root" --password "miPass" --database "mi_db" --backup-type full
```

MongoDB (sin compresión):
```powershell
python src/cli.py backup run --dbtype mongo --host "localhost" --port 27017 --user "admin" --password "Laboratorio1" --database "Algoritmo" --backup-type full
```


### 2) Backup — Ejemplo (con compresión)

Puedes usar la opción `--compress` con valores comunes como `zip`, `tar` o `gz` / `tar.gz` (según tu preferencia y la utilidad `auto_compress` disponible en el proyecto):

Postgres + ZIP:
```powershell
python src/cli.py backup run --dbtype postgres --host "localhost" --port 5432 --user "postgres" --password "Laboratorio1" --database "postgres" --backup-type full --compress zip
```

MySQL + TAR.GZ:
```powershell
python src/cli.py backup run --dbtype mysql --host "localhost" --port 3306 --user "root" --password "miPass" --database "mi_db" --backup-type full --compress tar
```

Mongo + gzip (ejemplo):
```powershell
python src/cli.py backup run --dbtype mongo --host "localhost" --port 27017 --user "admin" --password "Laboratorio1" --database "Algoritmo" --backup-type full --compress gz
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
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password 'Laboratorio1'
```

Restaurar Mongo especificando archivo:
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password 'Laboratorio1' --backup-file "backups\mongo_Algoritmo_20251203_104438.dump"
```

Con verificación de hash:
```powershell
python src/cli.py restore run --dbtype mongo --database Algoritmo --host localhost --port 27017 --user admin --password 'Laboratorio1' --backup-file "backups\mongo_Algoritmo_20251203_104438.dump" --verify-hash
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
$env:PGPASSWORD = 'TuPassword'
python src/cli.py restore run --dbtype postgres --database test_restore_pg --host localhost --port 5432 --user postgres --password 'TuPassword'
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
$env:PGPASSWORD = 'TuPassword'
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
& "C:\Program Files\MongoDB\mongosh\bin\mongosh.exe" --host localhost --port 27017 -u 'admin' -p 'Laboratorio1' --authenticationDatabase 'admin' --eval "use Algoritmo; db.Script.countDocuments();"
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


### 7) Ejemplo completo: backup + comprimir + subir a S3

1. Ejecutar backup comprimido y subir a la nube en un solo comando:
```powershell
python src/cli.py backup run --dbtype postgres --host "localhost" --port 5432 --user "postgres" --password "Laboratorio1" --database "postgres" --backup-type full --compress zip --cloud s3
```

2. Si la configuración de nube requiere credenciales específicas, configúralas primero con `config cloud` o editando `config/config.toml`.


---

Si quieres, adapto estos ejemplos a tu estilo (por ejemplo PowerShell vs Bash), añado más ejemplos de `restore` (p.ej. usando `pg_restore` con opciones), o incluyo un ejemplo de `Docker run` para ejecutar un flujo completo dentro del contenedor.
