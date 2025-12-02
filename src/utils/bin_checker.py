import shutil
import platform
from typing import List, Dict
import glob
import os


# Binarios necesarios según la operación (backup vs restore)
REQUIRED_BINARIES_BY_OP = {
    "backup": {
        "postgres": ["pg_dump"],
        "mysql": ["mysqldump"],
        "mongo": ["mongodump"],
        "sqlserver": ["sqlcmd", "bcp"],
    },
    "restore": {
        "postgres": ["psql", "pg_restore"],
        "mysql": ["mysql"],
        "mongo": ["mongorestore"],
        "sqlserver": ["sqlcmd", "bcp"],
    },
}

# Flatten unique names
ALL_BINARIES = sorted({b for op in REQUIRED_BINARIES_BY_OP.values() for vals in op.values() for b in vals})


def check_binaries(which_list: List[str] = None) -> Dict[str, bool]:
    """
    Comprueba la presencia de binarios en el PATH.

    :param which_list: lista de nombres de binarios a chequear. Si None, usa ALL_BINARIES.
    :return: dict {binary_name: found_bool}
    """
    targets = which_list or ALL_BINARIES
    result = {}
    for binary in targets:
        path = shutil.which(binary)
        if path:
            result[binary] = True
            continue

        # fallback: buscar en rutas comunes conocidas (Windows Program Files, etc.)
        alt = _find_in_common_paths(binary)
        result[binary] = alt is not None
    return result


def find_binaries(which_list: List[str] = None) -> Dict[str, str]:
    """
    Devuelve un dict con la ruta encontrada para cada binario, o None si no se encuentra.
    :return: {binary_name: path_or_None}
    """
    targets = which_list or ALL_BINARIES
    result: Dict[str, str] = {}
    for binary in targets:
        path = shutil.which(binary)
        if path:
            result[binary] = path
            continue

        alt = _find_in_common_paths(binary)
        result[binary] = alt

    return result


def _find_in_common_paths(binary: str) -> str:
    """Busca ejecutables en rutas comunes usadas por los conectores.

    Devuelve la ruta si se encuentra, o None.
    """
    system = platform.system().lower()

    patterns = []
    # Windows comunes
    if system == "windows":
        if binary.lower() in ("pg_dump", "pg_restore", "psql"):
            patterns.extend([
                r"C:\\Program Files\\PostgreSQL\\*\\bin\\%s.exe" % binary,
                r"C:\\Program Files\\pg*\\bin\\%s.exe" % binary,
            ])
        if binary.lower() in ("mysqldump", "mysql"):
            patterns.extend([
                r"C:\\Program Files\\MySQL\\*\\bin\\%s.exe" % binary,
            ])
        if binary.lower() in ("mongodump", "mongorestore", "mongosh"):
            patterns.extend([
                r"C:\\Program Files\\MongoDB\\Tools\\bin\\%s.exe" % binary,
                r"C:\\Program Files\\MongoDB\\Server\\*\\bin\\%s.exe" % binary,
            ])
        if binary.lower() in ("sqlcmd", "bcp"):
            patterns.extend([
                r"C:\\Program Files\\Microsoft SQL Server\\*\\Tools\\Binn\\%s.exe" % binary,
            ])

    else:
        # *nix/mac common locations
        patterns.extend([
            "/usr/bin/%s" % binary,
            "/usr/local/bin/%s" % binary,
            "/usr/lib/postgresql/*/bin/%s" % binary,
            "/opt/mongodb/bin/%s" % binary,
        ])

    for p in patterns:
        # expand glob patterns
        for candidate in glob.glob(p):
            if os.path.exists(candidate):
                return candidate

    return None


def suggest_install_instructions() -> Dict[str, str]:
    """
    Devuelve sugerencias de instalación por plataforma para los binarios más comunes.
    No pretende cubrir todas las distribuciones; solo provee puntos de partida.
    """
    system = platform.system().lower()
    suggestions = {}

    if system == "windows":
        suggestions["psql"] = "choco install postgresql"  # choco
        suggestions["pg_restore"] = "choco install postgresql"
        suggestions["mysql"] = "choco install mysql"  # puede variar
        suggestions["mysqladmin"] = "choco install mysql"
        suggestions["mongorestore"] = "choco install mongodb"  # mongo tools
        suggestions["mongosh"] = "choco install mongosh"
        suggestions["sqlcmd"] = "choco install mssql-tools"  # o instalar MS SQL tools
    else:
        # Linux / macOS (brew)
        suggestions["psql"] = "apt-get install postgresql-client -y  # Debian/Ubuntu\n# OR\nbrew install libpq && brew link --force libpq" 
        suggestions["pg_restore"] = suggestions["psql"]
        suggestions["mysql"] = "apt-get install default-mysql-client -y  # Debian/Ubuntu\n# OR\nbrew install mysql"
        suggestions["mysqladmin"] = suggestions["mysql"]
        suggestions["mongorestore"] = "apt-get install mongodb-clients -y  # Debian/Ubuntu\n# OR\nbrew tap mongodb/brew && brew install mongodb-database-tools"
        suggestions["mongosh"] = "npm install -g mongosh  # or use distro packages"
        suggestions["sqlcmd"] = "# Instalar mssql-tools siguiendo instrucciones oficiales: https://docs.microsoft.com/"

    return suggestions


if __name__ == "__main__":
    # Modo standalone para debug
    res = find_binaries()
    for k, v in res.items():
        if v:
            print(f"{k}: FOUND -> {v}")
        else:
            print(f"{k}: MISSING")
    if not all(v for v in res.values()):
        print("\nSugerencias de instalación:")
        for k, s in suggest_install_instructions().items():
            print(f"- {k}: {s}")
