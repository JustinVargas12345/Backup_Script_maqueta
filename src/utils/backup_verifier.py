import shutil
import os
from pathlib import Path
from typing import Tuple, Optional, Union
from .hash_utils import calculate_sha256




class BackupVerifier:
    """
    Verifica integridad y condiciones de un backup:
    - calcula SHA256 (archivo o carpeta)
    - comprueba espacio libre >= tamaño mínimo requerido (en bytes)
    """

    @staticmethod
    def file_sha256(path: str) -> str:
        """
        Calcula SHA256 para archivo o carpeta.
        """
        p = Path(path)
        if p.is_file():
            return calculate_sha256(path)
        elif p.is_dir():
            return BackupVerifier._folder_sha256(p)
        else:
            raise FileNotFoundError(f"No existe el archivo o carpeta: {path}")

    @staticmethod
    def _folder_sha256(folder: Path) -> str:
        """
        Hash determinístico de una carpeta:
        - ordena archivos alfabéticamente
        - concatena hashes individuales + tamaños + paths relativos
        """
        import hashlib

        sha = hashlib.sha256()

        for file in sorted(folder.rglob("*")):
            if file.is_file():
                relative = str(file.relative_to(folder)).encode()
                sha.update(relative)
                size = file.stat().st_size
                sha.update(str(size).encode())

                with open(file, "rb") as f:
                    while chunk := f.read(1024 * 1024):
                        sha.update(chunk)

        return sha.hexdigest()

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
        """
        Obtiene tamaño real:
        - archivo → st_size
        - carpeta → suma recursiva
        """
        p = Path(path)

        if p.is_file():
            return p.stat().st_size

        if p.is_dir():
            total = 0
            for f in p.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total

        raise FileNotFoundError(f"No existe archivo o carpeta: {path}")

    @staticmethod
    def is_valid_backup_file(path: str) -> bool:
        """
        Chequeos simples: existe y es archivo o carpeta.
        """
        p = Path(path)
        return p.exists() and (p.is_file() or p.is_dir())

    @staticmethod
    def verify_hash(path: str, expected_hash: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Calcula sha256 y lo compara con expected_hash (si se provee).
        Retorna (ok, calculated_hash)
        """
        calculated = BackupVerifier.file_sha256(path)
        if expected_hash is None:
            return True, calculated
        return calculated == expected_hash, calculated
