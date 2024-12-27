from pydantic import BaseModel, Field


class FileSpec(BaseModel):
    path: str = Field(description="The relative file path including the filename")
    fileContent: str = Field(description="The content of the file. Must always be enclosed with double quotes for later parsing into JSON. Escape characters that could cause problems in later json parsing of this attribute using \\ but dont escape the ' character specifically")
