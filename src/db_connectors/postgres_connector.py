import subprocess
import shlex


class PostgresConnector:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port or 5432
        self.user = user
        self.password = password
        self.database = database

    def dump_database(self, output_path: str):
        """
        Realiza un backup usando pg_dump.
        """

        env = {
            "PGPASSWORD": self.password
        }

        cmd = f'pg_dump -h {self.host} -p {self.port} -U {self.user} -d {self.database} -F c -f "{output_path}"'

        process = subprocess.run(
            shlex.split(cmd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:
            raise Exception(
                f"pg_dump error:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )
