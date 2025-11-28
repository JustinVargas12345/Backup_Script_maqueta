import subprocess
import shlex
from datetime import datetime


class MySQLConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 3306
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
    # MÉTODO PRINCIPAL
    # ----------------------------
    def dump_database(self, output_path: str):
        """
        Realiza un backup usando mysqldump y registra logs.
        """

        # Forzar extensión .sql
        if not output_path.endswith(".sql"):
            output_path += ".sql"

        cmd = (
            f'mysqldump -h {self.host} -P {self.port} -u "{self.user}" '
            f'-p"{self.password}" --databases "{self.database}" > "{output_path}"'
        )

        # Log inicial
        self.log(f"=== INICIANDO BACKUP MYSQL ({self.database}) ===")
        self.log(f"Comando ejecutado: {cmd}")
        self.log(f"Archivo destino: {output_path}")

        # IMPORTANTE: shell=True es necesario para usar ">"
        process = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Log outputs
        if process.stdout:
            self.log(f"STDOUT:\n{process.stdout}")

        if process.stderr:
            self.log(f"STDERR:\n{process.stderr}")

        # Validar error
        if process.returncode != 0:
            self.log(f"❌ ERROR: mysqldump terminó con código {process.returncode}")
            raise Exception(
                f"mysqldump error:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )

        # Log final
        self.log(f"✔️ Backup MySQL completado: {output_path}")
        self.log(f"=== FIN BACKUP MYSQL ({self.database}) ===\n")
