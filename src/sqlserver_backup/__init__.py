'''
import os
import hashlib
import datetime
import platform


def now_timestamp():
    """
    Devuelve un timestamp limpio para nombres de archivos.
    Ejemplo: 2025-11-26_14-30-55
    """
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_dir(path):
    """
    Crea una carpeta si no existe.
    Devuelve True si está lista para usar.
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as ex:
        print(f"[ERROR] No se pudo crear la carpeta: {path}")
        print(f"        {ex}")
        return False


def file_exists(path):
    """Retorna True si el archivo existe."""
    return os.path.isfile(path)


def get_file_hash(path, algorithm="sha256"):
    """
    Calcula hash del archivo para verificar integridad.
    Algoritmos soportados: sha1, sha256, md5
    """
    if not file_exists(path):
        return None

    hash_func = hashlib.new(algorithm)
    
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def is_windows():
    """Retorna True si el sistema operativo es Windows."""
    return platform.system().lower() == "windows"


def is_linux():
    """Retorna True si es Linux."""
    return platform.system().lower() == "linux"


def normalize_path(path):
    """
    Normaliza rutas para evitar errores.
    """
    return os.path.normpath(path)


def safe_join(base, *paths):
    """
    Une rutas de forma segura.
    Similar a os.path.join pero validando que no salgan del directorio base.
    """
    final_path = os.path.abspath(os.path.join(base, *paths))

    if not final_path.startswith(os.path.abspath(base)):
        raise ValueError("Intento de escapar del directorio permitido")

    return final_path

'''

from .core import SQLServerBackup
from src.db_connectors.sqlserver_connector import SQLServerConnector

__all__ = ["SQLServerBackup", "SQLServerConnector", "run_sqlserver_backup"]


def run_sqlserver_backup(
    host: str,
    user: str,
    password: str,
    database: str,
    output_path: str | None = None,
    port: int | None = None
) -> str:
    """
    Función de conveniencia para ejecutar un backup de SQL Server.
    Retorna la ruta del archivo .bak generado.
    """
    connector = SQLServerConnector(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

    backup_engine = SQLServerBackup(connector)
    return backup_engine.full_backup(output_path)
