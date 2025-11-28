import os
import tomllib
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = "config/config.toml"


def load_config():
    """
    Carga config.toml si existe.
    Si está corrupto o vacío, devuelve {} en lugar de lanzar error.
    Aplica expansión de variables de entorno del estilo ${VAR}.
    """
    if not os.path.exists(CONFIG_PATH):
        return {}

    try:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
    except Exception:
        return {}

    # Expansión de variables de entorno ${VAR}
    def expand(value):
        if isinstance(value, str):
            return os.path.expandvars(value)
        if isinstance(value, dict):
            return {k: expand(v) for k, v in value.items()}
        if isinstance(value, list):
            return [expand(v) for v in value]
        return value

    return expand(config)
