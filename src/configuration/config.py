from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional, List

from .models import Model


class Envs(Enum):
    PROD = "PROD"
    DEV = "DEV"


class GenerationOptions(Enum):
    MODELS = "models"
    MODELS_AND_FIRST_TEST = "models_and_first_test"
    MODELS_AND_TESTS = "models_and_tests"


@dataclass
class Config:
    env: Envs = Envs.DEV
    debug: bool = False
    langchain_debug: bool = False
    model: Model = Model.CLAUDE_SONNET
    generate: GenerationOptions = GenerationOptions.MODELS_AND_TESTS
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    api_file_path: str = ""
    data_source: str = ""
    destination_folder: str = ""
    endpoints: Optional[List[str]] = None
    use_existing_framework: bool = False
    fix_retry_json: int = 5

    def update(self, updates: dict[str, Any]):
        for key, value in updates.items():
            setattr(self, key, value)
