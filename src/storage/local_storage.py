from pathlib import Path
from typing import Optional, List
import shutil


class LocalStorage:
    """
    Maneja el almacenamiento local de archivos de backup.
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
        """
        src = Path(src_path)

        if not src.exists():
            raise FileNotFoundError(f"El archivo '{src_path}' no existe.")

        dest = self.base_path / (dest_name if dest_name else src.name)

        # Copia segura sin cargar todo el archivo en memoria
        shutil.copy2(src, dest)

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
