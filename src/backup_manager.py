# src/backup_manager.py
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.utils.history_manager import HistoryManager
from src.utils.backup_verifier import BackupVerifier
#from src.utils.compress import compress_file
from src.utils.db_selector import DatabaseSelector
from src.utils import compress
from storage.local_storage import LocalStorage
from storage.cloud_storage import CloudStorage


class BackupManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.local = LocalStorage(self.config.get("local_backup_path", "backups"))

        cloud_cfg = self.config.get("cloud", {})
        self.cloud = CloudStorage(cloud_cfg.get("provider", ""), cloud_cfg) if cloud_cfg.get("provider") else None

        self.history = HistoryManager(self.config.get("history_file", "data/backup_history.json"))
        self.verifier = BackupVerifier()
        self.retention_days = self.config.get("retention_days", 7)

    from src.utils import compress

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
       
        import datetime
        from pathlib import Path
        from src.utils import compress

        # ==========================================================
        # 1) Seleccionar clase del conector y crear instancia
        # ==========================================================
        ConnectorClass = DatabaseSelector.get_connector_class(db_type)
        connector = ConnectorClass(host=host, port=port, user=user, password=password, database=database)

        # ==========================================================
        # 2) Crear path temporal para el dump
        # ==========================================================
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_name = f"{db_type}_{database}_{timestamp}"
        tmp_dir = Path("/tmp") if Path("/tmp").exists() else Path(".")
        raw_path = tmp_dir / (raw_name + ".dump")

        # ==========================================================
        # 3) Realizar dump de la base de datos
        # ==========================================================
        connector.dump_database(str(raw_path))

        # ==========================================================
        # 4) Comprimir si se especifica
        # ==========================================================
        if compression:
            compressed_files = compress.compress_file(str(raw_path), [compression])
            if not compressed_files:
                raise RuntimeError("No se pudo comprimir el archivo de backup.")
            final_path = compressed_files[0]  # usar solo el primer archivo
        else:
            final_path = str(raw_path)

        # ==========================================================
        # 5) Calcular hash SHA256
        # ==========================================================
        sha = BackupVerifier.file_sha256(final_path)

        # ==========================================================
        # 6) Guardar localmente
        # ==========================================================
        saved_path = self.local.save_file(final_path)

        # ==========================================================
        # 7) Subir a la nube si se solicita
        # ==========================================================
        cloud_url = None
        if upload_to_cloud and self.cloud:
            remote_name = f"{db_type}/{Path(saved_path).name}"
            try:
                cloud_remote = self.cloud.save_file(str(saved_path), remote_name)
                cloud_url = f"cloud://{cloud_remote}"
            except Exception as e:
                print(f"Simulación cloud, no se subió: {remote_name} ({e})")

        # ==========================================================
        # 8) Agregar registro al historial
        # ==========================================================
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



    def restore_backup(self, db_type: str, host: str, port: int, user: str, password: str, database: str, backup_file: str):
        backup_path = Path(backup_file)

        # 1) if remote cloud file, download first
        if not backup_path.exists() and self.cloud:
            local_tmp = self.local.base_path / backup_path.name
            self.cloud.get_path(backup_file, str(local_tmp))
            backup_path = local_tmp

        # 2) extract if compressed
        try:
            extracted = compress.extract(str(backup_path))
        except Exception:
            extracted = str(backup_path)

        # 3) restore via connector
        ConnectorClass = DatabaseSelector.get_connector_class(db_type)
        connector = ConnectorClass(host=host, port=port, user=user, password=password, database=database)
        connector.restore(extracted)

        # 4) record in history
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
