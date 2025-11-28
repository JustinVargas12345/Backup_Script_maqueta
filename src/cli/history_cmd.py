import typer
import sqlite3
from pathlib import Path
from datetime import datetime
from utils.logger import setup_logger

app = typer.Typer(help="Maneja el historial de operaciones de backup y restore.")

DB_PATH = Path("data/history.db")
logger = setup_logger()   # Logs a backup_master_log


# -------------------------------------------------------------
# Inicializar SQLite si no existe
# -------------------------------------------------------------
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,         
                db_type TEXT NOT NULL,           
                database_name TEXT,
                file_path TEXT,
                status TEXT NOT NULL,            
                message TEXT,
                timestamp TEXT NOT NULL
            );
        """)
        conn.commit()


# -------------------------------------------------------------
# Insertar en historial (seguro y con logs)
# -------------------------------------------------------------
def add_history(operation: str, db_type: str, database_name: str,
                file_path: str, status: str, message: str):

    init_db()

    entry_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO history (operation, db_type, database_name, file_path, status, message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (operation, db_type, database_name, file_path, status, message, entry_timestamp)
            )
            conn.commit()

        logger.info(f"[HISTORY] Registro añadido: {operation} - {db_type} - {database_name} ({status})")

    except Exception as e:
        logger.error(f"[HISTORY ERROR] No se pudo insertar historial: {e}")


# -------------------------------------------------------------
# COMMAND: mostrar historial
# -------------------------------------------------------------
@app.command("show")
def show_history(
        limit: int = typer.Option(20, help="Cantidad de registros a mostrar."),
        op: str = typer.Option(None, help="Filtrar por operación: backup | restore")
):
    """
    Muestra el historial de operaciones realizadas.
    """

    valid_ops = {"backup", "restore"}

    if op and op not in valid_ops:
        typer.secho("❌ Operación inválida. Usa: backup | restore", fg=typer.colors.RED)
        raise typer.Exit()

    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        if op:
            cursor.execute(
                "SELECT * FROM history WHERE operation = ? ORDER BY id DESC LIMIT ?",
                (op, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?",
                (limit,)
            )

        rows = cursor.fetchall()

    if not rows:
        typer.secho("⚠ No hay registros en el historial.", fg=typer.colors.YELLOW)
        return

    typer.secho(f"\nMostrando últimos {len(rows)} registros:\n", fg=typer.colors.CYAN)

    for r in rows:
        typer.echo(
            f"""
ID:          {r[0]}
Operación:   {r[1]}
DB Type:     {r[2]}
Base:        {r[3]}
Archivo:     {r[4]}
Estado:      {r[5]}
Mensaje:     {r[6]}
Fecha:       {r[7]}
----------------------------------------------
"""
        )


# -------------------------------------------------------------
# COMMAND: ver detalle de un registro por ID
# -------------------------------------------------------------
@app.command("get")
def get_entry(record_id: int):
    """
    Muestra una entrada específica del historial por ID.
    """

    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history WHERE id = ?", (record_id,))
        row = cursor.fetchone()

    if not row:
        typer.secho("❌ ID no encontrado.", fg=typer.colors.RED)
        return

    typer.secho(
        f"""
ID:             {row[0]}
Operación:      {row[1]}
DB Type:        {row[2]}
Base de datos:  {row[3]}
Archivo:        {row[4]}
Estado:         {row[5]}
Mensaje:        {row[6]}
Fecha:          {row[7]}
""",
        fg=typer.colors.GREEN
    )


# -------------------------------------------------------------
# COMMAND: limpiar todo el historial
# -------------------------------------------------------------
@app.command("clear")
def clear_history(confirm: bool = typer.Option(False, "--yes", "-y", help="Confirmar limpieza total.")):
    """
    Elimina todo el historial.
    """

    if not confirm:
        typer.secho("Debe confirmar: backup-cli history clear --yes", fg=typer.colors.RED)
        raise typer.Exit()

    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history;")
        # Reiniciar autoincremento
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='history';")
        conn.commit()

    logger.warning("[HISTORY] Historial completamente limpiado.")

    typer.secho("✔ Historial limpiado.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# COMMAND: borrar entrada específica
# -------------------------------------------------------------
@app.command("delete")
def delete_entry(record_id: int):
    """
    Elimina una entrada específica del historial.
    """

    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE id = ?", (record_id,))
        conn.commit()

    logger.info(f"[HISTORY] Entrada {record_id} eliminada.")

    typer.secho(f"✔ Entrada {record_id} eliminada.", fg=typer.colors.GREEN)
