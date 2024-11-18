import argparse
from datetime import datetime


class CLIArgumentParser:
    @staticmethod
    def parse_arguments():
        parser = argparse.ArgumentParser(description="API Framework Generation Tool")
        parser.add_argument(
            "api_file_path",
            help="The path of the OpenAPI definition file to process."
        )
        parser.add_argument(
            "--destination-folder",
            type=str,
            default=f"./generated/generated-framework_{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            help="Destination folder in which the files will be created (optional).",
        )
        parser.add_argument(
            "--endpoint",
            type=str,
            help="Specify the endpoint to generate the framework for (optional).",
        )
        parser.add_argument(
            "--generate",
            type=str,
            choices=["models", "models-and-tests"],
            default="models",
            help="Specify what to generate. 'models' for models only, 'models-and-tests' for models and tests.",
        )
        return parser.parse_args()