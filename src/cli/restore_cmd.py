import typer
from pathlib import Path
import shutil
import tempfile
import tarfile
import zipfile
import subprocess
import os
from typing import Optional

from utils.hash_utils import calculate_sha256
from utils.logger import setup_logger
from utils.history_manager import HistoryManager
from utils.backup_finder import BackupFinder

# helper local para registrar en el historial
def add_history(operation: str, db_type: str, database_name: str, file_path: str, status: str, message: str = None, file_hash: str = None, cloud_url: str = None):
    hm = HistoryManager("backup_history.json")
    try:
        hm.add_entry(
            operation=operation,
            db_type=db_type,
            database=database_name,
            file_path=file_path,
            hash=file_hash,
            status=status,
            message=message,
            cloud_url=cloud_url,
        )
    except Exception:
        logger.exception("Error registrando el historial")

from db_connectors.postgres_connector import PostgresConnector
from db_connectors.mysql_connector import MySQLConnector
from db_connectors.mongo_connector import MongoConnector
from db_connectors.sqlserver_connector import SQLServerConnector
from utils.bin_checker import check_binaries, suggest_install_instructions, REQUIRED_BINARIES_BY_OP, find_binaries


app = typer.Typer(help="Comandos para restauración de bases de datos.")
logger = setup_logger()


def get_binary_path(binary_name: str, db_type: str) -> str:
    """
    Obtiene la ruta completa de un binario. Si no está en PATH, intenta encontrarlo.
    Lanza excepción si no se encuentra.
    """
    paths = find_binaries([binary_name])
    if paths.get(binary_name):
        found_path = paths[binary_name]
        logger.info(f"Binary found: {binary_name} → {found_path}")
        return found_path
    
    error_msg = (
        f"No se encontró '{binary_name}' necesario para restaurar {db_type}. "
        f"Instala PostgreSQL, MySQL o MongoDB tools según corresponda."
    )
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)




def find_restore_target(folder: Path) -> Path:
    """
    Busca dentro de una carpeta el archivo/carpeta restaurable real.
    Para SQL: archivos (.sql, .dump, .bson, .json)
    Para MongoDB: carpeta con los dumps
    
    También maneja el formato especial donde un archivo .dump contiene:
        TYPE: MONGO_DUMP_DIRECTORY
        PATH: <ruta_relativa_o_absoluta>
    """
    logger.info(f"Buscando target en: {folder}")
    logger.info(f"Contenido: {list(folder.iterdir())}")
    
    candidates = []
    dump_markers = []

    # Primera pasada: buscar archivos .dump que puedan ser marcadores
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() == ".dump":
            try:
                with path.open("r") as f:
                    content = f.read().strip()
                
                # Verificar formato especial MONGO_DUMP_DIRECTORY
                if "MONGO_DUMP_DIRECTORY" in content and "PATH:" in content:
                    # Extraer la ruta
                    for line in content.split("\n"):
                        if line.startswith("PATH:"):
                            dir_str = line.split(":", 1)[1].strip()
                            # Convertir a Path absoluta si es relativa
                            dir_path = Path(dir_str)
                            if not dir_path.is_absolute():
                                # Si es relativa, buscar desde el punto de extracción
                                # o desde el directorio actual
                                dir_path_from_folder = folder / dir_str
                                dir_path_from_cwd = Path(dir_str)
                                
                                if dir_path_from_folder.exists():
                                    dir_path = dir_path_from_folder
                                elif dir_path_from_cwd.exists():
                                    dir_path = dir_path_from_cwd
                            
                            if dir_path.exists() and dir_path.is_dir():
                                logger.info(f"Encontrado marcador MONGO_DUMP_DIRECTORY: {dir_path}")
                                dump_markers.append(dir_path)
                            else:
                                logger.warning(f"Ruta en marcador no existe: {dir_path}")
            except Exception as e:
                logger.debug(f"No se pudo leer {path} como marcador: {e}")
    
    # Si encontramos marcadores válidos, usarlos
    if dump_markers:
        logger.info(f"Usando ruta desde marcador: {dump_markers[0]}")
        return dump_markers[0]

    # Segunda pasada: buscar archivos/carpetas restaurables normales
    for path in folder.rglob("*"):
        if path.is_file():
            if path.suffix.lower() in [".sql", ".bson", ".json"]:
                candidates.append(path)
        elif path.is_dir() and not path.name.startswith("."):
            # Verificar si la carpeta contiene archivos BSON (típico de mongodump)
            bson_files = list(path.glob("**/*.bson"))
            if bson_files:
                candidates.append(path)

    if not candidates:
        # Si no encontramos nada dentro, quizás la carpeta raíz es la que contiene los datos
        bson_files = list(folder.glob("**/*.bson"))
        if bson_files:
            logger.info(f"Usando carpeta raíz (contiene .bson): {folder}")
            return folder
        
        raise Exception(
            f"No se encontró ningún archivo/carpeta restaurable en {folder}. "
            f"Contenidos: {list(folder.iterdir())}"
        )

    # Prioridad: carpetas MongoDB primero, luego archivos
    dirs_with_bson = [c for c in candidates if c.is_dir()]
    files = [c for c in candidates if c.is_file()]
    
    if dirs_with_bson:
        logger.info(f"Usando carpeta MongoDB: {dirs_with_bson[0]}")
        return dirs_with_bson[0]
    
    if files:
        for ext in [".sql", ".bson", ".json"]:
            for c in files:
                if c.suffix.lower() == ext:
                    logger.info(f"Usando archivo: {c}")
                    return c
        logger.info(f"Usando archivo (default): {files[0]}")
        return files[0]
    
    logger.info(f"Usando candidato: {candidates[0]}")
    return candidates[0]


def detect_db_type(path: Path) -> str:
    """Detección básica de tipo según extensión."""
    ext = path.suffix.lower()

    if ext in [".zip", ".gz", ".tgz", ".tar"]:
        return "sql"

    if ext == ".sql":
        return "sql"

    if ext in [".dump", ".backup"]:
        return "postgres"

    if ext in [".bson", ".json"]:
        return "mongo"

    return "unknown"


def extract_safe(zip_ref, dest):
    """Extracción segura de ZIP/TAR para evitar ZIP-SLIP."""
    for member in zip_ref.namelist():
        extracted = dest / member
        if not extracted.resolve().startswith(dest.resolve()):
            raise Exception("Ataque ZIP-SLIP detectado.")
    zip_ref.extractall(dest)


def extract_if_needed(backup_path: Path) -> tuple:
    """
    Si `backup_path` es un comprimido, lo extrae en un tmp dir y devuelve
    (ruta_real_para_restaurar, tmp_dir). Si no, devuelve (backup_path, None).
    """
    suffix_lower = backup_path.suffix.lower()
    name_lower = backup_path.name.lower()
    
    if suffix_lower == ".zip":
        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(backup_path, "r") as z:
            extract_safe(z, tmp)
        return find_restore_target(tmp), tmp

    # Manejo especial para .tar.gz y .tgz
    if name_lower.endswith(".tar.gz") or suffix_lower == ".tgz" or suffix_lower == ".gz":
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(backup_path, "r:gz") as t:
            t.extractall(tmp)
        return find_restore_target(tmp), tmp

    if suffix_lower == ".tar":
        tmp = Path(tempfile.mkdtemp())
        with tarfile.open(backup_path, "r") as t:
            t.extractall(tmp)
        return find_restore_target(tmp), tmp

    return backup_path, None


# =====================================================================
# PostgreSQL Restore
# =====================================================================
def restore_postgres(conn: PostgresConnector, dump_path: Path, db_name: str):
    typer.echo(f"Restaurando PostgreSQL → {db_name}...")

    ext = dump_path.suffix.lower()
    env = os.environ.copy()
    env["PGPASSWORD"] = conn.password

    # Construir comando como string con quoting parecido al conector (Windows-friendly)
    if ext == ".sql":
        psql_path = get_binary_path("psql", "postgres")
        cmd_str = (
            f'"{psql_path}" '
            f'-h "{conn.host}" -p "{conn.port}" '
            f'-U "{conn.user}" -d "{db_name}" -f "{str(dump_path)}"'
        )
    else:
        pg_restore_path = get_binary_path("pg_restore", "postgres")
        cmd_str = (
            f'"{pg_restore_path}" '
            f'-h "{conn.host}" -p "{conn.port}" '
            f'-U "{conn.user}" -d "{db_name}" "{str(dump_path)}"'
        )

    logger.info(f"Ejecutando comando PostgreSQL (shell): {cmd_str}")

    try:
        process = subprocess.run(
            cmd_str,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        if process.stdout:
            logger.info(f"psql/pg_restore stdout: {process.stdout}")

        if process.returncode != 0:
            logger.error(f"psql/pg_restore stderr: {process.stderr}")
            raise RuntimeError(f"pg_restore falló: {process.stderr}")

    except Exception as e:
        # Normalizar excepción para el flujo anterior
        logger.exception("Error ejecutando restore Postgres")
        raise
    
    typer.secho("✔ PostgreSQL restaurado.", fg=typer.colors.GREEN)


# =====================================================================
# MySQL Restore
# =====================================================================
def restore_mysql(conn: MySQLConnector, dump_path: Path, db_name: str):
    typer.echo(f"Restaurando MySQL → {db_name}...")

    if dump_path.is_dir():
        raise ValueError("El backup MySQL debe ser archivo .sql, no carpeta.")

    # Usar la ruta detectada por el conector (más confiable)
    try:
        mysql_path = conn.mysql_path
    except Exception:
        mysql_path = get_binary_path("mysql", "mysql")

    restore_cmd = [
        mysql_path,
        "-h", str(conn.host),
        "-P", str(conn.port),
        "-u", str(conn.user),
        f"-p{conn.password}",
        db_name,
    ]

    logger.info(f"Ejecutando comando MySQL: {restore_cmd[0]} (con credenciales ocultas)")

    try:
        # Abrir el archivo como texto para que subprocess.text funcione bien
        with dump_path.open("r", encoding="utf-8", errors="ignore") as infile:
            process = subprocess.run(
                restore_cmd,
                stdin=infile,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        if process.stdout:
            logger.info(f"mysql stdout: {process.stdout}")
        if process.stderr:
            logger.error(f"mysql stderr: {process.stderr}")

        if process.returncode != 0:
            raise RuntimeError(f"mysql falló: {process.stderr}")

    except Exception as e:
        logger.exception("Error ejecutando restore MySQL")
        raise

    typer.secho("✔ MySQL restaurado.", fg=typer.colors.GREEN)


# =====================================================================
# MongoDB Restore
# =====================================================================
def restore_mongo(conn: MongoConnector, dump_path: Path, db_name: str):
    typer.echo(f"Restaurando MongoDB → {db_name}...")
    logger.info(f"restore_mongo called with dump_path={dump_path}, db_name={db_name}")

    # Verificar que sea un directorio
    if not dump_path.is_dir():
        # Si es un archivo .dump, extraer la ruta del marcador
        if dump_path.is_file() and dump_path.suffix.lower() == ".dump":
            try:
                with dump_path.open("r") as f:
                    content = f.read().strip()
                
                for line in content.split("\n"):
                    if line.startswith("PATH:"):
                        dir_str = line.split(":", 1)[1].strip()
                        dump_path = Path(dir_str)
                        if dump_path.is_absolute() or dump_path.exists():
                            break
                        else:
                            # Intentar relativo desde cwd
                            dump_path = Path(dir_str).resolve()
            except Exception as e:
                logger.error(f"Error extrayendo ruta del marcador .dump: {e}")
        
        # Verificar nuevamente
        if not dump_path.is_dir():
            raise ValueError(
                f"El backup Mongo debe ser una carpeta generada por mongodump, "
                f"pero recibimos: {dump_path} (existe: {dump_path.exists()})"
            )
    
    # Verificar que existan archivos BSON
    bson_files = list(dump_path.glob("**/*.bson"))
    if not bson_files:
        raise ValueError(
            f"No se encontraron archivos .bson dentro de {dump_path}. "
            f"Verifica que sea un backup válido de mongodump. "
            f"Contenido: {list(dump_path.iterdir())}"
        )

    mongorestore_path = get_binary_path("mongorestore", "mongo")
    # Construir lista de intentos siguiendo la lógica del MongoConnector.validate_connection
    attempts = []

    # 1) Sin autenticación
    attempts.append([
        mongorestore_path,
        f"--host={conn.host}",
        f"--port={conn.port}",
        f"--db={db_name}",
        str(dump_path)
    ])

    # 2) Con usuario/contraseña y auth DB
    if conn.user and conn.password:
        attempts.append([
            mongorestore_path,
            f"--host={conn.host}",
            f"--port={conn.port}",
            f"--username={conn.user}",
            f"--password={conn.password}",
            f"--authenticationDatabase={conn.auth_db}",
            f"--db={db_name}",
            str(dump_path)
        ])

        # 3) Intentar explícitamente con SCRAM-SHA-256
        attempts.append([
            mongorestore_path,
            f"--host={conn.host}",
            f"--port={conn.port}",
            f"--username={conn.user}",
            f"--password={conn.password}",
            f"--authenticationDatabase={conn.auth_db}",
            "--authenticationMechanism=SCRAM-SHA-256",
            f"--db={db_name}",
            str(dump_path)
        ])

        # 4) Intentar explícitamente con SCRAM-SHA-1
        attempts.append([
            mongorestore_path,
            f"--host={conn.host}",
            f"--port={conn.port}",
            f"--username={conn.user}",
            f"--password={conn.password}",
            f"--authenticationDatabase={conn.auth_db}",
            "--authenticationMechanism=SCRAM-SHA-1",
            f"--db={db_name}",
            str(dump_path)
        ])

    # 5) Si el host parece un dominio, intentar URI + SRV
    if "." in conn.host:
        if conn.user and conn.password:
            uri = f"mongodb+srv://{conn.user}:{conn.password}@{conn.host}/{conn.auth_db}?retryWrites=true&w=majority"
        else:
            uri = f"mongodb+srv://{conn.host}/{conn.auth_db}?retryWrites=true&w=majority"
        attempts.append([mongorestore_path, f"--uri={uri}", "--db=" + db_name, str(dump_path)])

    logger.info(f"Restaurando desde: {dump_path}")
    logger.info(f"Archivos .bson encontrados: {len(bson_files)}")

    last_errs = []
    # Ejecutar intentos en orden hasta que uno funcione
    for idx, cmd in enumerate(attempts, start=1):
        try:
            logger.info(f"Intento {idx}/{len(attempts)}: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                logger.info(f"mongorestore stdout: {result.stdout}")
            typer.secho(f"✓ mongorestore exitoso (intent {idx})", fg=typer.colors.GREEN)
            break
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"mongorestore stderr (intent {idx}): {error_msg}")
            logger.error(f"mongorestore stdout (intent {idx}): {e.stdout if e.stdout else '(vacío)'}")
            last_errs.append((cmd, error_msg))
    else:
        # Todos los intentos fallaron
        combined = "\n---\n".join([f"CMD: {' '.join(c)}\nERR: {m}" for c, m in last_errs])
        raise RuntimeError(f"mongorestore falló en todos los intentos:\n{combined}")
    
    typer.secho("✔ MongoDB restaurado.", fg=typer.colors.GREEN)


# =====================================================================
# SQL Server Restore
# =====================================================================
def restore_sqlserver(conn: SQLServerConnector, dump_path: Path, db_name: str):
    typer.echo(f"Restaurando SQL Server → {db_name}...")
    
    # SQL Server soporta restauración desde archivos .bak o .trn
    if dump_path.is_dir():
        raise ValueError("El backup SQL Server debe ser archivo .bak o .trn, no carpeta.")
    
    sqlcmd_path = get_binary_path("sqlcmd", "sqlserver")
    
    # Usar sqlcmd para ejecutar RESTORE DATABASE
    restore_cmd = f"""
    RESTORE DATABASE [{db_name}] 
    FROM DISK = N'{dump_path}' 
    WITH FILE = 1, NOUNLOAD, REPLACE, STATS = 10;
    """
    
    cmd = [
        sqlcmd_path,
        f"-S{conn.host}",
        f"-U{conn.user}",
        f"-P{conn.password}",
        "-Q", restore_cmd
    ]
    
    logger.info(f"Ejecutando comando SQL Server: {cmd[0]} (con credenciales)")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.info(f"sqlcmd stdout: {result.stdout}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"sqlcmd stderr: {error_msg}")
        logger.error(f"sqlcmd stdout: {e.stdout if e.stdout else '(vacío)'}")
        raise RuntimeError(f"sqlcmd falló: {error_msg}")
    
    typer.secho("✔ SQL Server restaurado.", fg=typer.colors.GREEN)


# =====================================================================
# Comando principal: restore
# Soporta dos modos:
#   1. Manual: especificar archivo backup_file
#   2. Automático: especificar dbtype + database, busca el último backup
# =====================================================================
@app.command("run")
def restore_database(
    dbtype: str = typer.Option(..., help="postgres | mysql | mongo | sqlserver"),
    database: str = typer.Option(..., help="Nombre de la base de datos destino."),
    host: str = typer.Option("localhost", help="Host del servidor."),
    port: Optional[int] = typer.Option(None, help="Puerto (default: según tipo DB)."),
    user: str = typer.Option(..., help="Usuario."),
    password: str = typer.Option(..., help="Contraseña."),
    backup_file: Optional[str] = typer.Option(None, help="(Opcional) Ruta del archivo backup. Si no se especifica, busca el último automáticamente."),
    verify_hash: bool = typer.Option(False, help="Verificar SHA256 del backup."),
    skip_binary_check: bool = typer.Option(False, help="Omitir verificación de binarios."),
    skip_connection_check: bool = typer.Option(False, help="Omitir validación de conexión al servidor."),
):
    """
    Restaura una base de datos desde un backup.
    
    Modo 1 - Automático (recomendado):
        python src/cli.py restore run --dbtype postgres --database mydb --user postgres --password pass
        → Busca el último backup de postgres en backups/ o registrado en historial
    
    Modo 2 - Manual:
        python src/cli.py restore run --dbtype postgres --database mydb --backup-file backups/postgres_mydb_*.dump --user postgres --password pass
        → Restaura el archivo especificado
    """
    
    logger.info(f"=== Iniciando restauración: dbtype={dbtype}, database={database}, host={host} ===")
    
    # Si no se especifica archivo, buscar el último backup automáticamente
    if not backup_file:
        typer.echo(f"🔍 Buscando último backup de {dbtype}...")
        backup_path = BackupFinder.find_by_history(dbtype, database)
        
        if not backup_path:
            backup_path = BackupFinder.find_latest_backup(dbtype, database)
        
        if not backup_path:
            typer.secho(f"❌ No se encontró backup para {dbtype}/{database}", fg=typer.colors.RED)
            logger.error(f"No backup found for {dbtype}/{database}")
            raise typer.Exit(code=1)
        
        typer.secho(f"✓ Encontrado: {backup_path}", fg=typer.colors.GREEN)
        logger.info(f"Backup found: {backup_path}")
    else:
        backup_path = Path(backup_file)
    
    if not backup_path.exists():
        typer.secho(f"❌ El archivo de backup no existe: {backup_path}", fg=typer.colors.RED)
        logger.error(f"Backup file not found: {backup_path}")
        raise typer.Exit(code=1)
    
    # Hash opcional
    file_hash = None
    if verify_hash:
        typer.echo("📊 Calculando hash SHA256...")
        try:
            file_hash = calculate_sha256(backup_path)
            typer.secho(f"SHA256: {file_hash}", fg=typer.colors.BLUE)
            logger.info(f"SHA256: {file_hash}")
        except Exception as e:
            typer.secho(f"⚠ No se pudo calcular hash: {e}", fg=typer.colors.YELLOW)
    
    # Extraer si está comprimido
    try:
        final_path, temp_dir = extract_if_needed(backup_path)
    except Exception as e:
        typer.secho(f"❌ Error extrayendo archivo: {e}", fg=typer.colors.RED)
        logger.error(f"Extraction error: {e}")
        add_history(
            operation="restore",
            db_type=dbtype,
            database_name=database,
            file_path=str(backup_path),
            status="error",
            message=f"Extraction error: {e}",
            file_hash=file_hash,
        )
        raise typer.Exit(code=1)
    
    # Verificar binarios requeridos (solo advertencia)
    if not skip_binary_check:
        required = REQUIRED_BINARIES_BY_OP.get("restore", {}).get(dbtype, [])
        if required:
            res = check_binaries(required)
            missing = [k for k, v in res.items() if not v]
            if missing:
                typer.secho(f"⚠ Faltan binarios para {dbtype}:", fg=typer.colors.YELLOW)
                for m in missing:
                    typer.echo(f"  - {m}")
                typer.secho("Ejecuta: python src/cli.py utils check-binaries", fg=typer.colors.CYAN)
                typer.secho("Continuando de todos modos...", fg=typer.colors.YELLOW)
                logger.warning(f"Missing binaries for restore: {missing}")
    
    # Configurar puerto según tipo si no se especifica
    if port is None:
        port = {"postgres": 5432, "mysql": 3306, "mongo": 27017, "sqlserver": 1433}.get(dbtype, None)
    
    # Validar conexión al servidor (opcional)
    if not skip_connection_check:
        typer.echo(f"🔗 Validando conexión a {dbtype}://{host}:{port}...")
        try:
            if dbtype == "postgres":
                conn_test = PostgresConnector(host, port, user, password, database)
                if not conn_test.validate_connection():
                    typer.secho(f"❌ No se pudo conectar a PostgreSQL en {host}:{port}", fg=typer.colors.RED)
                    logger.error(f"PostgreSQL connection validation failed")
                    typer.secho("💡 Verifica que:", fg=typer.colors.CYAN)
                    typer.echo(f"  - El servidor PostgreSQL está corriendo")
                    typer.echo(f"  - El host es correcto: {host}")
                    typer.echo(f"  - El puerto es correcto: {port}")
                    typer.echo(f"  - Las credenciales son correctas")
                    typer.echo(f"\n  Puedes saltar esta verificación con: --skip-connection-check")
                    raise typer.Exit(code=1)
                typer.secho("✓ Conexión OK", fg=typer.colors.GREEN)
                
            elif dbtype == "mysql":
                conn_test = MySQLConnector(host, port, user, password, database)
                if not conn_test.validate_connection():
                    typer.secho(f"❌ No se pudo conectar a MySQL en {host}:{port}", fg=typer.colors.RED)
                    logger.error(f"MySQL connection validation failed")
                    raise typer.Exit(code=1)
                typer.secho("✓ Conexión OK", fg=typer.colors.GREEN)
                
            elif dbtype == "mongo":
                conn_test = MongoConnector(host, port, user, password, database)
                if not conn_test.validate_connection():
                    typer.secho(f"❌ No se pudo conectar a MongoDB en {host}:{port}", fg=typer.colors.RED)
                    logger.error(f"MongoDB connection validation failed")
                    raise typer.Exit(code=1)
                typer.secho("✓ Conexión OK", fg=typer.colors.GREEN)
                
            elif dbtype == "sqlserver":
                conn_test = SQLServerConnector(host, port, user, password, database)
                if not conn_test.connection_test():
                    typer.secho(f"❌ No se pudo conectar a SQL Server en {host}:{port}", fg=typer.colors.RED)
                    logger.error(f"SQL Server connection validation failed")
                    raise typer.Exit(code=1)
                typer.secho("✓ Conexión OK", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"⚠ Error validando conexión: {e}", fg=typer.colors.YELLOW)
            logger.warning(f"Connection validation error: {e}")
            typer.secho("Puedes omitir la validación con: --skip-connection-check", fg=typer.colors.CYAN)
    
    # Ejecutar restauración
    try:
        if dbtype == "postgres":
            conn = PostgresConnector(host, port, user, password, database)
            restore_postgres(conn, final_path, database)
            
        elif dbtype == "mysql":
            conn = MySQLConnector(host, port, user, password, database)
            restore_mysql(conn, final_path, database)
            
        elif dbtype == "mongo":
            conn = MongoConnector(host, port, user, password, database)
            restore_mongo(conn, final_path, database)
        
        elif dbtype == "sqlserver":
            conn = SQLServerConnector(host, port, user, password, database)
            restore_sqlserver(conn, final_path, database)
        
        else:
            raise ValueError(f"Tipo de base de datos no soportado: {dbtype}")
        
        typer.secho(f"✅ Restauración completada exitosamente en {database}", fg=typer.colors.GREEN)
        logger.info(f"Restore completed successfully: {database}")
        
        add_history(
            operation="restore",
            db_type=dbtype,
            database_name=database,
            file_path=str(backup_path),
            status="success",
            message="Restauración completada sin errores.",
            file_hash=file_hash,
        )
    
    except Exception as e:
        typer.secho(f"❌ Error durante la restauración: {e}", fg=typer.colors.RED)
        logger.exception(f"Restore failed: {e}")
        
        add_history(
            operation="restore",
            db_type=dbtype,
            database_name=database,
            file_path=str(backup_path),
            status="error",
            message=str(e),
            file_hash=file_hash,
        )
        raise typer.Exit(code=1)
    
    finally:
        # Limpiar carpetas temporales
        if temp_dir is not None:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Temporary directory cleaned")
            except Exception as e:
                logger.warning(f"Could not clean temp dir: {e}")
