import typer
import sqlite3
from pathlib import Path
from datetime import datetime

app = typer.Typer(help="Maneja el historial de operaciones de backup y restore.")

DB_PATH = Path("data/history.db")


# -------------------------------------------------------------
# Inicializar SQLite si no existe
# -------------------------------------------------------------
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,         -- backup | restore
            db_type TEXT NOT NULL,           -- postgres, mysql, mongo, sqlite
            database_name TEXT,
            file_path TEXT,
            status TEXT NOT NULL,            -- success | error
            message TEXT,
            timestamp TEXT NOT NULL
        );
    """)

    conn.commit()
    conn.close()


def add_history(operation: str, db_type: str, database_name: str,
                file_path: str, status: str, message: str):

    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO history (operation, db_type, database_name, file_path, status, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            operation,
            db_type,
            database_name,
            file_path,
            status,
            message,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()


# -------------------------------------------------------------
# COMMAND: mostrar historial
# -------------------------------------------------------------
@app.command("show")
def show_history(limit: int = typer.Option(20, help="Cantidad de registros a mostrar."),
                 op: str = typer.Option(None, help="Filtrar por tipo de operación: backup | restore")):
    """
    Muestra el historial de operaciones realizadas.
    """

    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if op:
        cursor.execute("SELECT * FROM history WHERE operation = ? ORDER BY id DESC LIMIT ?", (op, limit))
    else:
        cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        typer.secho("No hay registros en el historial.", fg=typer.colors.YELLOW)
        return

    for r in rows:
        typer.secho(f"""
ID: {r[0]}
Operación: {r[1]}
Tipo DB: {r[2]}
Base: {r[3]}
Archivo: {r[4]}
Estado: {r[5]}
Mensaje: {r[6]}
Fecha: {r[7]}
----------------------------------------------
""", fg=typer.colors.CYAN)


# -------------------------------------------------------------
# COMMAND: ver detalle de un registro por ID
# -------------------------------------------------------------
@app.command("get")
def get_entry(record_id: int):
    """
    Muestra una entrada específica del historial por ID.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM history WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        typer.secho("ID no encontrado.", fg=typer.colors.RED)
        return

    typer.secho(f"""
ID: {row[0]}
Operación: {row[1]}
Tipo DB: {row[2]}
Base de datos: {row[3]}
Archivo: {row[4]}
Estado: {row[5]}
Mensaje: {row[6]}
Fecha: {row[7]}
""", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# COMMAND: limpiar todo
# -------------------------------------------------------------
@app.command("clear")
def clear_history(confirm: bool = typer.Option(False, "--yes", "-y", help="Confirmar limpieza total.")):
    """
    Elimina todo el historial.
    """

    if not confirm:
        typer.secho("Debe confirmar: backup-cli history clear --yes", fg=typer.colors.RED)
        return

    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()

    typer.secho("✔ Historial completamente limpiado.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# COMMAND: borrar entrada por ID
# -------------------------------------------------------------
@app.command("delete")
def delete_entry(record_id: int):
    """
    Elimina una entrada específica del historial.
    """

    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

    typer.secho(f"✔ Entrada {record_id} eliminada.", fg=typer.colors.GREEN)
