# scripts/test_sqlserver_integration.py

from src.sqlserver_backup import run_sqlserver_backup, SQLServerConnector
from pathlib import Path

print("=== TEST INTEGRACIÓN SQL SERVER ===")

# Parámetros de prueba
HOST = "localhost\\SQLEXPRESS"  # Cambia según tu instancia
USER = "backup_user"
PASSWORD = "Laboratorio1_1"
DATABASE = "PruebaBackup"
PORT = None  # Si es instancia nombrada, deja None

# Opcional: carpeta de salida específica
OUTPUT_PATH = None  # Si quieres usar la carpeta oficial de SQL Server

try:
    # Ejecutar backup
    backup_file = run_sqlserver_backup(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        output_path=OUTPUT_PATH,
        port=PORT
    )

    if Path(backup_file).exists():
        print(f"✔ Backup exitoso: {backup_file}")
    else:
        print(f"❌ Backup terminado pero no se encontró el archivo: {backup_file}")

except Exception as e:
    print(f"❌ Error durante el backup: {e}")
