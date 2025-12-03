

import subprocess
import glob
import os
from datetime import datetime
import shutil
import traceback

class MySQLConnector:
    LOG_FILE = "backup_master_log"

    def __init__(self, host, port, user, password, database, *, verbose: bool = False, capture_output: bool = False, log_file: str = None, traceback_on_error: bool = False):
        # Mantener compatibilidad: parámetros posicionales anteriores siguen funcionando
        self.host = host
        self.port = port or 3306
        self.user = user
        self.password = password
        self.database = database

        # Opciones de logging ampliadas (no cambian comportamiento por defecto)
        self.verbose = bool(verbose)
        self.capture_output = bool(capture_output)
        self.traceback_on_error = bool(traceback_on_error)
        # Si se pasa log_file, usarlo para los logs; si no, usar LOG_FILE class attr
        self.log_file = log_file or self.LOG_FILE

        # Detectar binarios automáticamente
        self.mysql_path = self._find_mysql()
        self.mysqldump_path = self._find_mysqldump()

        # Log rutas detectadas
        try:
            self.log(f"mysql_path -> {self.mysql_path}")
            self.log(f"mysqldump_path -> {self.mysqldump_path}")
        except Exception as e:
            # en caso de fallo al loggear, pasar
            pass

    # ----------------------------
    # MÉTODO DE LOG
    # ----------------------------
    def log(self, message: str):
        """Escribe en el log principal y opcionalmente en stdout si `verbose` está activo."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as log_file:
                log_file.write(entry)
        except Exception as e:
            # Intentar escribir en el log por defecto si falla
            try:
                with open(self.LOG_FILE, "a", encoding="utf-8") as log_file:
                    log_file.write(entry)
            except Exception as e2:
                pass

        # También imprimir en consola si verbose
        if getattr(self, "verbose", False):
            try:
                print(entry, end="")
            except Exception as e:
                pass

    # ----------------------------
    # BUSCAR mysql.exe
    # ----------------------------
    def _find_mysql(self) -> str:
        """
        Busca mysql.exe automáticamente.
        """

        # 1) Buscar en PATH
        try:
            self.log("_find_mysql: buscando 'mysql' en PATH")
        except Exception as e:
            pass

        path = shutil.which("mysql")
        if path:
            try:
                self.log(f"_find_mysql: encontrado en PATH -> {path}")
            except Exception as e:
                pass
            return path

        # 2) Rutas comunes en Windows
        try:
            self.log("_find_mysql: buscando en rutas comunes de instalación")
        except Exception as e:
            pass

        candidates = glob.glob(r"C:\\Program Files\\MySQL\\*\\bin\\mysql.exe")
        candidates = [c for c in candidates if "Workbench" not in c]

        if candidates:
            try:
                self.log(f"_find_mysql: encontrado en ruta común -> {candidates[0]}")
            except Exception as e:
                pass
            return candidates[0]

        # 3) Registro PATH para ayudar al diagnóstico
        try:
            path_env = os.environ.get("PATH", "")
            self.log(f"_find_mysql: PATH env -> {path_env}")
        except Exception as e:
            pass

        raise FileNotFoundError(
            "❌ No se encontró mysql.exe. Asegúrate de que MySQL Server está instalado o que 'mysql' está en PATH."
        )

    # ----------------------------
    # BUSCAR mysqldump.exe
    # ----------------------------
    def _find_mysqldump(self) -> str:
        """
        Busca mysqldump.exe automáticamente.
        """

        # 1) PATH
        try:
            self.log("_find_mysqldump: buscando 'mysqldump' en PATH")
        except Exception as e:
            pass

        path = shutil.which("mysqldump")
        if path:
            try:
                self.log(f"_find_mysqldump: encontrado en PATH -> {path}")
            except Exception as e:
                pass
            return path

        # 2) Rutas comunes
        try:
            self.log("_find_mysqldump: buscando en rutas comunes de instalación")
        except Exception as e:
            pass

        candidates = glob.glob(r"C:\\Program Files\\MySQL\\*\\bin\\mysqldump.exe")
        candidates = [c for c in candidates if "Workbench" not in c]

        if candidates:
            try:
                self.log(f"_find_mysqldump: encontrado en ruta común -> {candidates[0]}")
            except Exception as e:
                pass
            return candidates[0]

        try:
            self.log(f"_find_mysqldump: PATH env -> {os.environ.get('PATH', '')}")
        except Exception as e:
            pass

        raise FileNotFoundError(
            "❌ No se encontró mysqldump.exe. Instala MySQL Server o agrega mysqldump al PATH."
        )

    # ----------------------------
    # VALIDAR CONEXIÓN
    # ----------------------------
    def validate_connection(self) -> bool:
        """
        Valida la conexión ejecutando "SELECT 1" contra MySQL.
        """

        cmd = [
            self.mysql_path,
            "-h", self.host,
            "-P", str(self.port),
            "-u", self.user,
            f"-p{self.password}",
            "-e", "SELECT 1;"
        ]

        self.log(f"Validando conexión MySQL con: {' '.join(cmd)}")
        if self.verbose:
            try:
                self.log(f"ENV PATH (truncado): {os.environ.get('PATH', '')[:1000]}")
            except Exception:
                pass
        try:
            # Información adicional para diagnóstico
            self.log(f"validate_connection: mysql_path exists? {os.path.exists(self.mysql_path) if self.mysql_path else False}")
            try:
                self.log(f"validate_connection: mysql_path is executable? {os.access(self.mysql_path, os.X_OK) if self.mysql_path else False}")
            except Exception:
                pass

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.log(f"validate_connection: returncode={result.returncode}")
            if result.stdout:
                # sólo incluir STDOUT si capture_output está activo o verbose
                if self.capture_output or self.verbose:
                    self.log(f"validate_connection STDOUT:\n{result.stdout}")
            if result.stderr:
                self.log(f"validate_connection STDERR:\n{result.stderr}")

            if result.returncode == 0:
                self.log("✔️ Conexión MySQL validada correctamente.")
                return True

            self.log("❌ Error validando conexión MySQL (returncode != 0)")
            return False

        except Exception as e:
            tb = traceback.format_exc()
            if self.traceback_on_error:
                self.log(f"❌ Excepción validando conexión: {e}\n{tb}")
            else:
                self.log(f"❌ Excepción validando conexión: {e}")
            return False

    # ----------------------------
    # DUMP PRINCIPAL
    # ----------------------------
    def dump_database(self, output_path: str):
        """
        Realiza un backup usando mysqldump y registra logs.
        """

        if not output_path.endswith(".sql"):
            output_path += ".sql"

        cmd = [
            self.mysqldump_path,
            "-h", self.host,
            "-P", str(self.port),
            "-u", self.user,
            f"-p{self.password}",
            "--databases", self.database
        ]

        self.log(f"=== INICIANDO BACKUP MYSQL ({self.database}) ===")
        self.log(f"Comando ejecutado: {' '.join(cmd)}")
        self.log(f"mysqldump_path exists? {os.path.exists(self.mysqldump_path) if self.mysqldump_path else False}")
        try:
            self.log(f"mysqldump is executable? {os.access(self.mysqldump_path, os.X_OK) if self.mysqldump_path else False}")
        except Exception:
            pass
        self.log(f"Archivo destino: {output_path}")
        try:
            self.log(f"cwd: {os.getcwd()}")
            self.log(f"output dir exists? {os.path.exists(os.path.dirname(output_path))}")
        except Exception:
            pass

        try:
            if self.capture_output:
                # Capturar stdout para poder loguearlo y luego escribirlo al archivo
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                # Escribir stdout en el archivo destino
                try:
                    with open(output_path, "w", encoding="utf-8") as outfile:
                        outfile.write(process.stdout or "")
                except Exception as e:
                    tb = traceback.format_exc()
                    if self.traceback_on_error:
                        self.log(f"❌ Error escribiendo archivo de salida: {e}\n{tb}")
                    else:
                        self.log(f"❌ Error escribiendo archivo de salida: {e}")
                    raise
            else:
                with open(output_path, "w", encoding="utf-8") as outfile:
                    process = subprocess.run(
                        cmd,
                        stdout=outfile,
                        stderr=subprocess.PIPE,
                        text=True
                    )

        except Exception as e:
            tb = traceback.format_exc()
            if self.traceback_on_error:
                self.log(f"❌ Error ejecutando mysqldump: {e}\n{tb}")
            else:
                self.log(f"❌ Error ejecutando mysqldump: {e}")
            raise

        # Si capture_output está activo podemos loguear el stdout completo
        if getattr(process, "stdout", None) and (self.capture_output or self.verbose):
            try:
                self.log(f"STDOUT:\n{process.stdout}")
            except Exception:
                pass

        if process.stderr:
            self.log(f"STDERR:\n{process.stderr}")

        if process.returncode != 0:
            self.log(f"❌ ERROR: mysqldump terminó con código {process.returncode}")
            raise Exception(f"mysqldump error:\n{process.stderr}")

        self.log(f"✔️ Backup MySQL completado: {output_path}")
        self.log(f"=== FIN BACKUP MYSQL ({self.database}) ===\n")

        return output_path
