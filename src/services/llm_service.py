import json
from typing import Any, Dict, List, Optional

import pydantic
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from src.configuration.models import Model
from src.utils.constants import DataSource

from .file_service import FileService
from ..configuration.config import Config
from ..ai_tools.file_creation_tool import FileCreationTool
from ..ai_tools.file_reading_tool import FileReadingTool
from ..ai_tools.tool_converters import convert_tool_for_model
from ..utils.logger import Logger


class PromptConfig:
    """Configuration for prompt file paths."""

    DOT_ENV = "./prompts/create-dot-env.txt"
    MODELS = "./prompts/create-models.txt"
    FIRST_TEST = "./prompts/create-first-test.txt"
    FIRST_TEST_POSTMAN = "./prompts/create-first-test-postman.txt"
    TESTS = "./prompts/create-tests.txt"
    FIX_TYPESCRIPT = "./prompts/fix-typescript.txt"
    SUMMARY = "./prompts/generate-model-summary.txt"
    ADD_INFO = "./prompts/add-models-context.txt"
    ADDITIONAL_TESTS = "./prompts/create-additional-tests.txt"
    GROUP_PATHS_BY_SERVICE = "./prompts/group-paths-by-service.txt"


class LLMService:
    """
    Service for managing language model interactions.
    """

    def __init__(
        self,
        config: Config,
        file_service: FileService,
    ):
        """
        Initialize LLM Service.

        Args:
            config (Config): Configuration object
        """
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)

    def _select_language_model(
        self, language_model: Optional[Model] = None, override: bool = False
    ) -> BaseLanguageModel:
        """
        Select and configure the appropriate language model.


        Returns:
            BaseLanguageModel: Configured language model
        """
        try:
            if language_model and override:
                self.config.model = language_model
            if self.config.model.is_anthropic():
                return ChatAnthropic(
                    model_name=self.config.model.value,
                    temperature=1,
                    api_key=pydantic.SecretStr(self.config.anthropic_api_key),
                    timeout=None,
                    stop=None,
                    max_retries=3,
                    max_tokens_to_sample=8192,
                )
            return ChatOpenAI(
                model=self.config.model.value,
                temperature=1,
                max_retries=3,
                api_key=pydantic.SecretStr(self.config.openai_api_key),
            )
        except Exception as e:
            self.logger.error(f"Model initialization error: {e}")
            raise

    def _load_prompt(self, prompt_path: str) -> str:
        """
        Load a prompt from a file.

        Args:
            prompt_path (str): Path to the prompt file

        Returns:
            str: Loaded prompt content
        """
        try:
            with open(prompt_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except IOError as e:
            self.logger.error(f"Failed to load prompt from {prompt_path}: {e}")
            raise

    def create_ai_chain(
        self,
        prompt_path: str,
        tools: Optional[List[BaseTool]] = None,
        language_model: Optional[Model] = None,
    ) -> Any:
        """
        Create a flexible AI chain with tool support.

        Args:
            prompt_path (str): Path to the prompt template
            tools (Optional[List[BaseTool]]): Tools to bind
            tool_to_use (Optional[str]): Name of the tool to use
            language_model (Optional[BaseLanguageModel]): Language model to use

        Returns:
            Configured AI processing chain
        """
        try:
            all_tools = tools or []

            llm = self._select_language_model(language_model)
            prompt_template = ChatPromptTemplate.from_template(
                self._load_prompt(prompt_path)
            )

            if tools:
                converted_tools = [
                    convert_tool_for_model(tool, llm) for tool in all_tools
                ]

                if len(tools) == 1:
                    llm_with_tools = llm.bind_tools(
                        converted_tools, tool_choice=converted_tools[0]["name"]
                    )
                else:
                    llm_with_tools = llm.bind_tools(converted_tools)
            else:
                llm_with_tools = llm

            def process_response(response):
                tool_map = {tool.name.lower(): tool for tool in all_tools}

                if response.tool_calls:
                    tool_call = response.tool_calls[0]
                    selected_tool = tool_map.get(tool_call["name"].lower())

                    if selected_tool:
                        return selected_tool.invoke(tool_call["args"])

                return response.content

            return prompt_template | llm_with_tools | process_response

        except Exception as e:
            self.logger.error(f"Chain creation error: {e}")
            raise

    def generate_dot_env(self, api_definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate .env file configuration."""
        return json.loads(
            self.create_ai_chain(
                PromptConfig.DOT_ENV,
                tools=[FileCreationTool(self.config, self.file_service)],
            ).invoke({"api_definition": api_definition})
        )

    def generate_models(self, api_definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate models from API definition."""
        return json.loads(
            self.create_ai_chain(
                PromptConfig.MODELS,
                tools=[
                    FileCreationTool(self.config, self.file_service, are_models=True)
                ],
            ).invoke({"api_definition": api_definition})
        )

    def generate_first_test(
        self, api_definition: Dict[str, Any], models: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate first test from API definition and models."""
        prompt = None
        if self.config.data_source == DataSource.POSTMAN:
            prompt = PromptConfig.FIRST_TEST_POSTMAN
        else:
            prompt = self.config.generate

        return json.loads(
            self.create_ai_chain(
                prompt,
                tools=[FileCreationTool(self.config, self.file_service)],
            ).invoke({"api_definition": api_definition, "models": models})
        )

    def get_additional_models(
        self,
        relevant_models: List[Dict[str, Any]],
        available_models: List[Dict[str, Any]],
    ):
        """Trigger read file tool to decide what additional model info is needed"""
        self.logger.info(f"\nGetting additional models...")
        return self.create_ai_chain(
            PromptConfig.ADD_INFO,
            tools=[FileReadingTool(self.config, self.file_service)],
        ).invoke(
            {
                "relevant_models": relevant_models,
                "available_models": available_models,
            }
        )

    def generate_additional_tests(
        self,
        tests: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        api_definition: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate additional tests from tests, models and an API definition."""
        return json.loads(
            self.create_ai_chain(
                PromptConfig.ADDITIONAL_TESTS,
                tools=[FileCreationTool(self.config, self.file_service)],
            ).invoke(
                {
                    "tests": tests,
                    "models": models,
                    "api_definition": api_definition,
                }
            )
        )

    def group_paths_by_service(self, paths: str) -> List[Dict[str, Any]]:
        """Groups paths by service"""
        return json.loads(
            self.create_ai_chain(
                prompt_path=PromptConfig.GROUP_PATHS_BY_SERVICE
            ).invoke({"paths": paths})
        )

    def fix_typescript(
        self, files: List[Dict[str, str]], messages: List[str], are_models: bool = False
    ) -> None:
        """
        Fix TypeScript files.

        Args:
            files (List[Dict[str, str]]): Files to fix
            messages (List[str]): Associated error messages
        """
        self.logger.info("\nFixing TypeScript files:")
        for file in files:
            self.logger.info(f"  - {file['path']}")

        self.create_ai_chain(
            PromptConfig.FIX_TYPESCRIPT,
            tools=[
                FileCreationTool(self.config, self.file_service, are_models=are_models)
            ],
        ).invoke({"files": files, "messages": messages})
