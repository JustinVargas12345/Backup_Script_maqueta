# src/utils/backup_verifier.py
import shutil
import os
from pathlib import Path
from typing import Tuple, Optional
from .hash_utils import calculate_sha256


class BackupVerifier:
    """
    Verifica integridad y condiciones de un backup:
    - calcula SHA256
    - comprueba espacio libre >= tamaño mínimo requerido (en bytes)
    """

    @staticmethod
    def file_sha256(path: str) -> str:
        return calculate_sha256(path)

    @staticmethod
    def has_enough_disk_space(path: str, required_bytes: int) -> bool:
        """
        Comprueba si la partición que contiene 'path' tiene al menos required_bytes libres.
        """
        p = Path(path)
        if not p.exists():
            p = p.parent
        usage = shutil.disk_usage(str(p))
        free = usage.free
        return free >= required_bytes

    @staticmethod
    def get_file_size(path: str) -> int:
        p = Path(path)
        return p.stat().st_size

    @staticmethod
    def is_valid_backup_file(path: str) -> bool:
        """
        Chequeos simples: existe y es archivo o (para mongodump) carpeta.
        """
        p = Path(path)
        return p.exists() and (p.is_file() or p.is_dir())

    @staticmethod
    def verify_hash(path: str, expected_hash: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Calcula sha256 y lo compara con expected_hash (si se provee).
        Retorna (ok, calculated_hash)
        """
        calculated = calculate_sha256(path)
        if expected_hash is None:
            return True, calculated
        return (calculated == expected_hash, calculated)
