import re
import sys
from typing import List, Dict
from collections import defaultdict
import subprocess
import os
import json
from src.configuration.config import Config
from src.services.command_service import CommandService
from src.utils.logger import Logger
from src.visuals.loading_animator import LoadingDotsAnimator


class TestController:

    def __init__(self, config: Config, command_service: CommandService):
        self.command_service = command_service
        self.config = config
        self.logger = Logger.get_logger(__name__)

    def get_runnable_files(self, test_files: List[Dict[str, str]]) -> Dict[str, List[str]]:

        success, tsc_output = self.command_service.run_typescript_compiler()

        error_files = set()
        if not success:
            for line in tsc_output.split("\n"):
                match = re.search(r"(src/tests/.*?\.spec\.ts)", line)
                if match:
                    error_files.add(os.path.normpath(match.group(1)))

        runnable_files = []
        skipped_files = []

        for file in test_files:
            rel_path = os.path.normpath(os.path.relpath(file["path"], self.config.destination_folder))
            if any(rel_path.endswith(err_file) for err_file in error_files):
                skipped_files.append(rel_path)
            else:
                runnable_files.append(rel_path)

        if runnable_files:
            print("\n✅ Test files ready to run:")
            for path in runnable_files:
                print(f"   - {path}")
        else:
            print("\n⚠️ No test files can be run due to compilation errors.")

        if skipped_files:
            print("\n❌ Skipping test files with TypeScript compilation errors:")
            for path in skipped_files:
                print(f"   - {path}")

        self.logger.info("\nFinal checks completed")
        return {"runnable": runnable_files, "skipped": skipped_files}

    def prompt_to_run_tests(self) -> bool:
        answer = input("\n🧪 Do you want to run the tests now? (y/n): ").strip().lower()
        if answer not in ("y", "yes", "Y", "YES"):
            self.logger.info("\n🔵 Test run skipped.")
            return False
        return True

    def run_tests(self, test_files: List[str], skipped_files: List[str] = []) -> List[Dict[str, str]]:
        self.logger.info("\n🛠️ Running tests ...\n")
        all_parsed_tests = []
        all_parsed_failures = []

        total_files = len(test_files)

        for index, test_file in enumerate(test_files, start=1):
            file_name = os.path.basename(test_file)
            animator = LoadingDotsAnimator(prefix=f"▶️ Running file {file_name} ({index}/{total_files}) ")
            animator.start()

            ignore_flags = " ".join(f"--ignore {path}" for path in skipped_files)
            command = f"npx mocha -r ts-node/register {test_file} {ignore_flags} --reporter json --timeout 10000 --no-warnings"

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
                all_parsed_failures.extend(parsed.get("failures", []))
                animator.stop()
                sys.stdout.write(f"\r{' ' * 80}\r✅ {file_name} ({index}/{total_files})\n")
            except subprocess.TimeoutExpired:
                animator.stop()
                sys.stdout.write(f"\r{' ' * 80}\r🔍 {file_name} ({index}/{total_files}) - Timed out.\n")
            except json.JSONDecodeError:
                animator.stop()
                sys.stdout.write(
                    f"\r❌ {file_name} ({index}/{total_files}) - Failed to parse test output. Check if tests ran correctly.\n"
                )

        return all_parsed_tests, all_parsed_failures

    def report_tests(self, tests: List[Dict[str, str]], failures: List[Dict[str, str]] = []) -> None:
        grouped_tests = defaultdict(list)

        seen = set()
        all_results = []

        for test in tests + failures:
            key = test.get("fullTitle", "") or test.get("title", "")
            if key and key not in seen:
                seen.add(key)
                all_results.append(test)

        for test in all_results:
            full_title = test.get("fullTitle", "")
            suite_title = full_title.replace(test.get("title", ""), "").strip() or "Ungrouped"
            grouped_tests[suite_title].append(test)

        for suite, tests in grouped_tests.items():
            self.logger.info(f"\n📂 {suite}")
            for test in tests:
                title = test["title"]
                duration = f"({test.get('duration')}ms)" if test.get("duration") else ""

                if test.get("err"):
                    self.logger.warning(f"    🔍 {title}")
                else:
                    self.logger.info(f"    ✅ {title} {duration}")

        self.logger.info("\n🎉 Test run completed. Tests flagged with 🔍 require further review\n")

    def run_tests_flow(self, test_files: List[Dict[str, str]]) -> None:
        test_data = self.get_runnable_files(test_files)
        runnable_files = test_data["runnable"]
        skipped_files = test_data["skipped"]
        if not runnable_files:
            self.logger.warning("⚠️ No test files can be run due to compilation errors.")
            return

        if not self.prompt_to_run_tests():
            return

        results, hook_failures = self.run_tests(runnable_files, skipped_files)
        self.report_tests(results, hook_failures)
