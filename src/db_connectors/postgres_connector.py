import subprocess
import shlex
from datetime import datetime
import shutil
import glob
import os


class PostgresConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 5432
        self.user = user
        self.password = password
        self.database = database

        # Detect pg_dump automatically
        self.pg_dump_path = self._find_pg_dump()

    # ----------------------------
    # LOG SYSTEM
    # ----------------------------
    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        with open(self.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(entry)

    # ----------------------------
    # LOCATE PG_DUMP
    # ----------------------------
    def _find_pg_dump(self) -> str:
        """
        Busca pg_dump automáticamente, aunque NO esté en PATH.
        """
        # 1) ¿Está en PATH?
        path = shutil.which("pg_dump")
        if path:
            return path

        # 2) Instalaciones estándar en Windows
        candidates = glob.glob(r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe")
        if candidates:
            return candidates[0]

        # 3) Instalaciones alternativas
        candidates = glob.glob(r"C:\Program Files\pg*\bin\pg_dump.exe")
        if candidates:
            return candidates[0]

        raise FileNotFoundError(
            "❌ No se encontró pg_dump.exe. "
            "Asegúrate de que PostgreSQL esté instalado."
        )

    # ----------------------------
    # VALIDATE CONNECTION (SAFE)
    # ----------------------------
    def validate_connection(self):
        """
        Valida la conexión ejecutando pg_dump sobre un archivo temporal real.
        (Windows NO permite usar NUL, por eso esta versión funciona)
        """

        self.log("🧪 Probando conexión PostgreSQL…")

        env = os.environ.copy()
        env["PGPASSWORD"] = self.password

        # Archivo real temporal → Windows-friendly
        temp_test_file = os.path.join(os.environ.get("TEMP", "."), "pg_dump_test.tmp")

        cmd = (
            f'"{self.pg_dump_path}" '
            f'-h "{self.host}" -p "{self.port}" '
            f'-U "{self.user}" -d "{self.database}" '
            f'-F c -f "{temp_test_file}"'
        )

        process = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        # Eliminamos archivo temporal si existe
        if os.path.exists(temp_test_file):
            try:
                os.remove(temp_test_file)
            except:
                pass

        if process.returncode != 0:
            self.log(f"❌ ERROR conexión PostgreSQL:\n{process.stderr}")
            return False

        self.log("✔️ Conexión PostgreSQL exitosa.")
        return True

    # ----------------------------
    # BACKUP REAL
    # ----------------------------
    def dump_database(self, output_path: str):
        """
        Realiza un backup usando pg_dump.
        """

        # Forzar extensión .dump
        if not output_path.endswith(".dump"):
            output_path += ".dump"

        env = os.environ.copy()
        env["PGPASSWORD"] = self.password

        cmd = (
            f'"{self.pg_dump_path}" -h "{self.host}" -p "{self.port}" '
            f'-U "{self.user}" -d "{self.database}" -F c -f "{output_path}"'
        )

        # Logs iniciales
        self.log(f"=== INICIANDO BACKUP POSTGRES ({self.database}) ===")
        self.log(f"Comando ejecutado: {cmd}")
        self.log(f"Archivo destino: {output_path}")

        process = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        # STDOUT / STDERR
        if process.stdout:
            self.log(f"STDOUT:\n{process.stdout}")

        if process.stderr:
            self.log(f"STDERR:\n{process.stderr}")

        # Validar resultado
        if process.returncode != 0:
            self.log(f"❌ ERROR: pg_dump terminó con código {process.returncode}")
            raise Exception(
                f"pg_dump error:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )

        self.log(f"✔️ Backup Postgres completado: {output_path}")
        self.log(f"=== FIN BACKUP POSTGRES ({self.database}) ===\n")

        return output_path
