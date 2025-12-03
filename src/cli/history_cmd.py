import typer
from pathlib import Path
from utils.logger import setup_logger
from utils.history_manager import HistoryManager

app = typer.Typer(help="Maneja el historial JSON de operaciones de backup y restore.")

logger = setup_logger()

HISTORY_PATH = "backup_history.json"
history = HistoryManager(HISTORY_PATH)


def safe_get(item: dict, key: str, default=""):
    """Devuelve item[key] si existe, de lo contrario default."""
    return item.get(key) if item.get(key) not in [None, "N/A"] else default


@app.command("show")
def show_history(
    limit: int = typer.Option(200, help="Cantidad de registros a mostrar."),
    op: str = typer.Option(None, help="Filtrar por operación: backup | restore")
):
    """
    Muestra el historial completo sin filtrar de manera agresiva.
    """

    rows = history.get_all()

    if not rows:
        typer.secho("⚠ No hay registros en el historial JSON.", fg=typer.colors.YELLOW)
        return

    # Filtrar solo si se especificó `--op`
    valid_ops = {"backup", "restore"}
    if op:
        if op not in valid_ops:
            typer.secho("❌ Operación inválida. Usa: backup | restore", fg=typer.colors.RED)
            raise typer.Exit()
        rows = [r for r in rows if r.get("operation") == op]

    # Orden por timestamp si existe
    rows = sorted(rows, key=lambda x: x.get("timestamp", ""), reverse=True)
    rows = rows[:limit]

    typer.secho(f"\nMostrando {len(rows)} registros:\n", fg=typer.colors.CYAN)

    for r in rows:
        record_id = r.get("id", "")
        operation = r.get("operation", "")
        db_type = r.get("db_type", "")
        database = r.get("database", "")
        file_path_str = r.get("file_path", "")
        status = r.get("status", "")
        message = r.get("message", "")
        timestamp = r.get("timestamp", "")
        cloud_url = r.get("cloud_url", "")
        file_hash = r.get("hash", "")

        file_path = Path(file_path_str) if file_path_str else None
        exists = file_path.exists() if file_path else False
        size = file_path.stat().st_size if exists else 0

        compression = "Sin compresión"
        if exists and file_path.suffix in {".zip", ".gz", ".tar", ".tgz", ".7z"}:
            compression = f"Comprimido ({file_path.suffix})"

        typer.echo(
            f"""
ID:            {record_id}
Operación:     {operation}
DB Type:       {db_type}
Base:          {database}
Archivo:       {file_path_str}
Existe:        {"✔ Sí" if exists else "❌ No"}
Tamaño:        {size / 1024:.2f} KB
Compresión:    {compression}
Hash:          {file_hash}
Estado:        {status}
Mensaje:       {message}
Cloud URL:     {cloud_url}
Fecha:         {timestamp}
----------------------------------------------
"""
        )


# -------------------------------------------------------------
# COMMAND: eliminar entrada
# -------------------------------------------------------------
@app.command("delete")
def delete_entry(record_id: str):
    """
    Elimina una entrada específica del historial JSON.
    """

    rows = history.get_all()
    filtered = [r for r in rows if r.get("id") != record_id]

    if len(filtered) == len(rows):
        typer.secho("❌ ID no encontrado.", fg=typer.colors.RED)
        return

    history._save_history(filtered)
    logger.info(f"[HISTORY] Entrada {record_id} eliminada del JSON.")

    typer.secho(f"✔ Entrada {record_id} eliminada.", fg=typer.colors.GREEN)
