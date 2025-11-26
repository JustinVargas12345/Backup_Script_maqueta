import subprocess
import pyodbc
from pathlib import Path


def get_sqlserver_backup_dir(server, user, password, port=None):
    """
    Detecta la carpeta oficial de backups de SQL Server.
    Intenta primero mediante pyodbc usando xp_instance_regread.
    Devuelve un Path o None.
    """

    # Construcción del SERVER para pyodbc
    if port:
        server_str = f"{server},{port}"
    else:
        server_str = server  # Puede incluir SQLEXPRESS o instancia nombrada

    query = """
    DECLARE @dir NVARCHAR(4000);
    EXEC master.dbo.xp_instance_regread
        N'HKEY_LOCAL_MACHINE',
        N'SOFTWARE\\Microsoft\\MSSQLServer\\MSSQLServer',
        N'BackupDirectory',
        @dir OUTPUT;

    SELECT @dir AS BackupDirectory;
    """

    # -------------------------------
    # INTENTO A: Obtener ruta por ODBC
    # -------------------------------
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server_str};UID={user};PWD={password};",
            timeout=4
        )

        cur = conn.cursor()
        cur.execute(query)
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row and row[0]:
            path = Path(str(row[0])).resolve()
            return path

    except Exception as e:
        print(f"[WARN] No se pudo obtener ruta por ODBC: {e}")

    # -------------------------------
    # INTENTO B: Valor por defecto de instancias SQL
    # -------------------------------
    fallback_paths = [
        r"C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL14.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL13.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL12.SQLEXPRESS\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL15.MSSQLSERVER\MSSQL\Backup",
        r"C:\Program Files\Microsoft SQL Server\MSSQL14.MSSQLSERVER\MSSQL\Backup",
    ]

    for p in fallback_paths:
        p = Path(p)
        if p.exists():
            print(f"[INFO] Usando carpeta fallback detectada: {p}")
            return p

    # -------------------------------
    # INTENTO C: Comando sqlcmd (si está disponible)
    # -------------------------------
    try:
        cmd = [
            "sqlcmd",
            "-S", server_str,
            "-U", user,
            "-P", password,
            "-Q", query
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)

        if r.returncode == 0 and ":\\" in r.stdout:
            for line in r.stdout.splitlines():
                if ":\\" in line:
                    path = Path(line.strip()).resolve()
                    return path

    except Exception:
        pass

    print("[ERROR] No fue posible detectar la carpeta de backup de SQL Server.")
    return None
