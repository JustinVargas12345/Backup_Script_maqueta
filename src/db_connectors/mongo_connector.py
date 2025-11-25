import subprocess
import shlex
import os


class MongoConnector:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 27017
        self.user = user
        self.password = password
        self.database = database

    def dump_database(self, output_path: str):
        """
        Realiza backup con mongodump.
        El archivo de salida se generará como un directorio; luego lo comprimirá el sistema.
        """

        dump_dir = output_path.replace(".dump", "")

        cmd = (
            f'mongodump --host {self.host} --port {self.port} '
            f'--username {self.user} --password {self.password} '
            f'--db {self.database} --out "{dump_dir}"'
        )

        process = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:
            raise Exception(
                f"mongodump error:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )

        # El CLI de backup espera un archivo .dump, así que generamos uno vacío
        # La compresión + nube ya lo empaquetará correctamente
        with open(output_path, "w") as f:
            f.write("MONGO_DUMP_DIRECTORY:\n" + dump_dir)
