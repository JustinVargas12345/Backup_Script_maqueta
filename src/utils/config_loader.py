import os
import tomllib
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = "config/config.toml"


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}
