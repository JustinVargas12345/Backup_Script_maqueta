import typer
from pathlib import Path
import shutil
import tempfile
import tarfile
import zipfile
import subprocess
from typing import Optional

from utils.hash_utils import calculate_sha256
from utils.logger import setup_logger
from cli.history_cmd import add_history

from db_connectors.postgres_connector import PostgresConnector
from db_connectors.mysql_connector import MySQLConnector
from db_connectors.mongo_connector import MongoConnector


app = typer.Typer(help="Comandos para restauración de bases de datos.")
logger = setup_logger()   # Logs → backup_master_log


# -------------------------------------------------------------
# Detección básica de tipo según extensión
# -------------------------------------------------------------
def detect_db_type(backup_path: Path) -> str:
    ext = backup_path.suffix.lower()

    if ext == ".sql":
        return "sql"  # puede ser postgres o mysql
    if ext in [".dump", ".backup"]:
        return "postgres"
    if ext in [".bson", ".json"]:
        return "mongo"

    return "unknown"


# -------------------------------------------------------------
# Extracción segura de ZIP/TAR para evitar ZIP-SLIP
# -------------------------------------------------------------
def extract_safe(zip_ref, dest):
    for member in zip_ref.namelist():
        extracted = dest / member
        if not extracted.resolve().startswith(dest.resolve()):
            raise Exception("Ataque ZIP-SLIP detectado.")
    zip_ref.extractall(dest)


def extract_if_needed(backup_path: Path) -> Path:
    if backup_path.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(backup_path, "r") as z:
            extract_safe(z, tmp)
        return tmp

    if backup_path.suffix in [".gz", ".tgz"]:
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(backup_path, "r:gz") as t:
            t.extractall(tmp)
        return tmp

    return backup_path


# -------------------------------------------------------------
# PostgreSQL Restore
# Soporta:
#   - .sql → usa psql
#   - .dump (binario) → usa pg_restore
# -------------------------------------------------------------
def restore_postgres(conn: PostgresConnector, dump_path: Path, db_name: str):
    typer.echo(f" Restaurando PostgreSQL → {db_name} ...")

    ext = dump_path.suffix.lower()

    env = {"PGPASSWORD": conn.password}

    if ext == ".sql":
        restore_cmd = [
            "psql",
            f"-h{conn.host}",
            f"-p{conn.port}",
            f"-U{conn.user}",
            "-d", db_name,
            "-f", str(dump_path)
        ]
    else:  # formato binario -F c
        restore_cmd = [
            "pg_restore",
            f"-h{conn.host}",
            f"-p{conn.port}",
            f"-U{conn.user}",
            "-d", db_name,
            str(dump_path)
        ]

    subprocess.run(restore_cmd, check=True, env=env)

    typer.secho("✔ Restauración PostgreSQL completada.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# MySQL Restore
# -------------------------------------------------------------
def restore_mysql(conn: MySQLConnector, dump_path: Path, db_name: str):
    typer.echo(f" Restaurando MySQL → {db_name} ...")

    if dump_path.is_dir():
        raise ValueError("El backup MySQL debe ser archivo .sql, no carpeta.")

    restore_cmd = [
        "mysql",
        f"-h{conn.host}",
        f"-P{conn.port}",
        f"-u{conn.user}",
        f"-p{conn.password}",
        db_name
    ]

    with dump_path.open("rb") as f:
        subprocess.run(restore_cmd, stdin=f, check=True)

    typer.secho("✔ Restauración MySQL completada.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# Mongo Restore (compatible con tu formato de backup)
# Tu backup genera:
#   archivo.dump → archivo con texto:
#       MONGO_DUMP_DIRECTORY:\n<real_directory_path>
# Esto se respeta y se usa correctamente.
# -------------------------------------------------------------
def restore_mongo(conn: MongoConnector, dump_path: Path, db_name: str):
    typer.echo(f" Restaurando MongoDB → {db_name} ...")

    # tu formato especial: archivo que contiene ruta real
    if dump_path.is_file() and dump_path.suffix == ".dump":
        with dump_path.open("r") as f:
            line = f.read().strip()
        if line.startswith("MONGO_DUMP_DIRECTORY:"):
            dir_real = line.split(":", 1)[1].strip()
            dump_path = Path(dir_real)

    if not dump_path.is_dir():
        raise ValueError("El backup Mongo debe ser carpeta generada por mongodump.")

    restore_cmd = [
        "mongorestore",
        f"--host={conn.host}",
        f"--port={conn.port}",
        f"--username={conn.user}",
        f"--password={conn.password}",
        f"--db={db_name}",
        str(dump_path)
    ]

    subprocess.run(restore_cmd, check=True)

    typer.secho("✔ Restauración MongoDB completada.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# Comando principal: restore
# -------------------------------------------------------------
@app.command("restore")
def restore_database(
    backup_file: str = typer.Argument(..., help="Archivo o carpeta del backup."),
    db: Optional[str] = typer.Option(None, help="postgres, mysql o mongo."),
    db_name: str = typer.Option(..., help="Base destino."),
    host: str = typer.Option("localhost", help="Host."),
    port: Optional[int] = typer.Option(None, help="Puerto."),
    user: str = typer.Option(..., help="Usuario."),
    password: str = typer.Option(..., help="Contraseña."),
    verify_hash: bool = typer.Option(False, help="Verificar SHA256.")
):
    """
    Restaura una base de datos desde un archivo de backup.
    """

    backup_path = Path(backup_file)
    if not backup_path.exists():
        raise typer.BadParameter("El archivo de backup no existe.")

    logger.info(f"[RESTORE] Iniciando restauración de {backup_path}")

    # hash opcional
    if verify_hash:
        typer.echo(" Calculando hash SHA256...")
        file_hash = calculate_sha256(backup_path)
        typer.secho(f" SHA256: {file_hash}", fg=typer.colors.BLUE)
        logger.info(f"[RESTORE] SHA256: {file_hash}")

    # autodetección
    if not db:
        db = detect_db_type(backup_path)
        typer.secho(f"Tipo detectado automáticamente → {db}", fg=typer.colors.CYAN)

    # extraer si fue comprimido
    final_path = extract_if_needed(backup_path)

    try:
        if db in ["postgres", "sql"]:
            conn = PostgresConnector(host, port or 5432, user, password, db_name)
            restore_postgres(conn, final_path, db_name)
            real_type = "postgres"

        elif db == "mysql":
            conn = MySQLConnector(host, port or 3306, user, password, db_name)
            restore_mysql(conn, final_path, db_name)
            real_type = "mysql"

        elif db == "mongo":
            conn = MongoConnector(host, port or 27017, user, password, db_name)
            restore_mongo(conn, final_path, db_name)
            real_type = "mongo"

        else:
            raise typer.BadParameter("Tipo de base de datos inválido.")

        typer.secho("✔ Restauración finalizada con éxito.", fg=typer.colors.GREEN)
        logger.info(f"[RESTORE] Restauración correcta en {db_name}")

        add_history(
            operation="restore",
            db_type=real_type,
            database_name=db_name,
            file_path=str(backup_path),
            status="success",
            message="Restauración completada sin errores."
        )

    except Exception as e:
        logger.error(f"[RESTORE ERROR] {e}")

        add_history(
            operation="restore",
            db_type=db or "unknown",
            database_name=db_name,
            file_path=str(backup_path),
            status="error",
            message=str(e)
        )

        raise typer.Exit(code=1)

    finally:
        # limpieza temporal
        if final_path != backup_path and final_path.is_dir():
            shutil.rmtree(final_path, ignore_errors=True)
            logger.info("[RESTORE] Carpeta temporal eliminada")
