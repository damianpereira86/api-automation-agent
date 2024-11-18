import logging

from src.configuration.config import Config


class Logger:
    @staticmethod
    def configure_logger(config: Config):
        logging.basicConfig(
            format="%(name)s - %(levelname)s - %(message)s",
            level=logging.DEBUG if config.debug else logging.INFO
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

    @staticmethod
    def get_logger(name: str):
        return logging.getLogger(name)