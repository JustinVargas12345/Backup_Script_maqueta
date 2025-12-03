"""
Utilidad para encontrar el último backup de cada tipo de base de datos.
Busca en:
  - backups/ para PostgreSQL, MySQL, Mongo
  - SQL Server backup directory (desde config o ruta estándar)
"""

from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import json
from utils.history_manager import HistoryManager


class BackupFinder:
    """Encuentra el último backup por tipo de DB."""
    
    BACKUP_DIR = Path("backups")
    
    # Rutas estándar de SQL Server según instalación
    SQLSERVER_BACKUP_PATHS = [
        r"C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL16.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL14.SQLEXPRESS\MSSQL\Backup",
    ]
    
    @staticmethod
    def find_latest_backup(db_type: str, database: Optional[str] = None) -> Optional[Path]:
        """
        Encuentra el último backup de un tipo de DB dado.
        
        Args:
            db_type: "postgres", "mysql", "mongo", "sqlserver"
            database: nombre de BD (opcional, si no se especifica busca el más reciente)
        
        Returns:
            Path al archivo de backup o None si no se encuentra
        """
        
        if db_type == "sqlserver":
            return BackupFinder._find_latest_sqlserver(database)
        else:
            return BackupFinder._find_latest_in_backups_folder(db_type, database)
    
    @staticmethod
    def _find_latest_in_backups_folder(db_type: str, database: Optional[str] = None) -> Optional[Path]:
        """Busca en carpeta backups/ el último archivo de un tipo DB."""
        
        if not BackupFinder.BACKUP_DIR.exists():
            return None
        
        # Extensiones esperadas por tipo
        extensions_map = {
            "postgres": [".dump", ".sql"],
            "mysql": [".sql", ".dump"],
            "mongo": [".dump", ".bson", ".json"],
        }
        
        extensions = extensions_map.get(db_type.lower(), [])
        if not extensions:
            return None
        
        candidates = []
        
        for ext in extensions:
            pattern = f"{db_type}*{ext}" if not database else f"{db_type}_{database}*{ext}"
            candidates.extend(BackupFinder.BACKUP_DIR.glob(pattern))
        
        if not candidates:
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return candidates[0]
    
    @staticmethod
    def _find_latest_sqlserver(database: Optional[str] = None) -> Optional[Path]:
        """Busca en directorios estándar de SQL Server el último backup."""
        
        candidates = []
        
        for base_path_str in BackupFinder.SQLSERVER_BACKUP_PATHS:
            base_path = Path(base_path_str)
            if not base_path.exists():
                continue
            
            # Buscar archivos .bak (full), .trn (transaction log), .dmp
            for pattern in ["*.bak", "*.trn", "*.dmp"]:
                candidates.extend(base_path.glob(pattern))
        
        if not candidates:
            return None
        
        # Si se especifica BD, filtrar por nombre
        if database:
            candidates = [c for c in candidates if database.lower() in c.name.lower()]
        
        if not candidates:
            return None
        
        # Ordenar por fecha (más reciente primero), priorizando .bak > .trn
        def sort_key(p):
            # Preferencia: full (.bak) > transaction log (.trn)
            prio = {"bak": 0, "trn": 1, "dmp": 2}
            suffix_prio = prio.get(p.suffix.lstrip(".").lower(), 999)
            return (suffix_prio, -p.stat().st_mtime)
        
        candidates.sort(key=sort_key)
        return candidates[0]
    
    @staticmethod
    def list_backups_by_database(db_type: str) -> dict:
        """
        Lista todos los backups agrupados por base de datos.
        
        Returns:
            Dict {database_name: [Path, Path, ...]} ordenado por fecha
        """
        
        if db_type == "sqlserver":
            return BackupFinder._list_sqlserver_backups()
        else:
            return BackupFinder._list_backups_in_folder(db_type)
    
    @staticmethod
    def _list_backups_in_folder(db_type: str) -> dict:
        """Lista backups en carpeta backups/ agrupados por DB."""
        
        if not BackupFinder.BACKUP_DIR.exists():
            return {}
        
        extensions_map = {
            "postgres": [".dump", ".sql"],
            "mysql": [".sql", ".dump"],
            "mongo": [".dump", ".bson", ".json"],
        }
        
        extensions = extensions_map.get(db_type.lower(), [])
        candidates = []
        
        for ext in extensions:
            candidates.extend(BackupFinder.BACKUP_DIR.glob(f"{db_type}*{ext}"))
        
        # Agrupar por nombre de BD (extrae de nombre de archivo)
        by_db = {}
        for p in candidates:
            # Formato: {dbtype}_{database}_{timestamp}.{ext}
            parts = p.stem.split("_")
            if len(parts) >= 2:
                db_name = parts[1]
                if db_name not in by_db:
                    by_db[db_name] = []
                by_db[db_name].append(p)
        
        # Ordenar cada grupo por fecha (más reciente primero)
        for db_name in by_db:
            by_db[db_name].sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return by_db
    
    @staticmethod
    def _list_sqlserver_backups() -> dict:
        """Lista backups de SQL Server agrupados por BD."""
        
        candidates = []
        
        for base_path_str in BackupFinder.SQLSERVER_BACKUP_PATHS:
            base_path = Path(base_path_str)
            if not base_path.exists():
                continue
            
            for pattern in ["*.bak", "*.trn", "*.dmp"]:
                candidates.extend(base_path.glob(pattern))
        
        # Agrupar por nombre de BD (parte antes de _full, _diff, _log, _trn)
        by_db = {}
        for p in candidates:
            # Formato: {database}_full/diff/log_{timestamp}.{ext}
            stem = p.stem
            # Extraer nombre de BD (parte antes del último _)
            parts = stem.rsplit("_", 1)
            if len(parts) >= 1:
                db_name = parts[0].replace("_full", "").replace("_diff", "").replace("_log", "")
                if db_name not in by_db:
                    by_db[db_name] = []
                by_db[db_name].append(p)
        
        # Ordenar cada grupo por fecha y tipo (full > diff > log)
        for db_name in by_db:
            def sort_key(p):
                prio = {"bak": 0, "trn": 1, "dmp": 2}
                suffix_prio = prio.get(p.suffix.lstrip(".").lower(), 999)
                return (suffix_prio, -p.stat().st_mtime)
            
            by_db[db_name].sort(key=sort_key)
        
        return by_db
    
    @staticmethod
    def find_by_history(db_type: str, database: Optional[str] = None) -> Optional[Path]:
        """
        Busca el último backup usando el historial JSON (backup_history.json).
        Más confiable que buscar en carpetas.
        
        Args:
            db_type: "postgres", "mysql", "mongo", "sqlserver"
            database: nombre de BD (opcional)
        
        Returns:
            Path al archivo de backup más reciente registrado
        """
        
        try:
            hm = HistoryManager("backup_history.json")
            entries = hm.get_all()
        except Exception:
            return None
        
        # Filtrar por tipo y BD
        matching = []
        for entry in entries:
            if entry.get("db_type") != db_type:
                continue
            if database and entry.get("database") != database:
                continue
            if entry.get("status") != "success":
                continue
            
            file_path = entry.get("file_path")
            if file_path and Path(file_path).exists():
                matching.append((entry, Path(file_path)))
        
        if not matching:
            return None
        
        # Ordenar por timestamp (más reciente primero)
        matching.sort(key=lambda x: x[0].get("timestamp", ""), reverse=True)
        
        return matching[0][1]
