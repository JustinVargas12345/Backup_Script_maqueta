'''
import subprocess
import shlex
from datetime import datetime


class PostgresConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 5432
        self.user = user
        self.password = password
        self.database = database

    # ----------------------------
    # MÉTODO DE LOG
    # ----------------------------
    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        with open(self.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(entry)

    # ----------------------------
    # DUMP PRINCIPAL
    # ----------------------------
    def dump_database(self, output_path: str):
        """
        Realiza un backup usando pg_dump y registra logs.
        """

        # Forzar extensión .dump si falta
        if not output_path.endswith(".dump"):
            output_path += ".dump"

        env = {"PGPASSWORD": self.password}

        cmd = (
            f'pg_dump -h "{self.host}" -p "{self.port}" -U "{self.user}" '
            f'-d "{self.database}" -F c -f "{output_path}"'
        )

        # Log inicial
        self.log(f"=== INICIANDO BACKUP POSTGRES ({self.database}) ===")
        self.log(f"Comando ejecutado: {cmd}")
        self.log(f"Archivo destino: {output_path}")

        process = subprocess.run(
            shlex.split(cmd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Log outputs
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

        # Log final
        self.log(f"✔️ Backup Postgres completado: {output_path}")
        self.log(f"=== FIN BACKUP POSTGRES ({self.database}) ===\n")
'''

import subprocess
import shlex
from datetime import datetime


class PostgresConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 5432
        self.user = user
        self.password = password
        self.database = database

    # ----------------------------
    # MÉTODO DE LOG
    # ----------------------------
    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        with open(self.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(entry)

    # ----------------------------
    # Validar conexión con pg_dump
    # ----------------------------
    def validate_connection(self):
        """
        Validar si la conexión al servidor PostgreSQL es exitosa
        usando pg_dump.
        """
        env = {"PGPASSWORD": self.password}
        
        cmd = (
            f'pg_dump -h "{self.host}" -p "{self.port}" -U "{self.user}" '
            f'-d "{self.database}" -F c -f "/dev/null"'
        )

        process = subprocess.run(
            shlex.split(cmd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:
            self.log(f"❌ ERROR: Conexión a PostgreSQL fallida. STDERR:\n{process.stderr}")
            raise Exception(f"Conexión fallida: {process.stderr}")

        self.log(f"✔️ Conexión a PostgreSQL exitosa.")
        return True

    # ----------------------------
    # DUMP PRINCIPAL
    # ----------------------------
    def dump_database(self, output_path: str):
        """
        Realiza un backup usando pg_dump y registra logs.
        """

        # Forzar extensión .dump si falta
        if not output_path.endswith(".dump"):
            output_path += ".dump"

        env = {"PGPASSWORD": self.password}

        cmd = (
            f'pg_dump -h "{self.host}" -p "{self.port}" -U "{self.user}" '
            f'-d "{self.database}" -F c -f "{output_path}"'
        )

        # Log inicial
        self.log(f"=== INICIANDO BACKUP POSTGRES ({self.database}) ===")
        self.log(f"Comando ejecutado: {cmd}")
        self.log(f"Archivo destino: {output_path}")

        process = subprocess.run(
            shlex.split(cmd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Log outputs
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

        # Log final
        self.log(f"✔️ Backup Postgres completado: {output_path}")
        self.log(f"=== FIN BACKUP POSTGRES ({self.database}) ===\n")
