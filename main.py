import logging
import os
import traceback
import json
import yaml

from dependency_injector.wiring import inject, Provide
from dependency_injector import providers
from dotenv import load_dotenv

from src.adapters.config_adapter import ProdConfigAdapter, DevConfigAdapter
from src.adapters.processors_adapter import ProcessorsAdapter
from src.configuration.cli import CLIArgumentParser
from src.configuration.config import Config, GenerationOptions, Envs
from src.container import Container
from src.framework_generator import FrameworkGenerator
from src.utils.checkpoint import Checkpoint
from src.utils.logger import Logger
from src.utils.constants import DataSource


@inject
def main(
    logger: logging.Logger,
    config: Config = Provide[Container.config],
    framework_generator: FrameworkGenerator = Provide[Container.framework_generator],
):
    """Main function to orchestrate the API framework generation process."""
    try:
        logger.info("🚀 Starting the API Framework Generation Process! 🌟")

        args = CLIArgumentParser.parse_arguments()

        checkpoint = Checkpoint()

        last_namespace = checkpoint.get_last_namespace()

        def prompt_user_resume_previous_run():
            while True:
                user_input = (
                    input(
                        "Info related to a previous run was found, would you like to resume? (y/n): "
                    )
                    .strip()
                    .lower()
                )

                if user_input in {"y", "n"}:
                    return user_input == "y"

        def _set_data_source(api_file_path: str) -> DataSource:
            """
            Determines the type of data source by reading and parsing the file.

            Args:
                api_file_path: Path to the API definition file

            Returns:
                DataSource: The detected data source type (SWAGGER, POSTMAN, or UNKNOWN)
            """
            if api_file_path.endswith((".yml", ".yaml")):
                return DataSource.SWAGGER

            try:
                with open(api_file_path, "r") as f:
                    if api_file_path.endswith(".json"):
                        data = json.load(f)
                    else:
                        data = yaml.safe_load(f)

                if isinstance(data, dict):
                    if "info" in data and "_postman_id" in data["info"]:
                        return DataSource.POSTMAN
                    elif "openapi" in data or "swagger" in data:
                        return DataSource.SWAGGER

            except Exception as e:
                logger.error(f"Error reading file {api_file_path}: {e}")

        data_source = _set_data_source(args.api_file_path)

        if last_namespace != "default" and prompt_user_resume_previous_run():
            checkpoint.restore_last_namespace()
            args.destination_folder = last_namespace

        if args.use_existing_framework and not args.destination_folder:
            raise ValueError(
                "The destination folder parameter must be set when using an existing framework."
            )

        config.update(
            {
                "api_file_path": args.api_file_path,
                "destination_folder": args.destination_folder
                or config.destination_folder,
                "endpoints": args.endpoints,
                "generate": GenerationOptions(args.generate),
                "data_source": _set_data_source(args.api_file_path),
                "use_existing_framework": args.use_existing_framework,
            }
        )

        processor = None
        if data_source == DataSource.SWAGGER:
            processor = container.swagger_processor()
        elif data_source == DataSource.POSTMAN:
            processor = container.postman_processor()
        else:
            raise ValueError(f"Unsupported data source: {data_source}")

        container.api_processor.override(processor)
        framework_generator = container.framework_generator()

        logger.info(f"\nAPI file path: {config.api_file_path}")
        logger.info(f"Destination folder: {config.destination_folder}")
        logger.info(f"Use existing framework: {config.use_existing_framework}")
        logger.info(
            f"Endpoints: {', '.join(config.endpoints) if config.endpoints else 'All'}"
        )
        logger.info(f"Generate: {config.generate}")
        logger.info(f"Model: {config.model}")

        if last_namespace == "default" or last_namespace != args.destination_folder:
            checkpoint.namespace = config.destination_folder
            checkpoint.save_last_namespace()
        else:
            framework_generator.restore_state(last_namespace)

        api_definitions = framework_generator.process_api_definition()

        if not config.use_existing_framework:
            framework_generator.setup_framework(api_definitions)
            framework_generator.create_env_file(api_definitions)

        framework_generator.generate(api_definitions, config.generate)
        framework_generator.run_final_checks(config.generate)

        checkpoint.clear()

        logger.info("\n✅ Framework generation completed successfully!")

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
    except PermissionError as e:
        logger.error(f"❌ Permission denied: {e}")
    except ValueError as e:
        logger.error(f"❌ Invalid data: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    load_dotenv(override=True)
    env = Envs(os.getenv("ENV", "DEV").upper())

    # Initialize containers
    config_adapter = ProdConfigAdapter() if env == Envs.PROD else DevConfigAdapter()
    processors_adapter = ProcessorsAdapter(config=config_adapter.config)
    container = Container(
        config_adapter=config_adapter, processors_adapter=processors_adapter
    )

    # Wire dependencies
    container.init_resources()
    container.wire(modules=[__name__])

    Logger.configure_logger(container.config())
    logger = Logger.get_logger(__name__)

    try:
        main(logger)
    except Exception as e:
        logger.error(f"💥 A critical error occurred: {e}")
        traceback.print_exc()
