from typing import List

from pydantic import BaseModel, Field

from .file_spec import FileSpec


class FileCreationInput(BaseModel):
    files: List[FileSpec] = Field(
        description="A list of dicts, each containing a path and fileContent key",
        examples=[[{"path": "file.txt", "fileContent": "Hello, World!"}]],
    )
