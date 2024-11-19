import json
import logging
from typing import List, Type, Dict, Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from .models.file_creation_input import FileCreationInput
from .models.file_spec import FileSpec

from ..configuration.config import Config
from ..utils.logger import Logger
from ..services.file_service import FileService


class FileCreationTool(BaseTool):
    name: str = "create_files"
    description: str = "Create files with a given content."
    args_schema: Type[BaseModel] = FileCreationInput
    config: Config = None
    file_service: FileService = None
    logger: logging.Logger = None

    def __init__(self, config: Config, file_service: FileService):
        super().__init__()
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)

    def _run(self, files: List[FileSpec]) -> str:
        try:
            created_files = self.file_service.create_files(
                destination_folder=self.config.destination_folder,
                files=files
            )
            self.logger.info(f"Successfully created {len(created_files)} files")
            return json.dumps([file_spec.model_dump() for file_spec in files])
        except Exception as e:
            self.logger.error(f"Error creating files: {e}")
            raise

    async def _arun(self, files: List[FileSpec]) -> str:
        return self._run(files)

    def _parse_input(self, tool_input: str | Dict) -> Dict[str, Any]:
        if isinstance(tool_input, str):
            data = json.loads(tool_input)
        else:
            data = tool_input

        if isinstance(data["files"], str):
            files_data = json.loads(data["files"])
        else:
            files_data = data["files"]

        file_specs = [FileSpec(**file_spec) for file_spec in files_data]
        return {"files": file_specs}
