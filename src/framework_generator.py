import json
import signal
import sys
import yaml
from typing import List, Dict, Any, Optional

from .ai_tools.models.file_spec import FileSpec
from .configuration.config import Config, GenerationOptions
from .processors.swagger_processor import SwaggerProcessor
from .services.command_service import CommandService
from .services.file_service import FileService
from .services.llm_service import LLMService
from .utils.checkpoint import Checkpoint
from .utils.logger import Logger


class FrameworkGenerator:
    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        command_service: CommandService,
        file_service: FileService,
        swagger_processor: SwaggerProcessor,
    ):
        self.config = config
        self.llm_service = llm_service
        self.command_service = command_service
        self.file_service = file_service
        self.swagger_processor = swagger_processor
        self.models_count = 0
        self.test_files_count = 0
        self.logger = Logger.get_logger(__name__)
        self.checkpoint = Checkpoint(self, "framework_generator", self.config.destination_folder)

        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        self.logger.warning("⚠️ Process interrupted! Saving progress...")
        try:
            self.save_state()
        finally:
            sys.exit(1)

    def _log_error(self, message: str, exc: Exception):
        """Helper method to log errors consistently"""
        self.logger.error(f"{message}: {exc}")

    def save_state(self):
        self.checkpoint.save(
            state={
                "destination_folder": self.config.destination_folder,
                "self": {
                    "models_count": self.models_count,
                    "test_files_count": self.test_files_count,
                },
            }
        )

    def restore_state(self, namespace: str):
        self.checkpoint.namespace = namespace
        self.checkpoint.restore(restore_object=True)

    @Checkpoint.checkpoint()
    def process_api_definition(self) -> List[Dict[str, Any]]:
        """Process the API definition file and return a list of API endpoints"""
        try:
            self.logger.info(f"\nProcessing API definition from {self.config.api_definition}")
            return self.swagger_processor.process_api_definition(self.config.api_definition)
        except Exception as e:
            self._log_error("Error processing API definition", e)
            raise

    @Checkpoint.checkpoint()
    def setup_framework(self):
        """Set up the framework environment"""
        try:
            self.logger.info(f"\nSetting up framework in {self.config.destination_folder}")
            self.file_service.copy_framework_template(self.config.destination_folder)
            self.command_service.install_dependencies()
        except Exception as e:
            self._log_error("Error setting up framework", e)
            raise

    @Checkpoint.checkpoint()
    def create_env_file(self, api_definition):
        """Generate the .env file from the provided API definition"""
        try:
            self.logger.info("\nGenerating .env file")

            # Remove paths from the API definition
            api_definition_str = api_definition["yaml"]

            try:
                env_definition_dict = json.loads(api_definition_str)
            except json.JSONDecodeError:
                env_definition_dict = yaml.safe_load(api_definition_str)

            if "paths" in env_definition_dict:
                env_definition_dict.pop("paths")

            if isinstance(api_definition_str, str) and api_definition_str.strip().startswith("{"):
                env_definition = json.dumps(env_definition_dict)
            else:
                env_definition = yaml.dump(env_definition_dict)

            self.llm_service.generate_dot_env(env_definition)
        except Exception as e:
            self._log_error("Error creating .env file", e)
            raise

    @Checkpoint.checkpoint()
    def generate(
        self,
        merged_api_definition_list: List[Dict[str, Any]],
        generate_tests: GenerationOptions,
    ):
        """Process the API definitions and generate models and tests"""
        try:
            self.logger.info("\nProcessing API definitions")
            all_generated_models = {"info": []}
            api_paths = []
            api_verbs = []

            for definition in merged_api_definition_list:
                if not self._should_process_endpoint(definition["path"]):
                    continue
                if definition["type"] == "path":
                    api_paths.append(definition)
                elif definition["type"] == "verb":
                    api_verbs.append(definition)

            for path in self.checkpoint.checkpoint_iter(api_paths, "generate_paths", all_generated_models):
                models = self._generate_models(path)
                all_generated_models["info"].append(
                    {
                        "path": path["path"],
                        "files": [model["path"] + " - " + model["summary"] for model in models],
                        "models": models,
                    }
                )
                self.logger.debug("Generated models for path: " + path["path"])

            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                for verb in self.checkpoint.checkpoint_iter(api_verbs, "generate_verbs"):
                    self._generate_tests(verb, all_generated_models["info"], generate_tests)
                    self.logger.debug(f"Generated tests for path: {verb['path']} - {verb['verb']}")

            self.logger.info(
                f"\nGeneration complete. "
                f"{self.models_count} models and {self.test_files_count} tests were generated."
            )
        except Exception as e:
            self._log_error("Error processing definitions", e)
            self.save_state()
            raise

    @Checkpoint.checkpoint()
    def run_final_checks(self, generate_tests: GenerationOptions):
        """Run final checks like TypeScript compilation and tests"""
        try:
            test_files = self.command_service.get_generated_test_files()

            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                if not test_files:
                    self.logger.warning("⚠️ No test files found! Skipping tests.")
                else:
                    tests = self.command_service.get_runnable_tests(test_files)

            self.logger.info("\nFinal checks completed")

            self.command_service.prompt_and_run_tests(tests)

        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def _should_process_endpoint(self, path: str) -> bool:
        """Check if an endpoint should be processed based on configuration"""
        if self.config.endpoints is None:
            return True
        return any(path.startswith(endpoint) for endpoint in self.config.endpoints)

    def _generate_models(self, api_definition: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Process a path definition and generate models"""
        try:
            self.logger.info(f"\nGenerating models for path: {api_definition['path']}")
            models = self.llm_service.generate_models(api_definition["yaml"])
            if models:
                self.models_count += len(models)
                self._run_code_quality_checks(models, are_models=True)
            else:
                self.logger.warning(f"No models generated for {api_definition['path']}")
            return models
        except Exception as e:
            self._log_error(f"Error processing path definition for {api_definition['path']}", e)
            raise

    def _generate_tests(
        self,
        api_verb: Dict[str, Any],
        all_models: List[Dict[str, Any]],
        generate_tests: GenerationOptions,
    ):
        """Generate tests for a specific verb (HTTP method) in the API definition"""
        try:
            relevant_models = []
            other_models = []
            for model in all_models:
                if api_verb["path"] == model["path"] or str(api_verb["path"]).startswith(model["path"] + "/"):
                    relevant_models.append(model["models"])
                else:
                    other_models.append(
                        {
                            "path": model["path"],
                            "files": model["files"],
                        }
                    )

            self.logger.info(
                f"\nGenerating first test for path: {api_verb['path']} and verb: {api_verb['verb']}"
            )

            if other_models:
                additional_models: List[FileSpec] = self.llm_service.get_additional_models(
                    relevant_models,
                    other_models,
                )
                self.logger.info(f"\nAdding additional models: {[model.path for model in additional_models]}")
                relevant_models.extend(map(lambda x: x.to_json(), additional_models))

            tests = self.llm_service.generate_first_test(api_verb["yaml"], relevant_models)
            if tests:
                self.test_files_count += 1
                self.save_state()
                self._run_code_quality_checks(tests)
                if generate_tests == GenerationOptions.MODELS_AND_TESTS:
                    self._generate_additional_tests(
                        tests,
                        relevant_models,
                        api_verb,
                    )
            else:
                self.logger.warning(f"No tests generated for {api_verb['path']} - {api_verb['verb']}")
        except Exception as e:
            self._log_error(
                f"Error processing verb definition for {api_verb['path']} - {api_verb['verb']}",
                e,
            )

            raise

    def _generate_additional_tests(
        self,
        tests: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        api_definition: Dict[str, Any],
    ):
        """Generate additional tests based on the initial test and models"""
        try:
            self.logger.info(
                f"\nGenerating additional tests for path: {api_definition['path']} "
                f"and verb: {api_definition['verb']}"
            )
            additional_tests = self.llm_service.generate_additional_tests(
                tests, models, api_definition["yaml"]
            )
            if additional_tests:
                self.save_state()
                self._run_code_quality_checks(additional_tests)
        except Exception as e:
            self._log_error(
                f"Error generating additional tests for {api_definition['path']} - {api_definition['verb']}",
                e,
            )
            raise

    def _run_code_quality_checks(self, files: List[Dict[str, Any]], are_models: bool = False):
        """Run code quality checks including TypeScript compilation, linting, and formatting"""
        try:

            def typescript_fix_wrapper(problematic_files, messages):
                self.llm_service.fix_typescript(problematic_files, messages, are_models)

            self.command_service.run_command_with_fix(
                self.command_service.run_typescript_compiler_for_files,
                typescript_fix_wrapper,
                files,
            )
            self.command_service.format_files()
            self.command_service.run_linter()
        except Exception as e:
            self._log_error("Error during code quality checks", e)
            raise
