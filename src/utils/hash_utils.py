import hashlib
from pathlib import Path

def calculate_sha256(file_path: str) -> str:
    """
    Calcula el hash SHA-256 de un archivo.

    Args:
        file_path (str): Ruta del archivo a calcular.

    Returns:
        str: Hash SHA-256 en formato hexadecimal.

    Raises:
        FileNotFoundError: Si el archivo no existe.
    """

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"El archivo no existe: {file_path}")

    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()
