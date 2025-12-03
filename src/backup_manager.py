# src/backup_manager.py
import datetime
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from src.utils.history_manager import HistoryManager
from src.utils.backup_verifier import BackupVerifier
from src.utils.db_selector import DatabaseSelector
from src.utils import compress

from src.storage.local_storage import LocalStorage
from src.storage.cloud_storage_impl import CloudStorage
from src.utils.logger import setup_logger


logger = setup_logger()

# Módulo SQL Server (nuevo import limpio)
from src.sqlserver_backup import run_sqlserver_backup, run_sqlserver_backup_test, get_sqlserver_backup_dir


class BackupManager:
    """
    Clase principal para manejar backups de múltiples bases de datos.
    Este manager orquesta:
        - Selección del conector
        - Generación del backup
        - Compresión
        - Guardado local
        - Subida a la nube (opcional)
        - Registro en historial
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Local backup path
        self.local = LocalStorage(self.config.get("local_backup_path", "backups"))

        # Cloud provider (si existe)
        cloud_cfg = self.config.get("cloud", {})
        self.cloud = CloudStorage(cloud_cfg.get("provider", ""), cloud_cfg) if cloud_cfg.get("provider") else None

        # Historial
        self.history = HistoryManager(self.config.get("history_file", "data/backup_history.json"))

        # Verificador de hash
        self.verifier = BackupVerifier()

        # Días de retención (pendiente implementar)
        self.retention_days = self.config.get("retention_days", 7)

    # ==========================================================
    #  MÉTODO PRINCIPAL DE BACKUP
    # ==========================================================
    def create_backup(
        self,
        db_type: str,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        compression: Optional[str] = None,
        upload_to_cloud: bool = False,
    ):
        """
        Realiza un backup de MySQL, PostgreSQL, MongoDB o SQL Server.
        """

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # ==========================================================
        #  CASO ESPECIAL: SQL SERVER → módulo dedicado
        # ==========================================================
        if db_type.lower() == "sqlserver":

            backup_file = run_sqlserver_backup(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                timestamp=timestamp,
            )

            # Guardar local
            saved_path = self.local.save_file(backup_file)

            # Hash
            sha = BackupVerifier.file_sha256(saved_path)

            # Subir a cloud si procede
            cloud_url = None
            if upload_to_cloud and self.cloud:
                remote_name = f"sqlserver/{Path(saved_path).name}"
                try:
                    remote = self.cloud.save_file(str(saved_path), remote_name)
                    cloud_url = f"cloud://{remote}"
                except Exception as e:
                    logger.warning(f"No se pudo subir a la nube: {e}")

            # Registrar
            entry = self.history.add_entry(
                operation="backup",
                db_type="sqlserver",
                database=database,
                file_path=str(saved_path),
                hash=sha,
                status="success",
                message=None,
                cloud_url=cloud_url
            )

            return entry

       # ---------------------------------------------------------
# BASES NORMALIZADAS (MySQL, PostgreSQL, MongoDB)
# ---------------------------------------------------------

# Seleccionar clase conector
        ConnectorClass = DatabaseSelector.get_connector_class(db_type)
        connector = ConnectorClass(host=host, port=port, user=user, password=password, database=database)

        # Crear dump temporal en un directorio temporal seguro (cross-platform)
        raw_name = f"{db_type}_{database}_{timestamp}.dump"
        tmp_dir = Path(tempfile.mkdtemp())
        raw_path = tmp_dir / raw_name

        try:
            connector.dump_database(str(raw_path))  # Genera el dump temporal

            # ================================================
            #  COMPRESSION FIX
            # ================================================
            if compression:
                compressed_files = compress.compress_file(
                    file_path=str(raw_path),
                    formats=[compression]  # <-- FIX: must be list
                )

                if not compressed_files:
                    raise RuntimeError("No se pudo comprimir el archivo.")

                final_path = compressed_files[0]

                # eliminar dump sin comprimir
                if raw_path.exists():
                    raw_path.unlink()
            else:
                final_path = str(raw_path)

            # SHA256 del archivo final
            sha = BackupVerifier.file_sha256(final_path)

            # Guardar localmente **correcto**
            saved_path = self.local.save_file(final_path)

            # Subida a la nube (opcional)
            cloud_url = None
            if upload_to_cloud and self.cloud:
                try:
                    remote = self.cloud.save_file(str(saved_path), f"{db_type}/{Path(saved_path).name}")
                    cloud_url = f"cloud://{remote}"
                except Exception as e:
                    logger.warning(f"No se pudo subir a la nube: {e}")

            # Registrar en el historial
            entry = self.history.add_entry(
                operation="backup",
                db_type=db_type,
                database=database,
                file_path=str(saved_path),
                hash=sha,
                status="success",
                message=None,
                cloud_url=cloud_url
            )

            return entry

        finally:
            # Eliminar dump temporal siempre (borrar todo el directorio temporal)
            try:
                if tmp_dir and tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"No se pudo limpiar el directorio temporal {tmp_dir}: {e}")

    # ==========================================================
    # RESTORE
    # ==========================================================
    def restore_backup(self, db_type: str, host: str, port: int, user: str, password: str, database: str, backup_file: str):
        backup_path = Path(backup_file)

        # 1) Descargar desde cloud si no existe local
        if not backup_path.exists() and self.cloud:
            local_tmp = self.local.base_path / backup_path.name
            self.cloud.get_path(backup_file, str(local_tmp))
            backup_path = local_tmp

        # 2) Extraer si está comprimido
        try:
            extracted = compress.extract(str(backup_path))
        except Exception:
            extracted = str(backup_path)

        # 3) Ejecutar restore
        ConnectorClass = DatabaseSelector.get_connector_class(db_type)
        connector = ConnectorClass(host=host, port=port, user=user, password=password, database=database)
        connector.restore(extracted)

        # 4) Registrar
        self.history.add_entry(
            operation="restore",
            db_type=db_type,
            database=database,
            file_path=str(backup_path),
            hash=None,
            status="success",
            message="Restored successfully",
            cloud_url=None
        )
        return True

    def list_history(self):
        return self.history.get_all()
