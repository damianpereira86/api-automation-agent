from dotenv import load_dotenv

from .cli import parse_arguments


def load_environment():
    load_dotenv(override=True)

args = parse_arguments()