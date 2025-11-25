import typer
from .backup_cmd import backup_app
from .restore_cmd import restore_app
from .config_cmd import config_app
from .history_cmd import history_app
from .utils_cmd import utils_app

app = typer.Typer(help="Herramienta CLI para realizar backups y restauraciones de bases de datos.")

# Registrar subcomandos
app.add_typer(backup_app, name="backup", help="Operaciones de respaldo")
app.add_typer(restore_app, name="restore", help="Operaciones de restauración")
app.add_typer(config_app, name="config", help="Configuraciones del sistema")
app.add_typer(history_app, name="history", help="Ver historial de backups")
app.add_typer(utils_app, name="utils", help="Utilidades adicionales")


def main():
    app()

if __name__ == "__main__":
    main()
