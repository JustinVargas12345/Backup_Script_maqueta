
import typer
import os
import json
from typing import Optional
from pathlib import Path
import subprocess

from utils.paths import get_backup_filename, get_backup_path, ensure_dir
from utils.compress import compress_file as util_compress, auto_compress
from utils.cloud_upload import upload_s3, upload_gcs, upload_azure
from utils.logger import setup_logger
from utils.config_loader import load_config
from sqlserver_backup.__init__ import run_sqlserver_backup  # Importamos la función específica para SQL Server

from db_connectors.postgres_connector import PostgresConnector
from db_connectors.mysql_connector import MySQLConnector
from db_connectors.mongo_connector import MongoConnector
from db_connectors.sqlserver_connector import SQLServerConnector

app = typer.Typer(help="Comando para realizar backups de bases de datos.")
logger = setup_logger()  # asume que setup_logger configura backup_master_log

HISTORY_FILE = "backup_history.json"


# -------------------------
# Historial simple (JSON)
# -------------------------
def save_history(entry: dict):
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = []

    data.append(entry)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# -------------------------
# Validación de conexión
# -------------------------
def _validate_sqlserver(connector: SQLServerConnector) -> bool:
    try:
        return bool(connector.connection_test())
    except Exception as e:
        logger.error(f"SQLServer validation error: {e}")
        return False


def _validate_postgres(connector: PostgresConnector) -> bool:
    try:
        # Usamos pg_dump para validar la conexión
        return connector.validate_connection()
    except Exception as e:
        logger.error(f"Postgres validation error: {e}")
        return False


def _validate_mysql(connector: MySQLConnector) -> bool:
    try:
        cmd = f'mysqladmin ping -h {connector.host} -u {connector.user} -p{connector.password}'
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return b"mysqld is alive" in r.stdout
    except FileNotFoundError:
        logger.warning("mysqladmin no está disponible en el PATH.")
        return False
    except Exception as e:
        logger.error(f"MySQL validation error: {e}")
        return False


def _validate_mongo(connector: MongoConnector) -> bool:
    try:
        cmd = f'mongosh --quiet --host {connector.host}:{connector.port} --eval "db.runCommand({{ping:1}})"'
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return b'"ok"' in r.stdout.lower() or b'ok' in r.stdout.lower()
    except FileNotFoundError:
        logger.warning("mongosh no está disponible en el PATH.")
        return False
    except Exception as e:
        logger.error(f"Mongo validation error: {e}")
        return False


def validate_connection(dbtype: str, connector) -> bool:
    logger.info(f"Validando conexión para '{dbtype}'")
    if dbtype == "sqlserver":
        return _validate_sqlserver(connector)
    if dbtype == "postgres":
        return _validate_postgres(connector)
    if dbtype == "mysql":
        return _validate_mysql(connector)
    if dbtype == "mongo":
        return _validate_mongo(connector)
    logger.error(f"validate_connection: motor no soportado: {dbtype}")
    return False


def execute_backup(dbtype: str, connector, backup_path: str, backup_type="full") -> str:
    logger.info(f"execute_backup -> dbtype={dbtype} path={backup_path} type={backup_type}")

    # ---------------------
    # SQL SERVER
    # ---------------------
    if dbtype == "sqlserver":
        try:
            # Usamos la función específica para SQL Server y pasamos el backup_type
            produced = run_sqlserver_backup(
                host=connector.host,
                user=connector.user,
                password=connector.password,
                database=connector.database,
                output_path=None,
                backup_type=backup_type  # Asegúrate de pasar el tipo de backup
            )
            return produced
        except Exception as e:
            logger.error(f"Error en backup de SQL Server: {e}")
            raise

    # ---------------------
    # PostgreSQL, MySQL, Mongo
    # ---------------------
    elif dbtype in ("postgres", "mysql", "mongo"):
        connector.dump_database(backup_path)
        return backup_path

    else:
        raise RuntimeError(f"Motor no soportado: {dbtype}")


# -------------------------
# Subida a la nube (wrapper)
# -------------------------
def upload_to_cloud(cloud_provider: str, final_file: str, config: dict) -> Optional[str]:
    logger.info(f"upload_to_cloud -> provider={cloud_provider} file={final_file}")
    try:
        if cloud_provider == "s3":
            creds = config.get("aws", {})
            return upload_s3(
                bucket=creds.get("bucket"),
                key=os.path.basename(final_file),
                filepath=str(final_file),
                access_key=creds.get("access_key"),
                secret_key=creds.get("secret_key"),
                region=creds.get("region"),
            )
        if cloud_provider == "gcs":
            creds = config.get("gcs", {})
            return upload_gcs(
                bucket_name=creds.get("bucket"),
                blob_name=os.path.basename(final_file),
                filepath=str(final_file),
                credentials_path=creds.get("credentials"),
            )
        if cloud_provider == "azure":
            creds = config.get("azure", {})
            return upload_azure(
                container=creds.get("container"),
                blob_name=os.path.basename(final_file),
                filepath=str(final_file),
                connection_string=creds.get("connection_string"),
            )
        raise RuntimeError("Proveedor de nube no soportado.")
    except Exception as e:
        logger.error(f"Error subiendo a la nube: {e}")
        return None


# -------------------------
# Comando principal
# -------------------------
@app.command("run")
def run_backup(
    dbtype: str = typer.Option(..., help="postgres | mysql | mongo | sqlserver"),
    host: str = typer.Option("localhost"),
    port: Optional[int] = typer.Option(None),
    user: str = typer.Option(...),
    password: str = typer.Option(...),
    database: str = typer.Option(...),
    outdir: str = typer.Option("backups"),
    compress: Optional[str] = typer.Option(None, help="zip | tar | gz"),
    cloud: Optional[str] = typer.Option(None, help="s3 | gcs | azure"),
    notify_slack: bool = typer.Option(False),
    backup_type: str = typer.Option("full", help="Tipo de backup: full, diff, log", show_default=True),  # <-- Añadimos esta opción
):
    logger.info("=== Iniciando backup desde CLI ===")
    config = load_config()

    # mapear conectores
    connectors_map = {
        "postgres": PostgresConnector,
        "mysql": MySQLConnector,
        "mongo": MongoConnector,
        "sqlserver": SQLServerConnector,
    }

    if dbtype not in connectors_map:
        typer.secho("❌ Motor no soportado.", fg=typer.colors.RED)
        logger.error(f"Motor no soportado: {dbtype}")
        raise typer.Exit(code=1)

    # crear instancia del conector
    ConnectorClass = connectors_map[dbtype]
    connector = ConnectorClass(host, port, user, password, database)

    # validar conexion
    if not validate_connection(dbtype, connector):
        typer.secho("❌ No se pudo validar la conexión.", fg=typer.colors.RED)
        logger.error("validate_connection returned False")
        raise typer.Exit(code=1)

    typer.secho("✅ Conexión validada correctamente.", fg=typer.colors.GREEN)
    logger.info("Conexión validada correctamente.")

    ensure_dir(Path(outdir))

    # generar ruta de backup
    if dbtype == "sqlserver":
        backup_path = outdir   # solo la carpeta, NO el archivo
    else:
        backup_filename = get_backup_filename(dbtype, database, "dump")
        backup_path = get_backup_path(outdir, backup_filename)

    # ejecutar backup
    try:
        produced = execute_backup(dbtype, connector, str(backup_path), backup_type=backup_type)  # <-- Aquí pasamos el tipo de backup
        logger.info(f"Backup producido en: {produced}")
    except Exception as e:
        logger.exception(f"Fallo en la generación del backup: {e}")
        typer.secho(f"❌ Error creando backup: {e}", fg=typer.colors.RED)
        save_history({
            "dbtype": dbtype,
            "database": database,
            "file": None,
            "cloud": None,
            "status": "error",
            "message": str(e)
        })
        raise typer.Exit(code=1)

    final_file = produced

    # compresión opcional
    if compress:
        try:
            compressed = auto_compress(final_file, compress)
            if isinstance(compressed, (list, tuple)):
                final_file = compressed[0]
            else:
                final_file = compressed
            logger.info(f"Archivo comprimido: {final_file}")
        except Exception as e:
            logger.exception(f"Error en compresión: {e}")
            typer.secho(f"❌ Error al comprimir: {e}", fg=typer.colors.RED)
            save_history({
                "dbtype": dbtype,
                "database": database,
                "file": str(produced),
                "cloud": None,
                "status": "error",
                "message": f"compress error: {e}"
            })
            raise typer.Exit(code=1)

    # upload a la nube (opcional)
    cloud_url = None
    if cloud:
        cloud_url = upload_to_cloud(cloud, final_file, config)
        if not cloud_url:
            typer.secho("⚠️ No se pudo subir el archivo a la nube.", fg=typer.colors.YELLOW)
            logger.warning("upload_to_cloud devolvió None")

    # Guardar historial de éxito
    save_history({
        "dbtype": dbtype,
        "database": database,
        "file": str(final_file),
        "cloud": cloud_url,
        "status": "success",
        "message": None
    })

    typer.secho(f"🎉 Backup finalizado: {final_file}", fg=typer.colors.GREEN)
    if cloud_url:
        typer.secho(f"☁️ Subido a: {cloud_url}", fg=typer.colors.CYAN)

    logger.info("=== Backup finalizado correctamente ===")
