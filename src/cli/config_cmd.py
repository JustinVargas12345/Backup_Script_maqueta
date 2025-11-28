import typer
from pathlib import Path
import toml
from typing import Optional

app = typer.Typer(help="Administración de configuración del sistema de backups.")

CONFIG_PATH = Path("config/config.toml")


# -------------------------------------------------------------
# Estructura base del archivo config.toml
# -------------------------------------------------------------
DEFAULT_CONFIG = {
    "postgres": {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
    },
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "root",
    },
    "mongo": {
        "host": "localhost",
        "port": 27017,
        "user": "",
        "password": "",
    },
    "backup": {
        "output_dir": "backups/",
        "compression": "zip",  # zip | tar | none
    },
    "cloud": {
        "provider": "",        # aws | gcp | azure | ""
        "bucket": "",
        "access_key": "",
        "secret_key": "",
        "region": "",
    }
}


# -------------------------------------------------------------
# Crear archivo config si no existe
# -------------------------------------------------------------
def create_default_config():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        toml.dump(DEFAULT_CONFIG, f)


# -------------------------------------------------------------
# Leer configuración completa
# -------------------------------------------------------------
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        create_default_config()

    try:
        return toml.load(CONFIG_PATH)
    except Exception:
        # archivo roto → se regenera
        create_default_config()
        return DEFAULT_CONFIG


# -------------------------------------------------------------
# Guardar configuración
# -------------------------------------------------------------
def save_config(data: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        toml.dump(data, f)


# -------------------------------------------------------------
# COMMAND: mostrar configuración actual
# -------------------------------------------------------------
@app.command("show")
def show_config():
    """Muestra la configuración del sistema."""
    config = load_config()
    typer.secho("Configuración actual:\n", fg=typer.colors.CYAN)
    typer.echo(toml.dumps(config))


# -------------------------------------------------------------
# COMMAND: resetear configuración
# -------------------------------------------------------------
@app.command("reset")
def reset_config():
    """Restaura config.toml a valores por defecto."""
    create_default_config()
    typer.secho("✔ Configuración restablecida a valores por defecto.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# COMMAND: modificar un valor dentro de la config
# -------------------------------------------------------------
@app.command("set")
def set_config_value(
    section: str = typer.Argument(..., help="postgres, mysql, mongo, backup, cloud"),
    key: str = typer.Argument(..., help="Clave a modificar."),
    value: str = typer.Argument(..., help="Nuevo valor.")
):
    """Modifica una clave del archivo de configuración."""

    config = load_config()

    if section not in config:
        raise typer.BadParameter(f"La sección '{section}' no existe en config.toml")

    if key not in config[section]:
        raise typer.BadParameter(f"La clave '{key}' no existe en la sección '{section}'")

    # Conversión automática inteligentemente
    if value.isdigit():
        value = int(value)
    elif value.lower() in ("true", "false"):
        value = value.lower() == "true"

    config[section][key] = value
    save_config(config)

    typer.secho(f"✔ {section}.{key} actualizado correctamente.", fg=typer.colors.GREEN)


# -------------------------------------------------------------
# COMMAND: configurar cloud de una vez
# -------------------------------------------------------------
@app.command("cloud")
def set_cloud_provider(
    provider: str = typer.Option(..., help="aws | gcp | azure"),
    bucket: str = typer.Option(..., help="Nombre del bucket/contenedor."),
    access_key: str = typer.Option(..., help="Clave de acceso."),
    secret_key: str = typer.Option(..., help="Clave secreta."),
    region: Optional[str] = typer.Option(None, help="Región del proveedor.")
):
    """Configura la sección cloud del archivo de configuración."""

    allowed = ["aws", "gcp", "azure"]
    if provider not in allowed:
        raise typer.BadParameter(f"Proveedor inválido. Debe ser uno de: {allowed}")

    config = load_config()

    config["cloud"]["provider"] = provider
    config["cloud"]["bucket"] = bucket
    config["cloud"]["access_key"] = access_key
    config["cloud"]["secret_key"] = secret_key

    if region:
        config["cloud"]["region"] = region

    save_config(config)

    typer.secho("✔ Configuración de nube actualizada.", fg=typer.colors.GREEN)
