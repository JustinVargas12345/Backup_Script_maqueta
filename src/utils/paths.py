import os
from pathlib import Path


def ensure_dir(path: str):
    """
    Crea un directorio si no existe.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_backup_filename(dbtype: str, dbname: str, extension: str):
    """
    Genera nombres de archivo de backup.
    """
    from .timestamps import timestamp_now

    ts = timestamp_now()
    return f"{dbtype}_{dbname}_{ts}.{extension}"


def get_backup_path(base_dir: str, filename: str):
    """
    Construye rutas absolutas.
    """
    ensure_dir(base_dir)
    return os.path.join(base_dir, filename)
