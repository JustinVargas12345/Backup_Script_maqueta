import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


class HistoryManager:
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

    def _load_history_raw(self) -> List[Dict[str, Any]]:
        return json.loads(self.history_path.read_text(encoding="utf-8"))

    def _normalize_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un registro antiguo al formato nuevo.
        No modifica el archivo original.
        """

        # Si es formato nuevo → devolverlo tal cual
        if "operation" in entry or "file_path" in entry:
            return entry

        # ---- Mapeo de tu formato viejo → formato nuevo ----
        return {
            "id": entry.get("id", str(uuid.uuid4())),
            "operation": entry.get("operation", "backup"),  # antes no existía
            "db_type": entry.get("dbtype", "unknown"),
            "database": entry.get("database", None),
            "file_path": entry.get("file", None),
            "hash": entry.get("hash", None),
            "cloud_url": entry.get("cloud", None),
            "status": entry.get("status", "unknown"),
            "message": entry.get("message", None),
            "timestamp": entry.get("timestamp", datetime.now().isoformat()),
        }

    def _load_history(self) -> List[Dict[str, Any]]:
        raw = self._load_history_raw()
        return [self._normalize_entry(r) for r in raw]

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
            "timestamp": datetime.now().isoformat(),
        }

        history = self._load_history_raw()
        history.append(entry)
        self._save_history(history)

        return entry

    def get_all(self) -> List[Dict[str, Any]]:
        return self._load_history()

    def get_entry(self, entry_id: str) -> Dict[str, Any]:
        for item in self._load_history():
            if item["id"] == entry_id:
                return item
        raise ValueError(f"No existe un backup con id {entry_id}")

    def clear(self):
        self._save_history([])
