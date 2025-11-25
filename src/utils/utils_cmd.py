import subprocess
import logging

def run_cmd(cmd):
    """
    Ejecuta comandos del sistema de forma segura.
    Devuelve True si el comando terminó correctamente, False si hubo error.
    """

    logging.info(f"Ejecutando comando: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )

        # Mostrar outputs
        if result.stdout:
            logging.info(result.stdout.strip())

        if result.stderr:
            logging.warning(result.stderr.strip())

        # Validar código de salida
        if result.returncode != 0:
            logging.error(f"Error ejecutando comando. Código: {result.returncode}")
            return False

        return True

    except Exception as e:
        logging.error(f"Excepción ejecutando comando: {str(e)}")
        return False
