import json
import logging
import os
from typing import List, Type, Dict, Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from src.ai_tools.models.file_creation_input import FileCreationInput
from src.ai_tools.models.file_spec import FileSpec
from dependency_injector.wiring import inject

from ..configuration.config import Config
from ..utils.logger import Logger


class FileCreationTool(BaseTool):
    name: str = "create_files"
    description: str = "Create files with a given content."
    args_schema: Type[BaseModel] = FileCreationInput
    config: Config = None
    logger: logging.Logger = None

    @inject
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = Logger.get_logger(__name__)

    def _run(self, files: List[FileSpec]) -> str:
        for file_spec in files:
            path = file_spec.path
            content = file_spec.fileContent
            if path.startswith("./"):
                path = path[2:]

            destination_folder = self.config.destination_folder
            updated_path = os.path.join(destination_folder, path)

            os.makedirs(os.path.dirname(updated_path), exist_ok=True)
            with open(updated_path, "w") as f:
                f.write(content)
            self.logger.info(f"Created file: {path}")

        return json.dumps([file_spec.model_dump() for file_spec in files])

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
