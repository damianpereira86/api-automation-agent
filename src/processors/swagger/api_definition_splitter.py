import copy
from typing import Optional, Dict, List

import yaml

from src.utils.logger import Logger


class APIDefinitionSplitter:
    """Splits API definitions into smaller components."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def split(self, api_definition: Dict) -> List[Dict]:
        """Splits the API definition into smaller, manageable parts."""
        self.logger.info("Splitting API definition into components...")
        api_definition_list = []

        base_copy = copy.deepcopy(api_definition)
        del base_copy["paths"]
        api_definition_list.append(self._create_entry("base", None, None, base_copy))

        # Split paths and verbs
        for path, path_data in api_definition.get("paths", {}).items():
            # Path entry
            path_copy = copy.deepcopy(api_definition)
            path_copy["paths"] = {path: path_data}
            api_definition_list.append(self._create_entry("path", path, None, path_copy))

            # Verb entries
            for verb, verb_data in path_data.items():
                verb_copy = copy.deepcopy(path_copy)
                verb_copy["paths"][path] = {verb: verb_data}
                api_definition_list.append(
                    self._create_entry("verb", path, verb.upper(), verb_copy)
                )

        self.logger.info("Successfully split API definition.")
        return api_definition_list

    @staticmethod
    def _create_entry(entry_type: str, path: Optional[str], verb: Optional[str], yaml_content: Dict) -> Dict:
        """Creates a standardized entry for API components."""
        return {
            "type": entry_type,
            "path": path,
            "verb": verb,
            "yaml": yaml.dump(yaml_content, sort_keys=False),
        }
