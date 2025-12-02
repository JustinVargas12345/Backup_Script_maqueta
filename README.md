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


### 3) Restore — Ejemplos

Nota: el grupo de comandos es `restore` y el comando dentro del grupo también se llama `restore`, por lo que la invocación es `python src/cli.py restore restore <backup_file> ...`.

Restaurar un dump de PostgreSQL (archivo `.dump` o `.sql`):
```powershell
python src/cli.py restore restore backups/postgres_postgres_20251202_154821.dump --db postgres --db-name postgres --host "localhost" --port 5432 --user "postgres" --password "Laboratorio1"
```

Restaurar un backup MySQL (.sql):
```powershell
python src/cli.py restore restore backups/mysql_mysql_20251201_141236.dump.sql --db mysql --db-name mi_db --host "localhost" --port 3306 --user "root" --password "miPass"
```

Restaurar Mongo (backup generado por mongodump):
```powershell
python src/cli.py restore restore backups/mongo_Algoritmo_20251202_143650.dump --db mongo --db-name Algoritmo --host "localhost" --port 27017 --user "admin" --password "Laboratorio1"
```

Puedes añadir `--verify-hash` al comando `restore` para que el programa calcule y muestre el SHA256 del archivo antes de proceder.


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
