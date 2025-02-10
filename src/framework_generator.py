import signal
import sys
from typing import List, Dict, Any
from typing import List, Dict, Any

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
        self.tests_count = 0
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
                "models_count": self.models_count,
                "tests_count": self.tests_count,
            },
            skip_object=True,
        )

    def restore_state(self, namespace: str):
        self.checkpoint.namespace = namespace
        state = self.checkpoint.restore()
        if state:
            self.models_count = state.get("models_count", 0)
            self.tests_count = state.get("tests_count", 0)
            self.logger.info("🔄 Restored checkpoint state.")

    @Checkpoint.checkpoint()
    def process_api_definition(self) -> List[Dict[str, Any]]:
        """Process the API definition file and return a list of API endpoints"""
        try:
            self.logger.info(
                f"\nProcessing API definition from {self.config.api_file_path}"
            )
            return self.swagger_processor.process_api_definition(
                self.config.api_file_path
            )
        except Exception as e:
            self._log_error("Error processing API definition", e)
            raise

    @Checkpoint.checkpoint()
    def setup_framework(self):
        """Set up the framework environment"""
        try:
            self.logger.info(
                f"\nSetting up framework in {self.config.destination_folder}"
            )
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
            self.llm_service.generate_dot_env(api_definition)
        except Exception as e:
            self._log_error("Error creating .env file", e)
            raise

    def generate(
        self,
        merged_api_definition_list: List[Dict[str, Any]],
        generate_tests: GenerationOptions,
    ):
        """Process the API definitions and generate models and tests"""
        try:
            self.logger.info("\nProcessing API definitions")
            api_paths = []
            api_verbs = []

            for definition in merged_api_definition_list:
                if not self._should_process_endpoint(definition["path"]):
                    continue
                if definition["type"] == "path":
                    api_paths.append(definition)
                elif definition["type"] == "verb":
                    api_verbs.append(definition)

            all_generated_models_info = self._generate_models(api_paths)
            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                if not self.checkpoint.restore("tests_generated"):
                    state = self.checkpoint.restore("test_partial")
                    last_idx = state["idx"] if state else 0
                    for idx, verb in enumerate(api_verbs):
                        if idx <= last_idx:
                            continue
                        self._generate_tests(
                            verb, all_generated_models_info, generate_tests
                        )
                        self.checkpoint.save(f"tests_generated", {"idx": idx}, False)
                    self.checkpoint.save("tests_generated", state={}, skip_object=False)
                else:
                    self.logger.info(
                        "✅ Tests already generated. Skipping test generation."
                    )

            self.logger.info(
                f"\nGeneration complete. {self.models_count} models and {self.tests_count} tests were generated."
            )
        except Exception as e:
            self._log_error("Error processing definitions", e)
            raise

    @Checkpoint.checkpoint()
    def run_final_checks(self, generate_tests: GenerationOptions):
        """Run final checks like TypeScript compilation and tests"""
        try:
            result = self.command_service.run_typescript_compiler()
            success, _ = result

            if success and generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                self.command_service.run_tests()

            self.logger.info("Final checks completed")
        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def _should_process_endpoint(self, path: str) -> bool:
        """Check if an endpoint should be processed based on configuration"""
        return self.config.endpoint is None or path.startswith(self.config.endpoint)

    @Checkpoint.checkpoint("generate_models")
    def _generate_models(self, api_paths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a path definition and generate models"""
        all_generated_models_info = []
        state = self.checkpoint.restore("models_partial")
        last_idx = 0
        if state:
            all_generated_models_info = state["all_generated_models_info"]
            last_idx = state["idx"]

        for idx, api_definition in enumerate(api_paths):
            if idx <= last_idx:
                continue
            try:
                self.logger.info(
                    f"\nGenerating models for path: {api_definition['path']}"
                )
                models = self.llm_service.generate_models(api_definition["yaml"])
                if models:
                    self.models_count += len(models)
                    self._run_code_quality_checks(models)
                    self.save_state()
                service_summary = self._generate_service_summary(models)
            except Exception as e:
                self._log_error(
                    f"Error processing path definition for {api_definition['path']}", e
                )
                raise

            all_generated_models_info.append(
                {
                    "path": api_definition["path"],
                    "summary": service_summary,
                    "files": [model["path"] for model in models],
                    "models": models,
                }
            )
            self.checkpoint.save(
                f"models_partial",
                {"idx": idx, "all_generated_models_info": all_generated_models_info},
                skip_object=True,
            )
        return all_generated_models_info

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
                if api_verb["path"] == model["path"] or str(
                    api_verb["path"]
                ).startswith(model["path"] + "/"):
                    relevant_models.append(model["models"])
                else:
                    other_models.append(
                        {
                            "path": model["path"],
                            "summary": model["summary"],
                            "files": model["files"],
                        }
                    )

            self.logger.info(
                f"\nGenerating first test for path: {api_verb['path']} and verb: {api_verb['verb']}"
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
                api_verb["yaml"], relevant_models
            )
            if tests:
                self.tests_count += 1
                self.save_state()
                self._run_code_quality_checks(tests)
                if generate_tests == GenerationOptions.MODELS_AND_TESTS:
                    self._generate_additional_tests(
                        tests,
                        relevant_models,
                        api_verb,
                    )
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
                f"\nGenerating additional tests for path: {api_definition['path']} and verb: {api_definition['verb']}"
            )
            additional_tests = self.llm_service.generate_additional_tests(
                tests, models, api_definition["yaml"]
            )
            if additional_tests:
                self.tests_count += 1
                self.save_state()
                self._run_code_quality_checks(additional_tests)
        except Exception as e:
            self._log_error(
                f"Error generating additional tests for {api_definition['path']} - {api_definition['verb']}",
                e,
            )
            raise

    def _run_code_quality_checks(self, files: List[Dict[str, Any]]):
        """Run code quality checks including TypeScript compilation, linting, and formatting"""
        try:

            def typescript_fix_wrapper(problematic_files, messages):
                self.llm_service.fix_typescript(problematic_files, messages)

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

    def _generate_service_summary(self, models: List[Dict[str, Any]]):
        """Generate a summary of a service"""
        self.logger.info(f"\nGenerating service summary for...")
        try:
            summary = self.llm_service.generate_service_summary(models)
            self.logger.info(f"Service summary: {summary}")
            return summary
        except Exception as e:
            self._log_error("Error during summary generation", e)
            raise
