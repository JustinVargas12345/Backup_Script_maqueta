
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


# scripts/test_backup_flow.py
import os
from pathlib import Path



from src.backup_manager import BackupManager
from src.utils.compress import compress_file
from src.storage.local_storage import LocalStorage
from src.storage.cloud_storage import CloudStorage

def main():
    # -----------------------------
    # Configuración de prueba
    # -----------------------------
    config = {
        "local_backup_path": "test_backups",
        "cloud": {
            "provider": "aws",  # podemos simular o usar "mock"
            "aws_access_key": "FAKEKEY",
            "aws_secret_key": "FAKESECRET",
            "region": "us-east-1",
            "bucket": "test-bucket"
        },
        "history_file": "test_history.json",
        "retention_days": 7
    }

    manager = BackupManager(config)

    # -----------------------------
    # Crear archivo dummy como "backup"
    # -----------------------------
    tmp_dir = Path("tmp_test")
    tmp_dir.mkdir(exist_ok=True)
    dummy_file = tmp_dir / "dummy_backup.sql"
    dummy_file.write_text("SELECT 1; -- dummy content")

    print(f"Archivo de prueba creado: {dummy_file}")

    # -----------------------------
    # Comprimir archivo
    # -----------------------------
    compressed_files = compress_file(str(dummy_file), "zip")
    print(f"Archivos comprimidos: {compressed_files}")

    # -----------------------------
    # Guardar en local
    # -----------------------------
    local_storage = LocalStorage("test_backups")
    for f in compressed_files:
        saved_path = local_storage.save_file(f)
        print(f"Archivo guardado localmente: {saved_path}")

    # -----------------------------
    # Simular subida a cloud
    # -----------------------------
    cloud_storage = CloudStorage("aws", config["cloud"])
    for f in compressed_files:
        remote_name = f"test/{Path(f).name}"
        # En pruebas sin credenciales válidas, podemos simular
        try:
            cloud_storage.save_file(str(f), remote_name)
            print(f"Archivo subido a cloud: {remote_name}")
        except Exception as e:
            print(f"Simulación cloud, no se subió: {remote_name} ({e})")

    # -----------------------------
    # Historial simulado
    # -----------------------------
    history_entry = manager.history.add_entry(
        operation="backup",
        db_type="dummydb",
        database="dummy",
        file_path=str(saved_path),
        hash="FAKEHASH123",
        status="success",
        message="Test backup complete",
        cloud_url="cloud://dummy/test.zip"
    )
    print("Entrada de historial creada:", history_entry)

if __name__ == "__main__":
    main()
