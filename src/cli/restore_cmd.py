import typer
from pathlib import Path
import shutil
import tempfile
import tarfile
import zipfile
import subprocess
from typing import Optional

from src.utils.hash_utils import calculate_sha256
from src.db_connectors.postgres_connector import PostgresConnector
from src.db_connectors.mysql_connector import MySQLConnector
from src.db_connectors.mongo_connector import MongoConnector


app = typer.Typer(help="Comandos para restauración de bases de datos.")


# -----------------------------
# Detectar tipo de backup
# -----------------------------
def detect_db_type(backup_path: Path) -> str:
    ext = backup_path.suffix.lower()
    if ext in [".sql"]:
        return "postgres"  # pero podría ser mysql; lo sabremos en el restore
    if ext in [".dump", ".backup"]:
        return "postgres"
    if ext in [".bson", ".json"]:
        return "mongo"
    return "unknown"


# -----------------------------
# Descomprimir si es zip o tar.gz
# -----------------------------
def extract_if_needed(backup_path: Path) -> Path:
    if backup_path.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(backup_path, 'r') as z:
            z.extractall(tmp)
        return tmp

    if backup_path.suffix in [".gz", ".tgz"]:
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(backup_path, "r:gz") as t:
            t.extractall(tmp)
        return tmp

    # No comprimido
    return backup_path


# -----------------------------
# Restaurar PostgreSQL
# -----------------------------
def restore_postgres(conn: PostgresConnector, dump_path: Path, db_name: str):
    typer.echo(f" Restaurando PostgreSQL → {db_name} ...")

    if dump_path.is_dir():
        raise ValueError("El archivo de backup de PostgreSQL debe ser un .sql o .dump, no un folder.")

    restore_cmd = [
        "psql",
        f"-h{conn.host}",
        f"-U{conn.user}",
        "-d", db_name,
        "-f", str(dump_path)
    ]

    env = {"PGPASSWORD": conn.password}

    subprocess.run(restore_cmd, check=True, env=env)

    typer.secho("✔ Restauración PostgreSQL completada.", fg=typer.colors.GREEN)


# -----------------------------
# Restaurar MySQL
# -----------------------------
def restore_mysql(conn: MySQLConnector, dump_path: Path, db_name: str):
    typer.echo(f" Restaurando MySQL → {db_name} ...")

    if dump_path.is_dir():
        raise ValueError("El archivo de backup MySQL debe ser .sql, no un folder.")

    restore_cmd = [
        "mysql",
        f"-h{conn.host}",
        f"-u{conn.user}",
        f"-p{conn.password}",
        db_name
    ]

    with dump_path.open("rb") as f:
        subprocess.run(restore_cmd, stdin=f, check=True)

    typer.secho("✔ Restauración MySQL completada.", fg=typer.colors.GREEN)


# -----------------------------
# Restaurar MongoDB
# -----------------------------
def restore_mongo(conn: MongoConnector, dump_path: Path, db_name: str):
    typer.echo(f" Restaurando MongoDB → {db_name} ...")

    if not dump_path.is_dir():
        raise ValueError("Los backups Mongo deben ser una carpeta creada por mongodump.")

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


# -----------------------------
# Comando principal
# -----------------------------
@app.command("restore")
def restore_database(
        backup_file: str = typer.Argument(..., help="Ruta del archivo o carpeta del backup."),
        db: Optional[str] = typer.Option(None, help="Tipo de base de datos (postgres, mysql, mongo)."),
        db_name: str = typer.Option(..., help="Nombre de la base donde restaurar."),
        host: str = typer.Option("localhost", help="Host del servidor."),
        port: Optional[int] = typer.Option(None, help="Puerto del motor."),
        user: str = typer.Option(..., help="Usuario con permisos de restauración."),
        password: str = typer.Option(..., help="Contraseña del usuario."),
        verify_hash: bool = typer.Option(False, help="Verificar integridad con SHA256.")
):
    """
    Restaura una base de datos desde un backup.
    """

    backup_path = Path(backup_file)
    if not backup_path.exists():
        raise typer.BadParameter("El archivo de backup no existe.")

    # Verificación opcional de hash
    if verify_hash:
        typer.echo(" Calculando hash SHA256...")
        file_hash = calculate_sha256(backup_path)
        typer.secho(f" SHA256: {file_hash}", fg=typer.colors.BLUE)

    # Detectar el tipo si no lo dieron
    if not db:
        db = detect_db_type(backup_path)
        typer.echo(f"Tipo detectado automaticamente → {db}")

    # Descomprimir si es necesario
    final_path = extract_if_needed(backup_path)

    # Conectar según motor
    if db == "postgres":
        conn = PostgresConnector(host, port or 5432, user, password)
        restore_postgres(conn, final_path, db_name)

    elif db == "mysql":
        conn = MySQLConnector(host, port or 3306, user, password)
        restore_mysql(conn, final_path, db_name)

    elif db == "mongo":
        conn = MongoConnector(host, port or 27017, user, password)
        restore_mongo(conn, final_path, db_name)

    else:
        raise typer.BadParameter("No se pudo detectar o no reconoce el tipo de base de datos.")

    typer.secho("✔ Base de datos restaurada exitosamente.", fg=typer.colors.GREEN)
