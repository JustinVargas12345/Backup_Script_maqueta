import subprocess
import shlex
import os
from datetime import datetime


class MongoConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database, auth_db="admin"):
        self.host = host
        self.port = port or 27017
        self.user = user
        self.password = password
        self.database = database
        self.auth_db = auth_db

    # ----------------------------
    # MÉTODO INTERNO PARA LOGGING
    # ----------------------------
    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        with open(self.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(entry)

    # ----------------------------
    # MÉTODO PRINCIPAL DE BACKUP
    # ----------------------------
    def dump_database(self, output_path: str):
        """
        Realiza backup con mongodump y escribe logs en backup_master_log.
        """

        # Forzar extensión .dump
        if not output_path.endswith(".dump"):
            output_path += ".dump"

        dump_dir = output_path[:-5]  # remover .dump final

        os.makedirs(os.path.dirname(dump_dir), exist_ok=True)

        cmd = (
            f'mongodump --host {self.host} --port {self.port} '
            f'--username "{self.user}" --password "{self.password}" '
            f'--authenticationDatabase "{self.auth_db}" '
            f'--db "{self.database}" --out "{dump_dir}"'
        )

        # Log inicial
        self.log(f"=== INICIANDO BACKUP MONGO ({self.database}) ===")
        self.log(f"Comando ejecutado: {cmd}")
        self.log(f"Directorio destino: {dump_dir}")

        # Ejecutar mongodump
        process = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Registrar output
        if process.stdout:
            self.log(f"STDOUT:\n{process.stdout}")

        if process.stderr:
            self.log(f"STDERR:\n{process.stderr}")

        # Validar resultado
        if process.returncode != 0:
            self.log(f"❌ ERROR: mongodump terminó con código {process.returncode}")
            raise Exception(
                f"mongodump error:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )

        # Crear archivo simbólico .dump
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("TYPE: MONGO_DUMP_DIRECTORY\n")
            f.write(f"PATH: {dump_dir}\n")

        # Log final exitoso
        self.log(f"✔️ Backup completado con éxito. Archivo placeholder: {output_path}")
        self.log(f"=== FIN BACKUP MONGO ({self.database}) ===\n")
