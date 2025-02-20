import os
import shutil
import json
from typing import List, Optional

from src.ai_tools.models.file_spec import FileSpec
from src.utils.logger import Logger


class FileService:
    """
    Service for handling file operations.
    """

    def __init__(self):
        """
        Initialize FileService.
        """
        self.logger = Logger.get_logger(__name__)

    def copy_framework_template(
        self, destination_folder: str, api_definition=None
    ) -> Optional[str]:
        """
        Copy the API framework template to a new folder.

        Args:
            destination_folder (str): Destination folder to copy the template to

        Returns:
            Optional[str]: The destination folder if successful, None otherwise
        """
        src_folder = "./api-framework-template"
        self.logger.info("Generating new framework...")
        try:
            shutil.copytree(src_folder, destination_folder)
            self.logger.info(f"Framework template generated successfully.")
            return destination_folder
        except Exception as e:
            self.logger.error(f"Error copying folder: {e}")
            return None

    def update_framework_for_postman(self, destination_folder, extracted_requests):
        self._create_run_order_file(destination_folder, extracted_requests)
        self._update_package_dot_json(destination_folder)

    def _create_run_order_file(
        self, destination_folder: str, extracted_requests: List[str]
    ):
        file_content = ["// This file runs the tests in order"]

        for request in extracted_requests:
            filepath = f'./src/tests{request["file_path"]}/{request["name"]}.spec.ts'
            file_content.append(f'import "{filepath}";')

        run_tests_file_spec = FileSpec(
            path="runTestsInOrder.js", fileContent="\n".join(file_content)
        )

        self.create_files(destination_folder, [run_tests_file_spec])
        self.logger.info(f"Created runTestsInOrder.js file at {destination_folder}")

    def _update_package_dot_json(self, destination_folder: str):
        package_json_path = os.path.join(destination_folder, "package.json")

        try:
            with open(package_json_path, "r") as file:
                package_json = json.load(file)
                package_json["scripts"][
                    "test"
                ] = "mocha runTestsInOrder.js --timeout 10000"

            with open(package_json_path, "w") as file:
                json.dump(package_json, file, indent=2)

            self.logger.info(f"Updated package.json at {package_json_path}")
        except Exception as e:
            self.logger.error(f"Failed to update package.json: {e}")

    def create_files(self, destination_folder: str, files: List[FileSpec]) -> List[str]:
        """
        Create files with the specified content.

        Args:
            destination_folder (str): Base folder to create the files in
            files (List[FileSpec]): List of FileSpec objects defining paths and content

        Returns:
            List[str]: List of paths to the created files
        """
        created_files = []
        for file_spec in files:
            try:
                path = file_spec.path
                content = file_spec.fileContent
                if path.startswith("./"):
                    path = path[2:]
                path = path.lstrip("/")
                updated_path = os.path.join(destination_folder, path)
                os.makedirs(os.path.dirname(updated_path), exist_ok=True)
                with open(updated_path, "w") as f:
                    f.write(content)

                self.logger.info(f"Created file: {path}")
                created_files.append(updated_path)
            except Exception as e:
                self.logger.error(f"Failed to create file {file_spec.path}: {e}")
        return created_files

    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read file content specified by path.

        Args:
            file_path (str): File path to read.

        Returns:
            Optional[str]: File contents if successful, None if file cannot be read.
        """
        try:
            with open(file_path, "r") as file:
                return file.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return None
