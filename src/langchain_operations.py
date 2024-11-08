import json
from file_manager import create_files
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utilities import clean_json_from_markdown
from constants import Model

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

    if Model.is_anthropic(MODEL):
        llm = ChatAnthropic(model_name=MODEL, temperature=1)
    else:
        llm = ChatOpenAI(model_name=MODEL, temperature=1)

    output_parser = StrOutputParser()
    chain = prompt_template | llm | output_parser
    return chain


def _execute_chain_with_retry(chain, inputs, max_retries=3):
    """
    Generic function to execute a chain with retry logic.

    Args:
    - chain: The LangChain chain to execute
    - inputs (dict): The inputs for the chain
    - max_retries (int): Maximum number of retry attempts
    """
    attempt = 0
    while attempt < max_retries:
        try:
            files_json = chain.invoke(inputs)
            cleaned_json = clean_json_from_markdown(files_json)
            return json.loads(cleaned_json)
        except json.JSONDecodeError:
            print(
                f"Failed to parse JSON, retrying... Attempt {attempt + 1}/{max_retries}"
            )
            attempt += 1
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break
    print("Max retries reached or an unexpected error occurred. Aborting operation.")
    return None


def create_dot_env(api_definition, destination_folder, max_retries=3):
    """Create the .env file"""
    chain = _create_chain(DOT_ENV_PROMPT)
    dot_env_file = _execute_chain_with_retry(
        chain, {"api_definition": api_definition}, max_retries
    )
    if dot_env_file is not None:
        create_files(dot_env_file, destination_folder)


def process_path(api_definition, max_retries=3):
    """Process a path in an API definition"""
    chain = _create_chain(MODELS_PROMPT)
    return _execute_chain_with_retry(
        chain, {"api_definition": api_definition}, max_retries
    )


def process_verb(api_definition, models, max_retries=3):
    """Process a verb in an API definition"""
    chain = _create_chain(CREATE_FIRST_TEST_PROMPT)
    return _execute_chain_with_retry(
        chain, {"api_definition": api_definition, "models": models}, max_retries
    )


def fix_typescript(files, messages, destination_folder, max_retries=3):
    """Fix the TypeScript files"""
    print(f"\nFixing TypeScript files: ")
    for file in files:
        print(f"  - {file['path']}")
    chain = _create_chain(FIX_TYPESCRIPT_PROMPT)
    fixed_files = _execute_chain_with_retry(
        chain, {"files": files, "messages": messages}, max_retries
    )
    if fixed_files is not None:
        create_files(fixed_files, destination_folder)
