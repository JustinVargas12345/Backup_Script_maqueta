

import subprocess
import shutil
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from .errors import DatabaseNotFoundError


class MongoConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database, auth_db="admin"):
        self.host = host
        self.port = port or 27017
        self.user = user
        self.password = password
        self.database = database
        self.auth_db = auth_db

        # Detectar mongodump
        self.mongodump_path = self._find_mongodump()

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------
    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        with open(self.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(entry)

    # --------------------------------------------------------
    # DETECTAR MONGODUMP
    # --------------------------------------------------------
    def _find_mongodump(self):
        # 1) Buscar en PATH
        path = shutil.which("mongodump")
        if path:
            self.log(f"mongodump encontrado en PATH: {path}")
            return path

        # 2) Rutas comunes en Windows
        common_paths = [
            r"C:\Program Files\MongoDB\Tools\bin\mongodump.exe",
            r"C:\Program Files\MongoDB\Tools\bin\mongodb-database-tools-windows-x86_64-100.13.0\bin\mongodump.exe",
            r"C:\Program Files\MongoDB\Server\7.0\bin\mongodump.exe",
        ]

        for p in common_paths:
            if os.path.exists(p):
                self.log(f"mongodump detectado en ruta conocida: {p}")
                return p

        # No lanzar desde el constructor: devolver None y dejar que quien llame decida
        # cómo manejar la ausencia del binario (por ejemplo, el CLI ya valida binarios).
        self.log("❌ ERROR: No se encontró mongodump en PATH ni en ubicaciones conocidas.")
        return None

    # --------------------------------------------------------
    # VALIDAR CONEXIÓN A MONGO (ping)
    # --------------------------------------------------------

    @staticmethod
    def try_connection(uri, timeout=3000):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=timeout)
            client.admin.command("ping")
            return True, uri
        except PyMongoError:
            return False, uri


    @staticmethod
    def validate_connection(host="localhost", port=27017, user=None, pwd=None, db="admin"):
        attempts = []

        # 1. Sin autenticación
        attempts.append(f"mongodb://{host}:{port}/?retryWrites=true&w=majority")

        # 2. Con autenticación (mongodb://user:pass@host:port/db)
        if user and pwd:
            attempts.append(
                f"mongodb://{user}:{pwd}@{host}:{port}/{db}?authSource={db}&retryWrites=true&w=majority"
            )

        # 3. Con SRV (solo si host parece un dominio)
        if "." in host:
            if user and pwd:
                attempts.append(
                    f"mongodb+srv://{user}:{pwd}@{host}/{db}?retryWrites=true&w=majority"
                )
            else:
                attempts.append(
                    f"mongodb+srv://{host}/{db}?retryWrites=true&w=majority"
                )

        # Intentar cada conexion
        for uri in attempts:
            ok, used_uri = MongoConnector.try_connection(uri)
            if ok:
                print(f"[OK] Conexión exitosa usando: {used_uri}")
                return True

            print(f"[FAIL] No funcionó: {used_uri}")

        print("[ERROR] Ninguno de los métodos de conexión funcionó.")
        return False

    # --------------------------------------------------------
    # BACKUP CON MONGODUMP
    # --------------------------------------------------------
    def dump_database(self, output_path: str):
        """
        Realiza backup con mongodump y deja un archivo .dump apuntando al folder.
        """

        if not output_path.endswith(".dump"):
            output_path += ".dump"

        dump_dir = output_path.replace(".dump", "")  # carpeta destino

        os.makedirs(os.path.dirname(dump_dir), exist_ok=True)

        cmd = [
            self.mongodump_path,
            "--host", self.host,
            "--port", str(self.port),
            "--username", self.user,
            "--password", self.password,
            "--authenticationDatabase", self.auth_db,
            "--db", self.database,
            "--out", dump_dir
        ]

        if not self.mongodump_path:
            self.log("❌ ERROR: mongodump no disponible. No es posible realizar backup de MongoDB.")
            raise FileNotFoundError("mongodump no disponible en el sistema. Instala MongoDB Database Tools.")

        # Log inicial
        self.log(f"=== INICIANDO BACKUP MONGO ({self.database}) ===")
        self.log("Comando ejecutado: " + " ".join(cmd))
        self.log(f"Directorio destino: {dump_dir}")

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Logs
        if process.stdout:
            self.log("STDOUT:\n" + process.stdout)

        if process.stderr:
            self.log("STDERR:\n" + process.stderr)

        # Validar OK
        if process.returncode != 0:
            stderr_l = (process.stderr or "").lower()
            # Buscar patrones comunes de "db not found"
            if self.database and (self.database.lower() in stderr_l or 'no such' in stderr_l or 'does not exist' in stderr_l or 'not found' in stderr_l):
                try:
                    self.log(f"❌ ERROR: Base de datos no encontrada ({self.database}). STDERR: {process.stderr}")
                except Exception:
                    pass
                raise DatabaseNotFoundError(process.stderr)

            self.log(f"❌ ERROR: mongodump terminó con código {process.returncode}")
            raise Exception(process.stderr)

        # Archivo simbólico
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("TYPE: MONGO_DUMP_DIRECTORY\n")
            f.write(f"PATH: {dump_dir}\n")

        self.log(f"✔️ Backup MONGO completado: {dump_dir}")
        self.log(f"=== FIN BACKUP MONGO ({self.database}) ===\n")
