from pathlib import Path
from typing import Optional, List


class LocalStorage:
    """
    Maneja el almacenamiento local de archivos de backup.
    Permite guardar, listar y borrar archivos dentro de un
    directorio específico del sistema.
    """

    def __init__(self, base_dir: str = "backups"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # Guardar archivo
    # ============================================================

    def save_file(self, src_path: str, dest_name: Optional[str] = None) -> Path:
        """
        Guarda un archivo en el directorio de backups.
        - src_path: archivo generado (ej: backup comprimido)
        - dest_name: nombre final del archivo en la carpeta local
        """
        src = Path(src_path)

        if not src.exists():
            raise FileNotFoundError(f"El archivo '{src_path}' no existe.")

        if dest_name:
            dest = self.base_path / dest_name
        else:
            dest = self.base_path / src.name

        dest.write_bytes(src.read_bytes())
        return dest

    # ============================================================
    # Listar archivos guardados
    # ============================================================

    def list_files(self) -> List[Path]:
        """
        Retorna una lista con todos los archivos guardados en local.
        """
        return [f for f in self.base_path.iterdir() if f.is_file()]

    # ============================================================
    # Borrar archivo
    # ============================================================

    def delete_file(self, file_name: str) -> bool:
        """
        Elimina un archivo del almacenamiento local.
        Retorna True si fue eliminado.
        """
        file_path = self.base_path / file_name

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    # ============================================================
    # Obtener ruta absoluta
    # ============================================================

    def get_path(self, file_name: str) -> Path:
        """
        Retorna la ruta absoluta de un archivo almacenado localmente.
        """
        file_path = self.base_path / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"El archivo '{file_name}' no existe en local storage.")
        return file_path
