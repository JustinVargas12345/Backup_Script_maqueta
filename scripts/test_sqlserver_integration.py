# scripts/test_sqlserver_integration.py
"""
TEST INTEGRACIÓN COMPLETA SQL SERVER
------------------------------------
Prueba:
 - Conexión
 - Lectura de carpeta de backups
 - Backup FULL
 - Backup DIFFERENTIAL
 - Backup LOG
"""

from src.db_connectors.sqlserver_connector import SQLServerConnector
from src.sqlserver_backup import SQLServerBackup
from src.sqlserver_backup.system_utils import get_sqlserver_backup_dir


def main():
    print("=== TEST INTEGRACIÓN SQL SERVER ===")

    # ------------------------------------------
    # CONFIGURA AQUÍ TU CONEXIÓN DE PRUEBA
    # ------------------------------------------
    SERVER = "localhost\\SQLEXPRESS"
    USER = "sa"
    PASSWORD = "Laboratorio1"
    DATABASE = "PruebaBackup"
    PORT = None  # o 1433 si usas puerto

    # ------------------------------------------
    # 1. PROBAR DETECCIÓN DE CARPETA DE BACKUP
    # ------------------------------------------
    print("\n[1] Detectando carpeta de backups...")
    folder = get_sqlserver_backup_dir(SERVER, USER, PASSWORD, PORT)
    if folder is None:
        print("❌ No se pudo detectar la carpeta de backup")
        return

    print(f"✔ Carpeta detectada: {folder}")

    # ------------------------------------------
    # 2. PROBAR CONEXIÓN Y CONTROLADOR
    # ------------------------------------------
    print("\n[2] Creando conector SQLServerConnector...")
    connector = SQLServerConnector(
        host=SERVER,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        port=PORT,
    )

    print("✔ Conector creado correctamente")

    # ------------------------------------------
    # 3. CREAR OBJETO BACKUP CORE
    # ------------------------------------------
    backup = SQLServerBackup(connector)

    # ------------------------------------------
    # 4. BACKUP FULL
    # ------------------------------------------
    print("\n[3] Ejecutando BACKUP FULL...")
    try:
        full_path = backup.full_backup()
        print(f"✔ Backup FULL generado: {full_path}")
    except Exception as e:
        print(f"❌ Error en FULL: {e}")
        return

    # ------------------------------------------
    # 5. BACKUP DIFERENCIAL
    # ------------------------------------------
    print("\n[4] Ejecutando BACKUP DIFERENCIAL...")
    try:
        diff_path = backup.differential_backup()
        print(f"✔ Backup DIFERENCIAL generado: {diff_path}")
    except Exception as e:
        print(f"❌ Error en DIFERENCIAL: {e}")

    # ------------------------------------------
    # 6. BACKUP DE LOG
    # ------------------------------------------
    print("\n[5] Ejecutando BACKUP LOG...")
    try:
        log_path = backup.log_backup()
        print(f"✔ Backup LOG generado: {log_path}")
    except Exception as e:
        print(f"❌ Error en LOG: {e}")

    print("\n=== TEST FINALIZADO ===")


if __name__ == "__main__":
    main()
