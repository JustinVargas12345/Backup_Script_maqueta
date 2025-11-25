import subprocess
import shlex


class MySQLConnector:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 3306
        self.user = user
        self.password = password
        self.database = database

    def dump_database(self, output_path: str):
        """
        Realiza un backup usando mysqldump.
        """

        cmd = (
            f'mysqldump -h {self.host} -P {self.port} -u {self.user} '
            f'-p{self.password} --databases {self.database} > "{output_path}"'
        )

        # IMPORTANTE: shell=True es necesario para redirección ">"
        process = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:
            raise Exception(
                f"mysqldump error:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )
