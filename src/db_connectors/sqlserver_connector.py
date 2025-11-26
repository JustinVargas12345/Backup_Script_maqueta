'''
import pyodbc

class SQLServerConnector:
    def __init__(self, server, database, username, password, driver="{ODBC Driver 17 for SQL Server}"):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.conn = None

    def connect(self):
        try:
            conn_str = (
                f"DRIVER={self.driver};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password}"
            )
            self.conn = pyodbc.connect(conn_str, timeout=5)
            print("[OK] Conectado a SQL Server correctamente.")
            return self.conn
        except Exception as e:
            print(f"[ERROR] No se pudo conectar a SQL Server: {e}")
            return None

    def test_query(self):
        """Ejecuta una consulta simple para validar la conexión."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT GETDATE()")
            result = cursor.fetchone()
            return result[0]
        except Exception as e:
            print(f"[ERROR] Error ejecutando test_query: {e}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()
            print("[OK] Conexión SQL Server cerrada.")
'''

import subprocess
from pathlib import Path
import shutil


try:
    import pyodbc
except ImportError:
    pyodbc = None


class SQLServerConnector:
    """
    Conector híbrido para SQL Server con:
    - sqlcmd
    - pyodbc
    Y detección automática de la carpeta oficial de backups.
    """

    def __init__(self, host, port, user, password, database):
        self.host = host              # Puede ser: localhost  ó localhost\SQLEXPRESS
        self.port = port              # Puede ser None si es instancia nombrada
        self.user = user
        self.password = password
        self.database = database

    def has_sqlcmd(self):
        """Retorna True si sqlcmd está disponible en el sistema."""
        return shutil.which("sqlcmd") is not None
    # ===============================================================
    # Construir servidor para ODBC / SQLCMD
    # ===============================================================
    def _build_server_string(self):
        """
        Devuelve la cadena correcta para SQL Server:
            - Si el host contiene una instancia (SQLEXPRESS), NO usar puerto.
            - Si no contiene instancia, usar host,port
        """
        if "\\" in self.host:  
            # Ej: localhost\SQLEXPRESS
            return self.host
        elif self.port:
            return f"{self.host},{self.port}"
        else:
            return self.host

    # ===============================================================
    # Detectar carpeta oficial de BACKUP vía ODBC
    # ===============================================================
    def detect_backup_directory_odbc(self):
        if not pyodbc:
            return None

        server = self._build_server_string()

        query = """
        DECLARE @dir NVARCHAR(4000);
        EXEC master.dbo.xp_instance_regread
            N'HKEY_LOCAL_MACHINE',
            N'SOFTWARE\\Microsoft\\MSSQLServer\\MSSQLServer',
            N'BackupDirectory',
            @dir OUTPUT;
        SELECT @dir AS BackupDirectory;
        """

        try:
            conn = pyodbc.connect(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};UID={self.user};PWD={self.password};",
                timeout=3
            )
            cur = conn.cursor()
            cur.execute(query)
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row and row[0]:
                return Path(str(row[0]))
        except Exception:
            return None

        return None

    # ===============================================================
    # Detectar carpeta de backup vía sqlcmd
    # ===============================================================
    def detect_backup_directory_sqlcmd(self):
        server = self._build_server_string()

        query = """
        DECLARE @dir NVARCHAR(4000);
        EXEC master.dbo.xp_instance_regread
            N'HKEY_LOCAL_MACHINE',
            N'SOFTWARE\\Microsoft\\MSSQLServer\\MSSQLServer',
            N'BackupDirectory',
            @dir OUTPUT;
        SELECT @dir;
        """

        try:
            cmd = [
                "sqlcmd",
                "-S", server,
                "-U", self.user,
                "-P", self.password,
                "-Q", query
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout.splitlines()

            for line in output:
                line = line.strip()
                if ":\\\\" in line or ":\\" in line:
                    return Path(line)

        except Exception:
            return None

        return None

    # ===============================================================
    # Método central de detección
    # ===============================================================
    def get_backup_directory(self) -> Path | None:
        # 1) ODBC (más seguro)
        d1 = self.detect_backup_directory_odbc()
        if d1:
            return d1

        # 2) sqlcmd
        d2 = self.detect_backup_directory_sqlcmd()
        if d2:
            return d2

        return None

    # ===============================================================
    # Tests de conexión
    # ===============================================================
    def _test_sqlcmd(self) -> bool:
        server = self._build_server_string()
        try:
            cmd = [
                "sqlcmd",
                "-S", server,
                "-U", self.user,
                "-P", self.password,
                "-Q", "SELECT 1;"
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return r.returncode == 0
        except FileNotFoundError:
            return False

    def _test_pyodbc(self) -> bool:
        if not pyodbc:
            return False

        server = self._build_server_string()

        try:
            conn = pyodbc.connect(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};UID={self.user};PWD={self.password};"
                f"DATABASE={self.database}",
                timeout=3
            )
            conn.close()
            return True
        except Exception:
            return False

    def connection_test(self):
        if self._test_sqlcmd():
            return "sqlcmd"
        if self._test_pyodbc():
            return "pyodbc"
        return None

    # ===============================================================
    # BACKUPS
    # ===============================================================
    def _backup_with_sqlcmd(self, output_file):
        server = self._build_server_string()

        sql = (
            f"BACKUP DATABASE [{self.database}] "
            f"TO DISK = '{output_file}' WITH INIT, FORMAT;"
        )

        cmd = [
            "sqlcmd",
            "-S", server,
            "-U", self.user,
            "-P", self.password,
            "-Q", sql
        ]

        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"[sqlcmd] error:\n{r.stderr}")

        return output_file

    def _backup_with_pyodbc(self, output_file):
        if not pyodbc:
            raise RuntimeError("pyodbc no está disponible.")

        server = self._build_server_string()

        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};UID={self.user};PWD={self.password};"
            f"DATABASE={self.database}"
        )
        cursor = conn.cursor()

        sql = (
            f"BACKUP DATABASE [{self.database}] "
            f"TO DISK = '{output_file}' WITH INIT, FORMAT;"
        )

        cursor.execute(sql)
        cursor.commit()
        cursor.close()
        conn.close()

        return output_file

    # ===============================================================
    # BACKUP PRINCIPAL
    # ===============================================================
    def create_backup(self, output_path: str | None) -> str:
        """
        Si output_path es None → se usa la carpeta oficial de SQL Server.
        """

        # Si no se especificó ruta → usar backup oficial
        if not output_path:
            backup_dir = self.get_backup_directory()
            if not backup_dir:
                raise RuntimeError(
                    "No se pudo detectar la carpeta oficial de backup "
                    "de SQL Server. Configúrala manualmente."
                )

            backup_dir.mkdir(parents=True, exist_ok=True)
            output_file = backup_dir / f"{self.database}_auto.bak"

        else:
            output_file = Path(output_path)

        method = self.connection_test()

        if not method:
            raise RuntimeError("No se pudo conectar con SQL Server por sqlcmd ni por pyodbc.")

        if method == "sqlcmd":
            return self._backup_with_sqlcmd(str(output_file))

        if method == "pyodbc":
            return self._backup_with_pyodbc(str(output_file))

        raise RuntimeError("Método de backup inesperado.")
