import os
from pathlib import Path
from src.db_connectors import SQLServerConnector


def run_sqlserver_backup_test():
    print("=== TEST BACKUP SQL SERVER (AUTO-DETECCIÓN DE CARPETA OFICIAL) ===")

    host = "localhost"
    port = 1433
    user = "backup_user"
    password = "Laboratorio1_1"
    database = "PruebaBackup"

    connector = SQLServerConnector(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

    # ---------------------------------------------------------
    # 1) Detectar carpeta oficial de backups
    # ---------------------------------------------------------
    print("\nDetectando carpeta oficial de SQL Server...")

    backup_dir = connector.get_backup_directory()

    if backup_dir:
        print(f"✔ Carpeta oficial detectada: {backup_dir}")
    else:
        print("❌ No se pudo detectar la carpeta oficial de SQL Server.")
        print("El test no puede continuar sin la detección automática.")
        return

    # ---------------------------------------------------------
    # 2) Construir archivo temporal dentro de la carpeta oficial
    # ---------------------------------------------------------
    test_file = backup_dir / f"{database}_test_auto.bak"
    print(f"\nArchivo de prueba que se usará:\n{test_file}")

    # ---------------------------------------------------------
    # 3) Ejecutar backup (sin output_path → usa carpeta oficial)
    # ---------------------------------------------------------
    print("\nEjecutando backup de prueba...\n")

    try:
        output_file = connector.create_backup(None)  # ← se usa carpeta oficial auto-detectada
        print(f"✔ Backup ejecutado, archivo generado en:\n{output_file}")
    except Exception as e:
        print(f"❌ Error durante el backup:\n{e}")
        return

    # ---------------------------------------------------------
    # 4) Validar que el archivo exista y no esté vacío
    # ---------------------------------------------------------
    print("\nValidando archivo generado...")

    if not Path(output_file).exists():
        print("❌ El archivo NO existe.")
    else:
        size = os.path.getsize(output_file)
        if size == 0:
            print("❌ El archivo se generó vacío (0 bytes).")
        else:
            print(f"✔ Archivo correcto. Tamaño: {size:,} bytes")

    print("\n=== FIN DEL TEST ===")





if __name__ == "__main__":
    run_sqlserver_backup_test()
