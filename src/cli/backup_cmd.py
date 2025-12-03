
import typer
import os
from typing import Optional
from pathlib import Path
import subprocess

from utils.paths import get_backup_filename, get_backup_path, ensure_dir
from utils.compress import auto_compress
from utils.cloud_upload import upload_s3, upload_gcs, upload_azure
from utils.logger import setup_logger
from utils.config_loader import load_config
from utils.notify import send_notification
import getpass
from sqlserver_backup.__init__ import run_sqlserver_backup  # Importamos la función específica para SQL Server
from utils.history_manager import HistoryManager

from db_connectors.postgres_connector import PostgresConnector
from db_connectors.mysql_connector import MySQLConnector
from db_connectors.mongo_connector import MongoConnector
from db_connectors.sqlserver_connector import SQLServerConnector
from utils.bin_checker import check_binaries, suggest_install_instructions, REQUIRED_BINARIES_BY_OP

app = typer.Typer(help="Comando para realizar backups de bases de datos.")
logger = setup_logger()  # asume que setup_logger configura backup_master_log

HISTORY_FILE = "backup_history.json"
history = HistoryManager(HISTORY_FILE)


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
        # Usar el método del conector que ya registra detalles en `backup_master_log`
        return connector.validate_connection()
    except Exception as e:
        logger.error(f"MySQL validation error: {e}")
        try:
            # Intentar también escribir en el log del conector para visibilidad
            connector.log(f"_validate_mysql: excepción durante validación: {e}")
        except Exception as log_e:
            logger.debug(f"_validate_mysql: no se pudo escribir en el log del conector: {log_e}")
        return False


def _validate_mongo(connector: MongoConnector) -> bool:
    try:
        # Use a list of args to avoid shell=True and injection; pass host and port separately
        cmd = [
            "mongosh",
            "--quiet",
            "--host",
            str(connector.host),
            "--port",
            str(connector.port),
            "--eval",
            "db.runCommand({ping:1})",
        ]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    skip_binary_check: bool = typer.Option(False, help="Omitir verificación de binarios en el PATH."),
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
    connector = ConnectorClass(host, port, user, password, database, )

    # Verificar binarios necesarios (por defecto) a menos que se solicite omitir
    if not skip_binary_check:
        required = REQUIRED_BINARIES_BY_OP.get("backup", {}).get(dbtype, [])
        if required:
            res = check_binaries(required)
            missing = [k for k, v in res.items() if not v]
            if missing:
                typer.secho("⚠ Faltan binarios requeridos para este motor:", fg=typer.colors.YELLOW)
                for m in missing:
                    typer.echo(f" - {m}")
                typer.secho("Ejecuta `python src/cli.py utils check-binaries` para ver sugerencias.", fg=typer.colors.CYAN)
                typer.secho("Continuando de todos modos; la operación puede fallar si faltan binarios.", fg=typer.colors.YELLOW)
                logger.warning(f"Faltan binarios: {missing} - continuando a petición del usuario.")

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
        history.add_entry(
            operation="backup",
            db_type=dbtype,
            database=database,
            file_path=None,
            hash=None,
            status="error",
            message=str(e),
            cloud_url=None,
        )
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
            history.add_entry(
                operation="backup",
                db_type=dbtype,
                database=database,
                file_path=str(produced) if produced is not None else None,
                hash=None,
                status="error",
                message=f"compress error: {e}",
                cloud_url=None,
            )
            raise typer.Exit(code=1)

    # upload a la nube (opcional)
    cloud_url = None
    if cloud:
        cloud_url = upload_to_cloud(cloud, final_file, config)
        if not cloud_url:
            typer.secho("⚠️ No se pudo subir el archivo a la nube.", fg=typer.colors.YELLOW)
            logger.warning("upload_to_cloud devolvió None")

    # Guardar historial de éxito
    entry = history.add_entry(
        operation="backup",
        db_type=dbtype,
        database=database,
        file_path=str(final_file),
        hash=None,
        status="success",
        message=None,
        cloud_url=cloud_url,
    )

    # Notificación opcional (configurada vía `config notify-set`)
    try:
        if notify_slack:
            notify_cfg = config.get("notify", {})
            notify_url = notify_cfg.get("url")
            auth_cfg = notify_cfg.get("auth", {})
            if notify_url:
                # Determine how to obtain token/secret at runtime (no secrets are read from config)
                method = auth_cfg.get("method", "none")
                token_type = auth_cfg.get("token_type", "jwt")
                env_var = auth_cfg.get("env_var")

                token_value = None
                if method == "env":
                    if not env_var:
                        logger.warning("notify auth method=env pero no se configuró env_var; omitiendo auth.")
                    else:
                        token_value = os.environ.get(env_var)
                        if token_value is None:
                            logger.warning(f"Variable de entorno {env_var} no encontrada; omitiendo auth.")
                elif method == "prompt":
                    # Prompt the user securely for the secret/token (not echoed)
                    prompt_text = "Secreto/token para notificación: "
                    token_value = getpass.getpass(prompt_text)
                elif method == "none":
                    token_value = None
                else:
                    logger.warning(f"Método de auth desconocido: {method}; omitiendo auth.")

                # Send notification: if token_type == 'jwt' we pass it as secret (make_jwt will create JWT);
                # if token_type == 'bearer' we pass it as auth_token (already-signed bearer token)
                ok = False
                status_code = 0
                text = ""
                if token_value:
                    if token_type == "jwt":
                        ok, status_code, text = send_notification(notify_url, entry, secret=token_value)
                    else:
                        ok, status_code, text = send_notification(notify_url, entry, auth_token=token_value)
                else:
                    # No token provided — attempt without Authorization
                    ok, status_code, text = send_notification(notify_url, entry)

                if ok:
                    logger.info(f"Notificación enviada correctamente a {notify_url} (HTTP {status_code})")
                else:
                    logger.warning(f"Notificación fallida a {notify_url} (HTTP {status_code}): {text}")
            else:
                logger.warning("notify_slack activo pero no hay URL configurada (usar `config notify-set`).")
    except Exception as e:
        logger.exception(f"Error durante envío de notificación: {e}")

    typer.secho(f"🎉 Backup finalizado: {final_file}", fg=typer.colors.GREEN)
    if cloud_url:
        typer.secho(f"☁️ Subido a: {cloud_url}", fg=typer.colors.CYAN)

    logger.info("=== Backup finalizado correctamente ===")
