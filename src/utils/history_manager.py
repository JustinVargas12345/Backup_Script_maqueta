# src/utils/history_manager.py
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryManager:
    """
    Maneja el historial de backups en un archivo JSON.
    Entrada por backup:
      - id
      - operation (backup|restore)
      - db_type
      - database
      - file_path
      - hash
      - timestamp
      - cloud_url (opcional)
      - status (success|error)
      - message (opcional)
    """

    def __init__(self, history_file: str = "data/backup_history.json"):
        self.history_path = Path(history_file)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")
            return
        try:
            json.loads(self.history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.history_path.write_text("[]", encoding="utf-8")

    def _load_history(self) -> List[Dict[str, Any]]:
        return json.loads(self.history_path.read_text(encoding="utf-8"))

    def _save_history(self, data: List[Dict[str, Any]]):
        self.history_path.write_text(json.dumps(data, indent=4), encoding="utf-8")

    def add_entry(
        self,
        operation: str,
        db_type: str,
        database: str,
        file_path: str,
        hash: Optional[str],
        status: str,
        message: Optional[str] = None,
        cloud_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        history = self._load_history()
        entry = {
            "id": str(uuid.uuid4()),
            "operation": operation,
            "db_type": db_type,
            "database": database,
            "file_path": file_path,
            "hash": hash,
            "status": status,
            "message": message,
            "cloud_url": cloud_url,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        history.append(entry)
        self._save_history(history)
        return entry

    def get_all(self) -> List[Dict[str, Any]]:
        return self._load_history()

    def get_entry(self, entry_id: str) -> Dict[str, Any]:
        history = self._load_history()
        for item in history:
            if item["id"] == entry_id:
                return item
        raise ValueError(f"No existe un backup con id {entry_id}")

    def clear(self):
        self._save_history([])
