from collections import defaultdict
import json
import os
import re
import subprocess
import logging
import sys
from typing import List, Dict, Tuple, Optional, Callable
from src.visuals.loading_animator import LoadingDotsAnimator

from ..configuration.config import Config


class CommandService:
    """
    Service for running shell commands with real-time output and error handling.
    """

    def __init__(self, config: Config, logger: Optional[logging.Logger] = None):
        """
        Initialize CommandService with an optional logger.

        Args:
            config (Config): Configuration instance
            logger (Optional[logging.Logger]): Logger instance (defaults to logger from logging module)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def _log_message(self, message: str, is_error: bool = False):
        """
        Log a message with optional error severity.

        Args:
            message (str): Message to log
            is_error (bool): Whether the message is an error
        """
        log_method = self.logger.error if is_error else self.logger.info
        log_method(message)

    def run_command(self, command: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run a shell command with real-time output and error handling.

        Args:
            command (str): Command to execute
            cwd (Optional[str]): Working directory for command execution

        Returns:
            Tuple[bool, str]: Success status and command output
        """
        try:
            self.logger.info(f"Running command: {command}")
            process = subprocess.Popen(
                command,
                cwd=cwd or self.config.destination_folder,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                universal_newlines=True,
                encoding="utf-8",
                env={
                    **os.environ,
                    "PYTHONUNBUFFERED": "1",
                    "FORCE_COLOR": "true",
                    "TERM": "xterm-256color",
                    "LANG": "en_US.UTF-8",
                    "LC_ALL": "en_US.UTF-8",
                },
            )

            output_lines = []
            while True:
                output = process.stdout.readline()
                if output:
                    output_lines.append(output.rstrip())
                    self._log_message(output.rstrip())

                if output == "" and process.poll() is not None:
                    break

            success = process.returncode == 0
            self._log_message(
                (f"\033[92mCommand succeeded.\033[0m" if success else f"\033[91mCommand failed.\033[0m"),
                is_error=not success,
            )
            return success, "\n".join(output_lines)

        except subprocess.SubprocessError as e:
            self._log_message(f"Subprocess error: {e}", is_error=True)
            return False, str(e)
        except Exception as e:
            self._log_message(f"Unexpected error: {e}", is_error=True)
            return False, str(e)

    def run_command_with_fix(
        self,
        command_func: Callable,
        fix_func: Optional[Callable] = None,
        files: Optional[List[Dict[str, str]]] = None,
        max_retries: int = 3,
    ) -> Tuple[bool, str]:
        """
        Execute a command with retries and an optional fix function on failure.

        Args:
            command_func (Callable): The function that runs the command
            fix_func (Optional[Callable]): Function to invoke if the command fails
            files (Optional[List[Dict[str, str]]]): Files to pass to the command function
            max_retries (int): Max number of retries on failure

        Returns:
            Tuple[bool, str]: Success status and output or error message
        """
        files = files or []
        retry_count = 0
        while retry_count < max_retries:
            if retry_count > 0:
                self._log_message(f"\nAttempt {retry_count + 1}/{max_retries}.")
            elif retry_count == 0:
                self._log_message("")

            success, message = command_func(files)

            if success:
                return success, message

            if fix_func:
                self._log_message(f"Applying fix: {message}")
                fix_func(files, message)

            retry_count += 1

        success, message = command_func(files)

        if success:
            return success, message

        self._log_message(f"Command failed after {max_retries} attempts.", is_error=True)
        return False, message

    def install_dependencies(self) -> Tuple[bool, str]:
        """Install npm dependencies"""
        self._log_message("\nInstalling dependencies...")
        return self.run_command("npm install --loglevel=error")

    def format_files(self) -> Tuple[bool, str]:
        """Format the generated files"""
        self._log_message("\nFormatting files...")
        return self.run_command("npm run prettify")

    def run_linter(self) -> Tuple[bool, str]:
        """Run the linter with auto-fix"""
        self._log_message("\nRunning linter...")
        return self.run_command("npm run lint:fix")

    def run_typescript_compiler(self) -> Tuple[bool, str]:
        """Run the TypeScript compiler"""
        self._log_message("\nRunning TypeScript compiler...\n")
        return self.run_command("npx tsc --noEmit")

    def get_generated_test_files(self) -> List[Dict[str, str]]:
        """Find and return a list of all generated test files from the correct destination folder."""

        test_dir = os.path.join(self.config.destination_folder, "src", "tests")
        test_files = []

        if not os.path.exists(test_dir):
            self._log_message(
                f"⚠️ Test directory '{test_dir}' does not exist. No tests found.",
                is_error=True,
            )
            return []

        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.endswith(".spec.ts"):
                    test_files.append({"path": os.path.join(root, file)})

        return test_files

    def get_runnable_tests(self, files: List[Dict[str, str]]) -> Tuple[List[str], List[str]]:
        success, tsc_output = self.run_typescript_compiler()

        error_files = set()
        if not success:
            for line in tsc_output.split("\n"):
                match = re.search(r"(src/tests/.*?\.spec\.ts)", line)
                if match:
                    error_files.add(os.path.normpath(match.group(1)))

        all_test_files = []
        skipped_files = []

        for file in files:
            rel_path = os.path.normpath(os.path.relpath(file["path"], self.config.destination_folder))
            if any(rel_path.endswith(err_file) for err_file in error_files):
                skipped_files.append(rel_path)
            else:
                all_test_files.append(rel_path)

        if all_test_files:
            print("\n✅ Test files that will be run:")
            for path in all_test_files:
                print(f"   - {path}")
        else:
            print("\n⚠️ No test files can be run due to compilation errors.")

        if skipped_files:
            print("\n❌ Skipping test files with TypeScript errors:")
            for path in skipped_files:
                print(f"   - {path}")

        return all_test_files

    def prompt_and_run_tests(self, runnable_test_files: List[str]) -> None:

        answer = input("\n🧪 Do you want to run the tests now? (y/n): ").strip().lower()
        if answer not in ("y", "yes"):
            print("🛑 Test run skipped.")
            return

        all_test_files = runnable_test_files
        print("\n🛠️ Running tests ...\n")

        all_parsed_tests = []
        total_files = len(all_test_files)

        for index, test_file in enumerate(all_test_files, start=1):
            file_name = os.path.basename(test_file)

            animator = LoadingDotsAnimator(prefix=f"▶️ Running file {file_name} ({index}/{total_files}) ")
            animator.start()

            command = f"npx mocha {test_file} --reporter json --timeout 10000 --no-warnings"

            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.config.destination_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                )
                stdout = result.stdout or ""
                parsed = json.loads(stdout)
                all_parsed_tests.extend(parsed.get("tests", []))

                animator.stop()
                sys.stdout.write(f"\r{' ' * 80}\r✅ {file_name} ({index}/{total_files})\n")
            except subprocess.TimeoutExpired:
                animator.stop()
                sys.stdout.write(
                    f"\r{' ' * 80}\r🔍 {file_name} ({index}/{total_files}) - Timed out. Require human evaluation\n"
                )
            except json.JSONDecodeError:
                animator.stop()
                sys.stdout.write(
                    f"\r❌ {file_name} ({index}/{total_files}) - Failed to parse test output. Check if tests ran correctly.\n"
                )

            grouped_tests = defaultdict(list)

        for test in parsed.get("tests", []):
            full_title = test.get("fullTitle", "")
            suite_title = full_title.replace(test["title"], "").strip() or "Ungrouped"
            grouped_tests[suite_title].append(test)

        for suite, tests in grouped_tests.items():
            print(f"\n📂 {suite}")
            for test in tests:
                title = test["title"]
                duration = f"({test.get('duration')}ms)" if test.get("duration") else ""
                if test.get("err"):
                    print(f"    🔍 {title} - Require human evaluation")
                else:
                    print(f"    ✅ {title} {duration}")


def build_typescript_compiler_command(files: List[Dict[str, str]]) -> str:
    """Build the TypeScript compiler command for specific files"""
    file_paths = " ".join(file["path"] for file in files)
    return (
        f"npx tsc {file_paths} "
        "--lib es2021 "
        "--module NodeNext "
        "--target ESNext "
        "--strict "
        "--esModuleInterop "
        "--skipLibCheck "
        "--forceConsistentCasingInFileNames "
        "--moduleResolution nodenext "
        "--allowUnusedLabels false "
        "--allowUnreachableCode false "
        "--noFallthroughCasesInSwitch "
        "--noImplicitOverride "
        "--noImplicitReturns "
        "--noPropertyAccessFromIndexSignature "
        "--noUncheckedIndexedAccess "
        "--noUnusedLocals "
        "--noUnusedParameters "
        "--checkJs "
        "--noEmit "
        "--strictNullChecks false "
        "--excludeDirectories node_modules"
    )
