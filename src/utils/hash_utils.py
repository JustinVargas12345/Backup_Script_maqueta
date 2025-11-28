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
        FileNotFoundError: Si el archivo no existe o no es un archivo válido.
        ValueError: Si file_path es una carpeta.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"El archivo no existe: {file_path}")

    if not path.is_file():
        raise ValueError(f"No se puede calcular hash de una carpeta: {file_path}")

    sha256 = hashlib.sha256()

    # Leer en chunks de forma eficiente
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):  # 1MB por chunk
            sha256.update(chunk)

    return sha256.hexdigest()
