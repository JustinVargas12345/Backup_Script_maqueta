import typer
import os
import json
from typing import Optional

from utils.paths import get_backup_filename, get_backup_path, ensure_dir
from utils.compress import auto_compress
from utils.cloud_upload import upload_s3, upload_gcs, upload_azure
from utils.logger import setup_logger
from utils.config_loader import load_config
from db_connectors.postgres_connector import PostgresConnector
from db_connectors.mysql_connector import MySQLConnector
from db_connectors.mongo_connector import MongoConnector

app = typer.Typer(help="Comando para realizar backups de bases de datos.")
logger = setup_logger()


# ------------------------------------------------------------
#  Helper para cargar datos del historial
# ------------------------------------------------------------
HISTORY_FILE = "backup_history.json"


def save_history(entry: dict):
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f, indent=4)

    with open(HISTORY_FILE, "r") as f:
        data = json.load(f)

    data.append(entry)

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ------------------------------------------------------------
#  Main backup function
# ------------------------------------------------------------
@app.command("run")
def run_backup(
    dbtype: str = typer.Option(..., help="Tipo de base de datos: postgres | mysql | mongo"),
    host: str = typer.Option("localhost", help="Host de la base de datos"),
    port: int = typer.Option(None, help="Puerto del motor"),
    user: str = typer.Option(..., help="Usuario de conexión"),
    password: str = typer.Option(..., help="Contraseña de conexión"),
    database: str = typer.Option(..., help="Nombre de la base de datos"),
    outdir: str = typer.Option("backups", help="Directorio donde guardar backups"),
    compress: Optional[str] = typer.Option(None, help="Compresión: zip | tar | gz"),
    cloud: Optional[str] = typer.Option(None, help="Cloud: s3 | gcs | azure"),
    notify_slack: bool = typer.Option(False, help="Enviar notificación a Slack"),
):
    """
    Realiza el backup completo, comprime si lo piden, y lo sube a la nube si se especifica.
    """
    logger.info("Iniciando backup solicitado por CLI...")

    config = load_config()

    # ------------------------------------------------------------
    #  Selección del conector segun DBMS
    # ------------------------------------------------------------
    if dbtype == "postgres":
        connector = PostgresConnector(host, port or 5432, user, password, database)
    elif dbtype == "mysql":
        connector = MySQLConnector(host, port or 3306, user, password, database)
    elif dbtype == "mongo":
        connector = MongoConnector(host, port or 27017, user, password, database)
    else:
        typer.echo("❌ Tipo de base de datos no soportado.")
        raise typer.Exit()

    # ------------------------------------------------------------
    #  Validar conexión
    # ------------------------------------------------------------
    try:
        connector.test_connection()
        logger.info("Conexión validada correctamente.")
    except Exception as e:
        logger.error(f"Error de conexión: {e}")
        typer.echo("❌ No se pudo conectar a la base de datos.")
        raise typer.Exit()

    # ------------------------------------------------------------
    #  Ejecutar backup físico
    # ------------------------------------------------------------
    ensure_dir(outdir)

    backup_filename = get_backup_filename(dbtype, database, "dump")
    backup_path = get_backup_path(outdir, backup_filename)

    try:
        dump_file = connector.create_backup(backup_path)
        logger.info(f"Backup creado: {dump_file}")
    except Exception as e:
        logger.error(f"Error creando el backup: {e}")
        raise typer.Exit()

    final_file = dump_file

    # ------------------------------------------------------------
    #  Compresión opcional
    # ------------------------------------------------------------
    if compress:
        try:
            final_file = auto_compress(dump_file, compress)
            logger.info(f"Archivo comprimido: {final_file}")
        except Exception as e:
            logger.error(f"Error en compresión: {e}")
            raise typer.Exit()

    # ------------------------------------------------------------
    #  Upload opcional a la nube
    # ------------------------------------------------------------
    cloud_url = None

    if cloud:
        logger.info(f"Subiendo a la nube: {cloud}")

        if cloud == "s3":
            creds = config.get("aws", {})
            cloud_url = upload_s3(
                bucket=creds["bucket"],
                key=os.path.basename(final_file),
                filepath=final_file,
                access_key=creds["access_key"],
                secret_key=creds["secret_key"],
                region=creds["region"],
            )

        elif cloud == "gcs":
            creds = config.get("gcs", {})
            cloud_url = upload_gcs(
                bucket_name=creds["bucket"],
                blob_name=os.path.basename(final_file),
                filepath=final_file,
                credentials_path=creds["credentials"],
            )

        elif cloud == "azure":
            creds = config.get("azure", {})
            cloud_url = upload_azure(
                container=creds["container"],
                blob_name=os.path.basename(final_file),
                filepath=final_file,
                connection_string=creds["connection_string"],
            )

        else:
            typer.echo("❌ Cloud no soportado.")
            raise typer.Exit()

        logger.info(f"Archivo subido a la nube: {cloud_url}")

    # ------------------------------------------------------------
    #  Guardar en historial
    # ------------------------------------------------------------
    save_history({
        "dbtype": dbtype,
        "database": database,
        "file": final_file,
        "cloud": cloud_url,
    })

    logger.info("Backup finalizado correctamente.")
    typer.echo(f"🎉 Backup generado exitosamente: {final_file}")

    if cloud_url:
        typer.echo(f"☁️ Subido a: {cloud_url}")

