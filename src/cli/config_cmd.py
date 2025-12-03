import typer
from pathlib import Path
import toml
import logging
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
    except Exception as e:
        # archivo roto → se regenera
        logging.exception(f"Error leyendo config.toml: {e}")
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


@app.command("notify-set")
def set_notify(
    url: str = typer.Option(..., help="URL a la que se enviarán las notificaciones POST"),
):
    """Configura la URL para notificaciones POST tras backups.

    Nota: por seguridad NO se almacenan secretos en el archivo de configuración.
    Use `notify-auth-set` para configurar el método de autenticación (env|prompt|none).
    """
    config = load_config()
    config.setdefault("notify", {})
    config["notify"]["url"] = url
    # No guardar secretos en texto claro
    config["notify"].pop("secret", None)
    save_config(config)
    typer.secho("✔ Notificación (URL) configurada.", fg=typer.colors.GREEN)


@app.command("notify-show")
def show_notify():
    """Muestra la configuración actual de notificaciones."""
    config = load_config()
    notify_cfg = config.get("notify", {})
    if not notify_cfg:
        typer.secho("No hay configuración de notificaciones.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    typer.echo("Notificaciones:")
    typer.echo(f"  URL: {notify_cfg.get('url')}")
    has_secret = bool(notify_cfg.get("secret"))
    typer.echo(f"  Tiene secreto: {has_secret}")


@app.command("notify-auth-set")
def set_notify_auth(
    method: str = typer.Option(..., help="Método: none | env | prompt"),
    token_type: str = typer.Option("jwt", help="Tipo de token: jwt | bearer"),
    env_var: Optional[str] = typer.Option(None, help="Nombre de la variable de entorno que contiene el secreto/token si method=env")
):
    """Configura cómo se obtendrá el secreto/token para firmar o enviar la notificación.

    - method=none: no se envía Authorization.
    - method=env: se leerá el valor desde la variable de entorno indicada por `env_var`.
    - method=prompt: se pedirá el secreto/token en tiempo de ejecución (no se almacena).

    token_type indica si el valor es un `jwt` (secret para firmar JWT HS256) o un `bearer` (token ya firmado).
    """
    allowed_methods = ("none", "env", "prompt")
    allowed_types = ("jwt", "bearer")
    if method not in allowed_methods:
        raise typer.BadParameter(f"method inválido. Debe ser uno de: {allowed_methods}")
    if token_type not in allowed_types:
        raise typer.BadParameter(f"token_type inválido. Debe ser uno de: {allowed_types}")
    if method == "env" and not env_var:
        raise typer.BadParameter("Cuando method=env, debe especificar --env-var con el nombre de la variable de entorno.")

    config = load_config()
    config.setdefault("notify", {})
    config["notify"]["auth"] = {
        "method": method,
        "token_type": token_type,
    }
    if env_var:
        config["notify"]["auth"]["env_var"] = env_var

    # IMPORTANT: Do not store any secret/token value here.
    save_config(config)
    typer.secho("✔ Método de autenticación para notificaciones configurado.", fg=typer.colors.GREEN)


@app.command("notify-auth-show")
def show_notify_auth():
    """Muestra la configuración de autenticación para las notificaciones (sin secretos)."""
    config = load_config()
    notify = config.get("notify", {})
    auth = notify.get("auth")
    if not auth:
        typer.secho("No hay método de autenticación configurado para notificaciones.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    typer.echo("Auth config:")
    typer.echo(f"  method: {auth.get('method')}")
    typer.echo(f"  token_type: {auth.get('token_type')}")
    if auth.get("env_var"):
        typer.echo(f"  env_var: {auth.get('env_var')}")
