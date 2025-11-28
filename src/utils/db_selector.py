# src/utils/db_selector.py
from typing import Type

from src.db_connectors.postgres_connector import PostgresConnector
from src.db_connectors.mysql_connector import MySQLConnector
from src.db_connectors.mongo_connector import MongoConnector


class DatabaseSelector:
    """
    Selecciona el conector adecuado según el motor de base de datos.
    """

    @staticmethod
    def get_connector_class(engine: str) -> Type:
        if not engine:
            raise ValueError("No se especificó un motor de base de datos.")

        e = engine.lower()

        # Variantes comunes aceptadas
        if e in ("postgres", "postgresql", "pg", "psql"):
            return PostgresConnector

        if e in ("mysql", "mariadb"):
            return MySQLConnector

        if e in ("mongo", "mongodb", "mongo-db"):
            return MongoConnector

        raise ValueError(f"Motor no soportado: {engine}")
