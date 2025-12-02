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
from utils.history_manager import HistoryManager

# helper local para registrar en el historial (usa el mismo archivo que el BackupManager)
def add_history(operation: str, db_type: str, database_name: str, file_path: str, status: str, message: str = None, file_hash: str = None, cloud_url: str = None):
    hm = HistoryManager("data/backup_history.json")
    try:
        hm.add_entry(
            operation=operation,
            db_type=db_type,
            database=database_name,
            file_path=file_path,
            hash=file_hash,
            status=status,
            message=message,
            cloud_url=cloud_url,
        )
    except Exception:
        # no bloquear la restauración por fallos en el log de historial
        logger.exception("Error registrando el historial")

from db_connectors.postgres_connector import PostgresConnector
from db_connectors.mysql_connector import MySQLConnector
from db_connectors.mongo_connector import MongoConnector
from utils.bin_checker import check_binaries, suggest_install_instructions, REQUIRED_BINARIES_BY_OP


app = typer.Typer(help="Comandos para restauración de bases de datos.")
logger = setup_logger()   # Logs → backup_master_log



def find_restore_target(folder: Path) -> Path:
    """
    Busca dentro de una carpeta el archivo restaurable real (.sql, .dump, .bson, .json).
    Prioriza:
    1. .dump
    2. .sql
    3. .bson / .json (mongo)
    """
    candidates = []

    for path in folder.rglob("*"):
        if path.suffix.lower() in [".dump", ".sql", ".bson", ".json"]:
            candidates.append(path)

    if not candidates:
        raise Exception("No se encontró ningún archivo restaurable dentro del comprimido.")

    # prioridad especial
    for ext in [".dump", ".sql", ".bson", ".json"]:
        for c in candidates:
            if c.suffix.lower() == ext:
                return c

    return candidates[0]










# -------------------------------------------------------------
# Detección básica de tipo según extensión
# -------------------------------------------------------------
def detect_db_type(path: Path) -> str:
    ext = path.suffix.lower()

    # detecto si está dentro de zip/tar
    if ext in [".zip", ".gz", ".tgz", ".tar"]:
        # asumimos SQL por default
        return "sql"

    if ext == ".sql":
        return "sql"

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


def extract_if_needed(backup_path: Path) -> tuple:
    """
    Si `backup_path` es un comprimido, lo extrae en un tmp dir y devuelve
    (ruta_real_para_restaurar, tmp_dir). Si no, devuelve (backup_path, None).
    """
    if backup_path.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(backup_path, "r") as z:
            extract_safe(z, tmp)
        return find_restore_target(tmp), tmp

    if backup_path.suffix in [".gz", ".tgz"]:
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(backup_path, "r:gz") as t:
            t.extractall(tmp)
        return find_restore_target(tmp), tmp

    if backup_path.suffix == ".tar":
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(backup_path, "r") as t:
            t.extractall(tmp)
        return find_restore_target(tmp), tmp

    return backup_path, None



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
    final_path, _temp_dir = extract_if_needed(backup_path)

    # Verificar binarios necesarios (para el tipo detectado) - no obligatorio
    required = REQUIRED_BINARIES_BY_OP.get("restore", {}).get(db, [])
    if required:
        res = check_binaries(required)
        missing = [k for k, v in res.items() if not v]
        if missing:
            typer.secho("⚠ Faltan binarios requeridos para el tipo de DB detectado:", fg=typer.colors.YELLOW)
            for m in missing:
                typer.echo(f" - {m}")
            typer.secho("Ejecuta `python src/cli.py utils check-binaries` para ver sugerencias.", fg=typer.colors.CYAN)
            typer.secho("Continuando de todos modos; la restauración puede fallar si faltan binarios.", fg=typer.colors.YELLOW)
            logger.warning(f"Faltan binarios para restore: {missing} - continuando a petición del usuario.")

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
            message="Restauración completada sin errores.",
            file_hash=locals().get("file_hash", None),
        )

    except Exception as e:
        logger.error(f"[RESTORE ERROR] {e}")

        add_history(
            operation="restore",
            db_type=db or "unknown",
            database_name=db_name,
            file_path=str(backup_path),
            status="error",
                message=str(e),
                file_hash=locals().get("file_hash", None),
        )

        raise typer.Exit(code=1)

    finally:
        # limpieza temporal: si extrajimos en un tmp, borrarlo
        if _temp_dir is not None:
            try:
                shutil.rmtree(_temp_dir, ignore_errors=True)
                logger.info("[RESTORE] Carpeta temporal eliminada")
            except Exception:
                logger.exception("No se pudo eliminar carpeta temporal")
