import os
from pathlib import Path
from datetime import datetime

from src.db_connectors.sqlserver_connector import SQLServerConnector  # Tu conector completo

class SQLServerBackup:
    """
    Manejador principal de backups para SQL Server.
    Requiere un objeto SQLServerConnector.
    """

    def __init__(self, connector: SQLServerConnector):
        self.connector = connector

    # ---------------------------------------------------------
    # Construir nombre de archivo
    # ---------------------------------------------------------
    def _generate_backup_filename(self, database, suffix="full"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{database}_{suffix}_{timestamp}.bak"

    # ---------------------------------------------------------
    # Determinar carpeta destino
    # ---------------------------------------------------------
    def _resolve_output_path(self, output_path: str | None):
        """
        Si output_path es None → usar carpeta oficial de SQL Server.
        """
        if output_path:
            folder = Path(output_path)
            folder.mkdir(parents=True, exist_ok=True)
            return folder

        backup_dir = self.connector.get_backup_directory()
        if not backup_dir:
            raise RuntimeError(
                "No se pudo detectar la carpeta oficial de backup de SQL Server "
                "y no se especificó output_path."
            )
        return Path(backup_dir)

    # ---------------------------------------------------------
    # Backup FULL
    # ---------------------------------------------------------
    def full_backup(self, output_path: str | None = None):
        """
        Realiza un backup FULL de la base de datos usando el conector.
        Retorna la ruta completa del archivo generado.
        """
        folder = self._resolve_output_path(output_path)
        filename = self._generate_backup_filename(self.connector.database, suffix="full")
        final_path = folder / filename

        output_file = self.connector.create_backup(str(final_path))

        if not Path(output_file).exists():
            raise RuntimeError(f"SQLServerBackup: Backup finalizado, pero el archivo no existe: {output_file}")

        return output_file

    # ---------------------------------------------------------
    # Backup DIFERENCIAL (pendiente)
    # ---------------------------------------------------------
    def differential_backup(self, output_path: str | None = None):
        raise NotImplementedError("Backup diferencial pendiente de implementación.")

    # ---------------------------------------------------------
    # Backup de LOGS (pendiente)
    # ---------------------------------------------------------
    def log_backup(self, output_path: str | None = None):
        raise NotImplementedError("Backup de logs pendiente de implementación.")
