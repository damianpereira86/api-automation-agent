import logging
import sys
from typing import Optional

from src.configuration.config import Config


class Logger:
    @staticmethod
    def configure_logger(config: Config):
        log_level = logging.DEBUG if config.debug else logging.INFO

        # Default formats
        stdout_format = "%(message)s"
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Handlers
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(log_level)
        stdout_handler.setFormatter(logging.Formatter(stdout_format))

        file_handler = logging.FileHandler(
            "logs/" + config.destination_folder.split("/")[-1] + ".log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(file_format))

        logging.basicConfig(
            format="%(message)s",
            level=log_level,
            handlers=[stdout_handler, file_handler],
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

    @staticmethod
    def get_logger(name: str):
        return logging.getLogger(name)
