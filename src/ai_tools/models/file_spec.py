from pydantic import BaseModel, Field


class FileSpec(BaseModel):
    path: str = Field(description="The relative file path including the filename")
    fileContent: str = Field(description="The content of the file")
