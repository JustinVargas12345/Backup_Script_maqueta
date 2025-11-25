# src/backup_manager.py
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.utils.history_manager import HistoryManager
from src.utils.backup_verifier import BackupVerifier
from src.utils.compress import Compressor
from src.utils.db_selector import DatabaseSelector

from src.storage.loca_storage import LocalStorage
from src.storage.cloud_storage import CloudStorage


class BackupManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.local = LocalStorage(self.config.get("local_backup_path", "backups"))
        cloud_cfg = self.config.get("cloud", {})
        self.cloud = CloudStorage(cloud_cfg.get("provider", ""), cloud_cfg) if cloud_cfg.get("provider") else None
        self.history = HistoryManager(self.config.get("history_file", "data/backup_history.json"))
        self.verifier = BackupVerifier()
        self.retention_days = self.config.get("retention_days", 7)

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
        # 1) select connector class and instantiate
        ConnectorClass = DatabaseSelector.get_connector_class(db_type)
        connector = ConnectorClass(host=host, port=port, user=user, password=password, database=database)

        # 2) create temp output path
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_name = f"{db_type}_{database}_{timestamp}"
        tmp_dir = Path("/tmp") if Path("/tmp").exists() else Path(".")
        raw_path = tmp_dir / (raw_name + ".dump")

        # 3) perform db dump via connector API (assumes connector has dump_database method)
        connector.dump_database(str(raw_path))

        # 4) compress if needed
        final_path = Compressor.compress(str(raw_path), compression) if compression else str(raw_path)

        # 5) compute hash
        sha = BackupVerifier.file_sha256(final_path)

        # 6) save locally
        saved_path = self.local.save_file(final_path)

        # 7) upload to cloud if requested
        cloud_url = None
        if upload_to_cloud and self.cloud:
            remote = f"{db_type}/{Path(saved_path).name}"
            ok = self.cloud.upload(str(saved_path), remote)
            if ok:
                cloud_url = remote

        # 8) add to history
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
        # if backup_file is remote (starts with cloud provider prefix) download first
        p = Path(backup_file)
        if not p.exists() and self.cloud:
            # download to local tmp
            local_tmp = self.local.base_path / Path(backup_file).name
            self.cloud.download(backup_file, str(local_tmp))
            backup_file = str(local_tmp)

        # extract if compressed
        try:
            extracted = Compressor.extract(backup_file)
        except Exception:
            extracted = backup_file

        # choose connector and call its restore method
        ConnectorClass = DatabaseSelector.get_connector_class(db_type)
        connector = ConnectorClass(host=host, port=port, user=user, password=password, database=database)
        # NOTE: assume connector has restore(extracted_path) method
        connector.restore(str(extracted))

        # record in history
        self.history.add_entry(
            operation="restore",
            db_type=db_type,
            database=database,
            file_path=backup_file,
            hash=None,
            status="success",
            message="Restored successfully",
            cloud_url=None
        )
        return True

    def list_history(self):
        return self.history.get_all()
