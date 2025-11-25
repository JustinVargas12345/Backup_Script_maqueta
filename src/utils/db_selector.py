# src/utils/db_selector.py
from typing import Tuple, Type
from pathlib import Path

# import connectors (ajusta si tus archivos están en otro paquete)
from src.db_connectors.postgres_connector import PostgresConnector
from src.db_connectors.mysql_connector import MySQLConnector
from src.db_connectors.mongo_connector import MongoConnector


class DatabaseSelector:
    """
    Selector de conectores según el nombre del motor.
    """

    @staticmethod
    def get_connector_class(engine: str):
        e = engine.lower()
        if e in ("postgres", "postgresql"):
            return PostgresConnector
        if e in ("mysql",):
            return MySQLConnector
        if e in ("mongo", "mongodb"):
            return MongoConnector
        raise ValueError(f"Motor no soportado: {engine}")
