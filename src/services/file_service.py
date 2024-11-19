import os
import shutil
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

    def copy_framework_template(self, destination_folder: str) -> Optional[str]:
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
            self.logger.info(
                f"Framework template generated successfully at {destination_folder}"
            )
            return destination_folder
        except Exception as e:
            self.logger.error(f"Error copying folder: {e}")
            return None

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
                updated_path = os.path.join(destination_folder, path)
                os.makedirs(os.path.dirname(updated_path), exist_ok=True)
                with open(updated_path, "w") as f:
                    f.write(content)

                self.logger.info(f"Created file: {path}")
                created_files.append(updated_path)
            except Exception as e:
                self.logger.error(f"Failed to create file {file_spec.path}: {e}")
        return created_files