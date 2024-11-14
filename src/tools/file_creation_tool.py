import json
import os
from typing import List, Type

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel

from src.config import args


class FileSpec(BaseModel):
    path: str = Field(description="The relative file path including the filename")
    fileContent: str = Field(description="The content to be written to the file")


class FileCreationInput(BaseModel):
    files: List[FileSpec] = Field(description="A list of file specifications to create")


class FileCreationTool(BaseTool):
    name: str = "create_files"
    description: str = "Create files with the given content. The input should be a always a List with path and fileContent."
    args_schema: Type[BaseModel]  = FileCreationInput

    def _run(self, files: List[FileSpec]) -> str:
        for file_spec in files:
            path = file_spec.path
            content = file_spec.fileContent
            if path.startswith("./"):
                path = path[2:]
            updated_path = os.path.join(args.destination_folder, path)
            os.makedirs(os.path.dirname(updated_path), exist_ok=True)
            with open(updated_path, "w") as f:
                f.write(content)
        return json.dumps([file_spec.model_dump() for file_spec in files])

    async def _arun(self, files: List[FileSpec]) -> str:
        return self._run(files)
