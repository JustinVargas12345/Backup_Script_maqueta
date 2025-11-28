import subprocess
import logging
from pathlib import Path

# -------------------------------------------------------
# Configuración global del logger
# -------------------------------------------------------
LOG_PATH = Path("backup_master_log.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def run_cmd(command: str, timeout: int = 600):
    """
    Ejecuta un comando del sistema y registra la salida en backup_master_log.log.

    :param command: Comando shell a ejecutar.
    :param timeout: Tiempo máx. de espera en segundos.
    :return: dict con stdout, stderr, returncode.
    """

    logging.info(f"[RUN_CMD] Ejecutando comando: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Log de resultados
        logging.info(f"[RUN_CMD] returncode: {result.returncode}")
        if result.stdout.strip():
            logging.info(f"[RUN_CMD] STDOUT:\n{result.stdout}")
        if result.stderr.strip():
            logging.warning(f"[RUN_CMD] STDERR:\n{result.stderr}")

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        msg = f"El comando excedió el tiempo límite de {timeout}s"
        logging.error(f"[RUN_CMD] TIMEOUT: {msg}")
        return {
            "stdout": "",
            "stderr": msg,
            "returncode": -1
        }

    except Exception as e:
        logging.exception(f"[RUN_CMD] Error inesperado: {str(e)}")
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }
