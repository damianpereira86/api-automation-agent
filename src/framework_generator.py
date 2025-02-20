import signal
import sys
import json
from typing import List, Dict, Any, Optional

from src.processors.api_processor import APIProcessor
from src.utils.constants import DataSource

from .ai_tools.models.file_spec import FileSpec
from .configuration.config import Config, GenerationOptions
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
        api_processor: APIProcessor,
    ):
        self.config = config
        self.llm_service = llm_service
        self.command_service = command_service
        self.file_service = file_service
        self.api_processor = api_processor
        self.models_count = 0
        self.test_files_count = 0
        self.logger = Logger.get_logger(__name__)
        self.checkpoint = Checkpoint(
            self, "framework_generator", self.config.destination_folder
        )

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
            self.logger.info(
                f"\nProcessing API definition from {self.config.api_file_path}"
            )
            return self.api_processor.process_api_definition(self.config.api_file_path)
        except Exception as e:
            self._log_error("Error processing API definition", e)
            raise

    @Checkpoint.checkpoint()
    def setup_framework(self, api_definition):
        """Set up the framework environment"""
        try:
            self.logger.info(
                f"\nSetting up framework in {self.config.destination_folder}"
            )
            self.file_service.copy_framework_template(self.config.destination_folder)
            if self.config.data_source == DataSource.POSTMAN:
                self.file_service.update_framework_for_postman(
                    self.config.destination_folder, api_definition
                )
            self.command_service.install_dependencies()
        except Exception as e:
            self._log_error("Error setting up framework", e)
            raise

    @Checkpoint.checkpoint()
    def create_env_file(self, api_definitions):
        """Generate the .env file from the provided API definition"""
        try:
            self.logger.info("\nGenerating .env file")
            env_vars_data = self.api_processor.extract_env_vars(api_definitions)
            self.llm_service.generate_dot_env(env_vars_data)
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

            api_paths = self.api_processor.get_api_paths(merged_api_definition_list)
            api_verbs = self.api_processor.get_api_verbs(merged_api_definition_list)

            for path in self.checkpoint.checkpoint_iter(
                api_paths, "generate_paths", all_generated_models
            ):
                models = self._generate_models(path)
                all_generated_models["info"].append(
                    {
                        "path": self.api_processor.get_api_path_name(path),
                        "files": [
                            model["path"] + " - " + model["summary"] for model in models
                        ],
                        "models": models,
                    }
                )
                self.logger.debug(
                    "Generated models for path: "
                    + self.api_processor.get_api_path_name(path)
                )

            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                for verb in self.checkpoint.checkpoint_iter(
                    api_verbs, "generate_verbs"
                ):
                    service_related_to_verb = self.api_processor.get_api_verb_rootpath(
                        verb
                    )
                    tests = self._generate_tests(
                        verb, all_generated_models["info"], generate_tests
                    )
                    for file in tests:
                        if "/responses" in file["path"]:
                            for model in all_generated_models["info"]:
                                if model["path"] == service_related_to_verb:
                                    model["files"].append(file["path"])
                                    model["models"].append(
                                        {
                                            "path": file["path"],
                                            "fileContent": file["fileContent"],
                                        }
                                    )

                    self.logger.debug(
                        f"Generated tests for path: {self.api_processor.get_api_verb_path(verb)} - {self.api_processor.get_api_verb_name(verb)}"
                    )

            self.logger.info(
                f"\nGeneration complete. {self.models_count} models and {self.test_files_count} tests were generated."
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
                    self.command_service.run_specific_tests_excluding_errors(test_files)

            self.logger.info("Final checks completed")

        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def _generate_models(
        self, api_definition: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Process a path definition and generate models"""
        try:
            self.logger.info(
                f"\nGenerating models for path: {self.api_processor.get_api_path_name(api_definition)}"
            )
            models = self.llm_service.generate_models(
                self.api_processor.get_api_path_content(api_definition)
            )
            if models:
                self.models_count += len(models)
                self._run_code_quality_checks(models, are_models=True)

            else:
                self.logger.warning(
                    f"No models generated for {self.api_processor.get_api_path_name(api_definition)}"
                )

            return models
        except Exception as e:

            self._log_error(
                f"Error processing path definition for {self.api_processor.get_api_path_name(api_definition)}",
                e,
            )

            raise

    def _generate_tests(
        self,
        api_verb: Dict[str, Any],
        all_models: List[Dict[str, Any]],
        generate_tests: GenerationOptions,
    ) -> Optional[List[Dict[str, Any]]]:
        """Generate tests for a specific verb (HTTP method) in the API definition"""
        try:
            relevant_models = self.api_processor.get_relevant_models(
                api_verb, all_models
            )
            other_models = self.api_processor.get_other_models(api_verb, all_models)

            self.logger.info(
                f"\nGenerating first test for path: {self.api_processor.get_api_verb_path(api_verb)} and verb: {self.api_processor.get_api_verb_name(api_verb)}"
            )

            if other_models:
                additional_models: List[FileSpec] = (
                    self.llm_service.get_additional_models(
                        relevant_models,
                        other_models,
                    )
                )
                self.logger.info(
                    f"\nAdding additional models: {[model.path for model in additional_models]}"
                )
                relevant_models.extend(map(lambda x: x.to_json(), additional_models))

            tests = self.llm_service.generate_first_test(
                self.api_processor.get_api_verb_content(api_verb), relevant_models
            )

            if tests:
                self.test_files_count += len(tests)
                self.save_state()

                self._run_code_quality_checks(tests)
                if generate_tests == GenerationOptions.MODELS_AND_TESTS:
                    additional_tests = self._generate_additional_tests(
                        tests,
                        relevant_models,
                        api_verb,
                    )

                    return additional_tests

                return tests

            else:
                self.logger.warning(
                    f"No tests generated for {self.api_processor.get_api_verb_path(api_verb)} - {self.api_processor.get_api_verb_name('verb')}"
                )

        except Exception as e:

            self._log_error(
                f"Error processing verb definition for {self.api_processor.get_api_verb_path(api_verb)} - {self.api_processor.get_api_verb_name(api_verb)}",
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
                f"\nGenerating additional tests for path: {self.api_processor.get_api_verb_path(api_definition)} and verb: {self.api_processor.get_api_verb_name(api_definition)}"
            )

            additional_tests = self.llm_service.generate_additional_tests(
                tests,
                models,
                self.api_processor.get_api_path_content(api_definition),
            )
            if additional_tests:
                self.save_state()
                self._run_code_quality_checks(additional_tests)

            return additional_tests
        except Exception as e:

            self._log_error(
                f"Error generating additional tests for {self.api_processor.get_api_verb_path(api_definition)} - {self.api_processor.get_api_verb_name(api_definition)}",
                e,
            )

            raise

    def _run_code_quality_checks(
        self, files: List[Dict[str, Any]], are_models: bool = False
    ):
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
