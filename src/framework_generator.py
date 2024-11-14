from .api_processing import process_api_definition
from .file_manager import copy_framework_template
from .langchain_operations import (
    create_dot_env,
    process_path,
    process_verb,
    fix_typescript,
)
from .commands import (
    install_dependencies,
    format_files,
    run_linter,
    run_tests,
    run_typescript_compiler,
    run_typescript_compiler_for_files,
)
from .utilities import run_command_with_fix


class FrameworkGenerator:
    def __init__(self, api_file_path, destination_folder, endpoint=None):
        self.destination_folder = destination_folder
        self.api_file_path = api_file_path
        self.endpoint = endpoint
        self.models_count = 0
        self.tests_count = 0

    def process_api_definition(self):
        return process_api_definition(self.api_file_path)

    def setup_framework(self):
        copy_framework_template(self.destination_folder)
        install_dependencies(self.destination_folder)

    def create_env_file(self, api_definition):
        print("\nGenerating .env file")
        create_dot_env(api_definition)

    def process_definitions(self, merged_api_definition_list, generate_tests):
        print("\nProcessing paths and verbs...")
        models = None

        for api_definition in merged_api_definition_list:
            if not self._should_process_endpoint(api_definition["path"]):
                continue

            if api_definition["type"] == "path":
                models = self._process_path_definition(api_definition)
            elif generate_tests and api_definition["type"] == "verb":
                self._process_verb_definition(api_definition, models)

        print(
            f"\nGeneration complete. {self.models_count} models and {self.tests_count} tests were generated."
        )

    def run_final_checks(self, generate_tests):
        result = run_typescript_compiler(self.destination_folder)
        success, _ = result

        if success and generate_tests:
            run_tests(self.destination_folder)

    def _should_process_endpoint(self, path):
        return self.endpoint is None or self.endpoint == path

    def _process_path_definition(self, api_definition):
        print(f"Generating models for path: {api_definition['path']}...")
        models = process_path(api_definition["yaml"])
        if models is not None:
            self.models_count += len(models)
            self._run_code_quality_checks(models)
        return models

    def _process_verb_definition(self, api_definition, models):
        print(
            f"Generating tests for path: {api_definition['path']} and verb: {api_definition['verb']}..."
        )
        tests = process_verb(api_definition["yaml"], models)
        if tests is not None:
            self.tests_count += 1
            self._run_code_quality_checks(tests)

    def _run_code_quality_checks(self, files):
        run_command_with_fix(
            run_typescript_compiler_for_files,
            fix_typescript,
            files,
            self.destination_folder,
        )
        format_files(self.destination_folder)
        run_linter(self.destination_folder)
