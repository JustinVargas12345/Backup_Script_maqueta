'''

from .core import SQLServerBackup
from db_connectors.sqlserver_connector import SQLServerConnector

__all__ = ["SQLServerBackup", "SQLServerConnector", "run_sqlserver_backup"]


def run_sqlserver_backup(
    host: str,
    user: str,
    password: str,
    database: str,
    output_path: str | None = None,
    port: int | None = None
) -> str:
    """
    Función de conveniencia para ejecutar un backup de SQL Server.
    Retorna la ruta del archivo .bak generado.
    """
    connector = SQLServerConnector(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

    backup_engine = SQLServerBackup(connector)
    return backup_engine.full_backup(output_path)
'''
from .core import SQLServerBackup
from db_connectors.sqlserver_connector import SQLServerConnector

__all__ = ["SQLServerBackup", "SQLServerConnector", "run_sqlserver_backup"]

def run_sqlserver_backup(
    host: str,
    user: str,
    password: str,
    database: str,
    backup_type: str = "full",  # Agregado para pasar el tipo de backup
    output_path: str | None = None,
    port: int | None = None
) -> str:
    """
    Función de conveniencia para ejecutar un backup de SQL Server.
    Retorna la ruta del archivo .bak generado.
    """
    connector = SQLServerConnector(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

    backup_engine = SQLServerBackup(connector)
    
    # Llamar a execute_backup con el tipo de backup
    return backup_engine.execute_backup(backup_type, output_path)
