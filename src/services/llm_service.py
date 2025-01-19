import json
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from .file_service import FileService
from ..configuration.config import Config
from ..ai_tools.file_creation_tool import FileCreationTool
from ..ai_tools.tool_converters import convert_tool_for_model
from ..utils.logger import Logger


class PromptConfig:
    """Configuration for prompt file paths."""

    DOT_ENV = "./prompts/create-dot-env.txt"
    MODELS = "./prompts/create-models.txt"
    FIRST_TEST = "./prompts/create-first-test.txt"
    TESTS = "./prompts/create-tests.txt"
    FIX_TYPESCRIPT = "./prompts/fix-typescript.txt"
    ADDITIONAL_TESTS = "./prompts/create-additional-tests.txt"
    FRAMEWORK_DOCUMENTATION = "./prompts/framework-documentation.txt"


class LLMService:
    """
    Service for managing language model interactions.
    """

    def __init__(
        self,
        config: Config,
        file_service: FileService,
        tools: Optional[List[BaseTool]] = None,
    ):
        """
        Initialize LLM Service.

        Args:
            config (Config): Configuration object
            tools (Optional[List[BaseTool]]): Optional list of tools
        """
        self.config = config
        self.logger = Logger.get_logger(__name__)
        self.tools = tools or [FileCreationTool(config, file_service)]
        self.framework_documentation = self._load_prompt(
            PromptConfig.FRAMEWORK_DOCUMENTATION
        )

    def _select_language_model(self) -> BaseLanguageModel:
        """
        Select and configure the appropriate language model.

        Returns:
            BaseLanguageModel: Configured language model
        """
        try:
            if self.config.model.is_anthropic():
                return ChatAnthropic(
                    model_name=self.config.model.value,
                    temperature=1,
                    api_key=self.config.anthropic_api_key,
                    max_tokens=8192,
                )
            return ChatOpenAI(
                model_name=self.config.model.value,
                temperature=1,
                api_key=self.config.openai_api_key,
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
        self, prompt_path: str, additional_tools: Optional[List[BaseTool]] = None
    ) -> Any:
        """
        Create a flexible AI chain with tool support.

        Args:
            prompt_path (str): Path to the prompt template
            additional_tools (Optional[List[BaseTool]]): Additional tools to bind

        Returns:
            Configured AI processing chain
        """
        try:
            all_tools = self.tools + (additional_tools or [])

            llm = self._select_language_model()
            prompt_template = ChatPromptTemplate.from_template(
                self._load_prompt(prompt_path)
            )

            converted_tools = [convert_tool_for_model(tool, llm) for tool in all_tools]
            llm_with_tools = llm.bind_tools(converted_tools)

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
            self.create_ai_chain(PromptConfig.DOT_ENV).invoke(
                {
                    "framework_documentation": self.framework_documentation,
                    "api_definition": api_definition,
                }
            )
        )

    def generate_models(self, api_definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate models from API definition."""
        return json.loads(
            self.create_ai_chain(PromptConfig.MODELS).invoke(
                {
                    "framework_documentation": self.framework_documentation,
                    "api_definition": api_definition,
                }
            )
        )

    def generate_first_test(
        self, api_definition: Dict[str, Any], models: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate first test from API definition and models."""
        return json.loads(
            self.create_ai_chain(PromptConfig.FIRST_TEST).invoke(
                {
                    "framework_documentation": self.framework_documentation,
                    "api_definition": api_definition,
                    "models": models,
                }
            )
        )

    def generate_additional_tests(
        self,
        tests: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        api_definition: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate additional tests from tests, models and an API definition."""
        return json.loads(
            self.create_ai_chain(PromptConfig.ADDITIONAL_TESTS).invoke(
                {
                    "framework_documentation": self.framework_documentation,
                    "tests": tests,
                    "models": models,
                    "api_definition": api_definition,
                }
            )
        )

    def fix_typescript(self, files: List[Dict[str, str]], messages: List[str]) -> None:
        """
        Fix TypeScript files.

        Args:
            files (List[Dict[str, str]]): Files to fix
            messages (List[str]): Associated error messages
        """
        self.logger.info("\nFixing TypeScript files:")
        for file in files:
            self.logger.info(f"  - {file['path']}")

        self.create_ai_chain(PromptConfig.FIX_TYPESCRIPT).invoke(
            {"files": files, "messages": messages}
        )
