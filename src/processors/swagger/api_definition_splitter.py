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

        for path, path_data in api_definition.get("paths", {}).items():
            normalized_path = self._normalize_path(path)

            path_copy = copy.deepcopy(api_definition)
            path_copy["paths"] = {path: path_data}
            api_definition_list.append(
                self._create_entry("path", normalized_path, None, path_copy)
            )

            for verb, verb_data in path_data.items():
                verb_copy = copy.deepcopy(path_copy)
                verb_copy["paths"][path] = {verb: verb_data}
                api_definition_list.append(
                    self._create_entry("verb", normalized_path, verb.upper(), verb_copy)
                )

        self.logger.info("Successfully split API definition.")
        return api_definition_list

    @staticmethod
    def _create_entry(
        entry_type: str, path: Optional[str], verb: Optional[str], yaml_content: Dict
    ) -> Dict:
        """Creates a standardized entry for API components."""
        return {
            "type": entry_type,
            "path": path,
            "verb": verb,
            "yaml": yaml.dump(yaml_content, sort_keys=False),
        }

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalizes the path by removing api and version prefixes."""
        parts = [p for p in path.split("/") if p]

        if not parts:
            return path

        start_index = 0

        if start_index < len(parts):
            if parts[start_index] == "api":
                start_index += 1

        if start_index < len(parts):
            if (
                parts[start_index].startswith("v")
                and len(parts[start_index]) > 1
                and parts[start_index][1:].isdigit()
            ):
                start_index += 1

        if start_index < len(parts):
            return "/" + "/".join(parts[start_index:])
        return path
