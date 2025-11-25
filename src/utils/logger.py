import logging
import logging.config
import os


def setup_logger():
    config_file = "config/logging.conf"

    if os.path.exists(config_file):
        logging.config.fileConfig(config_file)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )

    return logging.getLogger("dbbackup")
