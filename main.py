import logging
import os
import traceback

from dependency_injector.wiring import inject, Provide
from dotenv import load_dotenv

from src.adapters.config_adapter import ProdConfigAdapter, DevConfigAdapter
from src.adapters.processors_adapter import ProcessorsAdapter
from src.configuration.cli import CLIArgumentParser
from src.configuration.config import Config, GenerationOptions, Envs
from src.container import Container
from src.framework_generator import FrameworkGenerator
from src.utils.logger import Logger
from src.utils.repo_creator import create_github_repo, upload_directory_to_github


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

        if args.use_existing_framework and not args.destination_folder:
            raise ValueError(
                "The destination folder parameter must be set when using an existing framework."
            )

        config.update(
            {
                "api_file_path": args.api_file_path,
                "destination_folder": args.destination_folder
                or config.destination_folder,
                "endpoint": args.endpoint,
                "generate": GenerationOptions(args.generate),
                "use_existing_framework": args.use_existing_framework,
                "auto_create_repo": args.auto_create_repo,
            }
        )

        logger.info(f"\nAPI file path: {config.api_file_path}")
        logger.info(f"Destination folder: {config.destination_folder}")
        logger.info(f"Use existing framework: {config.use_existing_framework}")
        logger.info(f"Endpoint: {config.endpoint}")
        logger.info(f"Generate: {config.generate}")
        logger.info(f"Model: {config.model}")

        api_definitions = framework_generator.process_api_definition()

        if not config.use_existing_framework:
            framework_generator.setup_framework()
            framework_generator.create_env_file(api_definitions[0])

        framework_generator.generate(api_definitions, config.generate)
        framework_generator.run_final_checks(config.generate)

        logger.info("\n✅ Framework generation completed successfully!")

        if args.auto_create_repo:
            logger.info("⚡ Repository creation is enabled.")

            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                raise ValueError(
                    "❌ GitHub token not found. Set GITHUB_TOKEN in your .env file."
                )

            repo_name = os.path.basename(config.destination_folder)
            repo_url, owner_repo = create_github_repo(repo_name, github_token)

            if repo_url and owner_repo:
                logger.info(f"✅ Repository successfully created: {repo_url}")

                success = upload_directory_to_github(
                    owner_repo, config.destination_folder, github_token
                )
                if success:
                    logger.info("🚀 All generated files have been uploaded to GitHub!")
                else:
                    logger.error("❌ Some files failed to upload.")

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
    if env == Envs.PROD:
        config_adapter = ProdConfigAdapter()
    else:
        config_adapter = DevConfigAdapter()
    processors_adapter = ProcessorsAdapter()
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
