import requests
import json
from src.utils.logger import Logger
import yaml


class APIDefinitionLoader:
    """
    Downloads API definition from a URL or loads it from a file and returns it as a JSON object.

    Args:
        api_definition (str): URL or path to the API definition.

    Returns:
        dict: API definition as a dictionary.
    """

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def load(self, api_definition: str) -> dict:
        try:
            if api_definition.startswith("http") and (api_definition.endswith((".json", ".yaml", ".yml"))):
                self.logger.debug(f"Loading API definition from URL: {api_definition}")
                response = requests.get(api_definition)
                if response.status_code == 200:
                    if api_definition.endswith(".json"):
                        return response.json()
                    else:
                        return yaml.safe_load(response.text)
                else:
                    raise Exception(f"Error fetching API definition: {response.status_code}")
            else:
                self.logger.debug(f"Loading API definition from file: {api_definition}")
                with open(api_definition, "r") as file:
                    return json.loads(file.read())
        except Exception as e:
            self.logger.error(f"Error loading API definition: {e}")
            raise
