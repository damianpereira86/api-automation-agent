from typing import Optional, List, Dict, Any

from .configuration.config import Config
from .processors.swagger_processor import SwaggerProcessor
from .services.command_service import CommandService
from .services.file_service import FileService
from .services.llm_service import LLMService
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

    def _log_error(self, message: str, exc: Exception):
        """Helper method to log errors consistently"""
        self.logger.error(f"{message}: {exc}")

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

    def create_env_file(self, api_definition):
        """Generate the .env file from the provided API definition"""
        try:
            self.logger.info("\nGenerating .env file")
            self.llm_service.generate_dot_env(api_definition)
        except Exception as e:
            self._log_error("Error creating .env file", e)
            raise

    def process_definitions(
        self,
        merged_api_definition_list: List[Dict[str, Any]],
        generate_tests: bool = True,
    ):
        """Process the API definitions and generate models and tests"""
        try:
            self.logger.info("\nProcessing API definitions")
            models = None
            all_generated_models_info = []
            path_chunks = [path for path in merged_api_definition_list if path["type"] == "path"]
            verb_chunks = [verb for verb in merged_api_definition_list if verb["type"] == "verb"]

            for path in path_chunks:
                if not self._should_process_endpoint(path["path"]):
                    continue

                print(path)
                models = self._process_path_definition(path)
                api_definition_summary = self._generate_api_definition_summary(path)

                all_generated_models_info.append({
                    "path":path["path"],
                    "summary":api_definition_summary,
                    "files":[model["path"] for model in models],
                    "models":models,
                })

            if generate_tests:
                for verb in verb_chunks:
                    print(verb)
                    self._process_verb_definition(verb, all_generated_models_info)

            self.logger.info(
                f"\nGeneration complete. {self.models_count} models and {self.tests_count} tests were generated."
            )
        except Exception as e:
            self._log_error("Error processing definitions", e)
            raise

    def run_final_checks(self, generate_tests: bool = True):
        """Run final checks like TypeScript compilation and tests"""
        try:
            result = self.command_service.run_typescript_compiler()
            success, _ = result

            if success and generate_tests:
                self.command_service.run_tests()

            self.logger.info("Final checks completed")
        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def _should_process_endpoint(self, path: str) -> bool:
        """Check if an endpoint should be processed based on configuration"""
        return self.config.endpoint is None or self.config.endpoint == path

    def _process_path_definition(
        self, api_definition: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Process a path definition and generate models"""
        try:
            self.logger.info(f"\nGenerating models for path: {api_definition['path']}")
            models = self.llm_service.generate_models(api_definition["yaml"],self.config.additional_context)
            if models:
                self.models_count += len(models)
                self._run_code_quality_checks(models)
            return models
        except Exception as e:
            self._log_error(
                f"Error processing path definition for {api_definition['path']}", e
            )
            raise

    def _process_verb_definition(
        self, verb_chunk: Dict[str, Any], models: List[Dict[str, Any]]
    ):
        """Generate tests for a specific verb (HTTP method) in the API definition"""
        try:
            models_matched_by_path = None
            for model in models:
                if verb_chunk["path"] == model["path"] or str(verb_chunk["path"]).startswith(model["path"]+"/"):
                    models_matched_by_path = model["models"]
                    break

            all_available_models = [
                {
                    "path": model["path"],
                    "summary": model["summary"],
                    "files": model["files"]
                }
                for model in models
            ]
            
            read_files = self.llm_service.read_additional_model_info(
                self.config.additional_context,
                all_available_models,
                models_matched_by_path,
                verb_chunk
            )
            print(read_files)

            self.logger.info(
                f"\nGenerating tests for path: {verb_chunk['path']} and verb: {verb_chunk['verb']}"
            )
            tests = self.llm_service.generate_first_test(self.config.additional_context, read_files, verb_chunk["yaml"], models_matched_by_path)
            if tests:
                self.tests_count += 1
                self._run_code_quality_checks(tests)
        except Exception as e:
            self._log_error(
                f"Error processing verb definition for {verb_chunk['path']} - {verb_chunk['verb']}",
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
    
    def _generate_api_definition_summary(self, api_definition: Dict[str, Any]):
        """Generate a summary of a verb/path chunk"""
        try:
            return self.llm_service.generate_chunk_summary(api_definition)
        except Exception as e:
            self._log_error("Error during summary generation", e)
            raise
