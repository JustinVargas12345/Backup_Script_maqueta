import os
import hashlib
import datetime
import platform


def now_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as ex:
        print(f"[ERROR] No se pudo crear la carpeta: {path}")
        print(f"        {ex}")
        return False


def file_exists(path):
    return os.path.isfile(path)


def get_file_hash(path, algorithm="sha256"):
    if not file_exists(path):
        return None

    hash_func = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def is_windows():
    return platform.system().lower() == "windows"


def is_linux():
    return platform.system().lower() == "linux"


def normalize_path(path):
    return os.path.normpath(path)


def safe_join(base, *paths):
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(os.path.abspath(base)):
        raise ValueError("Intento de escapar del directorio permitido")
    return final_path
