import json

from langchain_anthropic import ChatAnthropic
from langchain_anthropic.chat_models import convert_to_anthropic_tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI

from .constants import Model
from .tools.file_creation_tool import FileCreationTool

MODEL = Model.CLAUDE_SONNET
DOT_ENV_PROMPT = "./prompts/create-dot-env.txt"
MODELS_PROMPT = "./prompts/create-models.txt"
CREATE_FIRST_TEST_PROMPT = "./prompts/create-first-test.txt"
CREATE_TESTS_PROMPT = "./prompts/create-tests.txt"
FIX_TYPESCRIPT_PROMPT = "./prompts/fix-typescript.txt"


def _create_chain(prompt_path):
    """
    Create a LangChain chain for a given prompt.

    Args:
    - prompt_path (str): The path to the prompt file.
    """
    with open(prompt_path, "r") as file:
        prompt = file.read()

    prompt_template = ChatPromptTemplate.from_template(prompt)

    if Model.is_anthropic(MODEL.value):
        llm = ChatAnthropic(model_name=MODEL.value, temperature=1)
        llm_with_tools = llm.bind_tools([convert_to_anthropic_tool(FileCreationTool())])
    else:
        llm = ChatOpenAI(model_name=MODEL.value, temperature=1)
        llm_with_tools = llm.bind_tools([convert_to_openai_tool(FileCreationTool())])
    chain = (
        prompt_template
        | llm_with_tools
        | (lambda x: x.tool_calls[0]["args"])
        | FileCreationTool().invoke
    )
    return chain


def create_dot_env(api_definition):
    """Create the .env file"""
    chain = _create_chain(DOT_ENV_PROMPT)
    return json.loads(chain.invoke({"api_definition": api_definition}))


def process_path(api_definition):
    """Process a path in an API definition"""
    chain = _create_chain(MODELS_PROMPT)
    return json.loads(chain.invoke({"api_definition": api_definition}))


def process_verb(api_definition, models):
    """Process a verb in an API definition"""
    chain = _create_chain(CREATE_FIRST_TEST_PROMPT)
    return json.loads(
        chain.invoke({"api_definition": api_definition, "models": models})
    )


def fix_typescript(files, messages):
    """Fix the TypeScript files"""
    print(f"\nFixing TypeScript files: ")
    for file in files:
        print(f"  - {file['path']}")
    chain = _create_chain(FIX_TYPESCRIPT_PROMPT)
    chain.invoke({"files": files, "messages": messages})
