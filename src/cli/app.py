import typer

# Importar los subcomandos CORRECTAMENTE
from cli.backup_cmd import app as backup_app
from cli.restore_cmd import app as restore_app
from cli.config_cmd import app as config_app
from cli.history_cmd import app as history_app
from cli.utils_cmd import app as utils_app


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
