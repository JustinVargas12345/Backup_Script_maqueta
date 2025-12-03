
from pathlib import Path
from datetime import datetime
import logging

from db_connectors.sqlserver_connector import SQLServerConnector  

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
    def _generate_backup_filename(self, database, suffix="full", extension="bak"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{database}_{suffix}_{timestamp}.{extension}"

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
    # Ejecutar el backup según el tipo
    # ---------------------------------------------------------
    def execute_backup(self, backup_type: str, output_path: str | None = None):
        """
        Ejecuta el tipo de backup especificado (full, differential, log).
        """
        if backup_type == "full":
            return self.full_backup(output_path)
        elif backup_type == "diff":
            return self.differential_backup(output_path)
        elif backup_type == "log":
            return self.log_backup(output_path)
        else:
            raise ValueError(f"Tipo de backup no válido: {backup_type}")

    # ---------------------------------------------------------
    # Backup FULL
    # ---------------------------------------------------------
    def full_backup(self, output_path: str | None = None):
        """
        Realiza un backup FULL de la base de datos usando el conector.
        Retorna la ruta completa del archivo generado.
        """
        folder = self._resolve_output_path(output_path)
        filename = self._generate_backup_filename(self.connector.database, suffix="full", extension="bak")
        final_path = folder / filename

        output_file = self.connector.create_backup(str(final_path))

        if not Path(output_file).exists(): 
            self._log(f"Backup FULL falló, archivo no encontrado: {output_file}", level="error")
            raise RuntimeError(f"SQLServerBackup: Backup FULL finalizado, pero el archivo no existe: {output_file}")

        self._log(f"Backup FULL completado | Archivo: {output_file}")
        return output_file

    # ---------------------------------------------------------
    # Backup DIFFERENTIAL
    # ---------------------------------------------------------
    def differential_backup(self, output_path: str | None = None):
        """
        Realiza un backup diferencial: solo crea backup de cambios desde último FULL.
        """
        folder = self._resolve_output_path(output_path)
        filename = self._generate_backup_filename(self.connector.database, suffix="diff", extension="bak")
        final_path = folder / filename

        output_file = self.connector.create_backup(
            str(final_path),
            backup_type="DIFFERENTIAL"
        )

        if not Path(output_file).exists():
            self._log(f"Backup diferencial falló, archivo no encontrado: {output_file}", level="error")
            raise RuntimeError(f"SQLServerBackup: Backup diferencial finalizado, pero el archivo no existe: {output_file}")

        self._log(f"Backup DIFERENCIAL completado | Archivo: {output_file}")
        return output_file

    # ---------------------------------------------------------
    # Backup LOG
    # ---------------------------------------------------------
    def log_backup(self, output_path: str | None = None):
        """
        Realiza backup de log, creando archivo .trn.
        Requiere: modo de recuperación FULL o BULK-LOGGED.
        """
        folder = self._resolve_output_path(output_path)
        filename = self._generate_backup_filename(self.connector.database, suffix="log", extension="trn")
        final_path = folder / filename

        output_file = self.connector.create_backup(
            str(final_path),
            backup_type="LOG"
        )

        if not Path(output_file).exists():
            self._log(f"Backup LOG falló, archivo no encontrado: {output_file}", level="error")
            raise RuntimeError(f"SQLServerBackup: Backup de LOG finalizado, pero el archivo no existe: {output_file}")

        self._log(f"Backup LOG completado | Archivo: {output_file}")
        return output_file
   

    # ---------------------------------------------------------
    # Logging interno
    # ---------------------------------------------------------
    def _log(self, message: str, level="info"):
        if level == "error":
            logging.error(message)
        else:
            logging.info(message)


# ---------------------------------------------------------
# Configuración de logging central (global)
# ---------------------------------------------------------
LOG_FILE = "backup_master_log.txt"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
