import typer

from cli.backup_cmd import app as backup_app
from cli.restore_cmd import app as restore_app
from cli.config_cmd import app as config_app
from cli.history_cmd import app as history_app
from cli.utils_cmd import app as utils_app


def create_app() -> typer.Typer:
    """
    Crea la aplicación principal de Typer y registra todos los subcomandos.
    """
    app = typer.Typer(
        help="Backup Manager CLI: herramienta para crear, restaurar y administrar backups de múltiples bases de datos."
    )

    # Registrar subcomandos separados en módulos
    app.add_typer(backup_app, name="backup", help="Crear backups de bases de datos")
    app.add_typer(restore_app, name="restore", help="Restaurar bases de datos")
    app.add_typer(config_app, name="config", help="Configurar almacenamiento local, remoto y opciones de backup")
    app.add_typer(history_app, name="history", help="Ver historial de backups realizados")
    app.add_typer(utils_app, name="utils", help="Comandos utilitarios")

    return app


app = create_app()


def main():
    """
    Punto de entrada principal para ejecutar el CLI.
    """
    app()


if __name__ == "__main__":
    main()
