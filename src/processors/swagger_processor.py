from typing import Dict, List, Union

from .swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    FileLoader,
    APIDefinitionLoader,
)
from ..utils.logger import Logger


class SwaggerProcessor:
    """Processes API definitions by orchestrating file loading, splitting, and merging."""

    def __init__(
        self,
        file_loader: FileLoader,
        splitter: APIDefinitionSplitter,
        merger: APIDefinitionMerger,
        apiDefinitionLoader: APIDefinitionLoader = None,
    ):
        """
        Initialize the SwaggerProcessor.

        Args:
            file_loader (FileLoader): Service to load API definition files.
            splitter (APIDefinitionSplitter): Service to split API definitions.
            merger (APIDefinitionMerger): Service to merge API definitions.
            apiDefinitionLoader (APIDefinitionLoader): Service to load API definition from URL or file.
        """
        self.file_loader = file_loader
        self.splitter = splitter
        self.merger = merger
        self.apiDefinitionLoader = apiDefinitionLoader or APIDefinitionLoader()
        self.logger = Logger.get_logger(__name__)

    def process_api_definition(self, api_definition: str) -> List[Dict[str, Union[str, Dict]]]:
        """
        Processes an API definition by loading, splitting, and merging its components.

        Args:
            api_definition (str): URL or path to the API definition.

        Returns:
            List of merged API definitions.
        """
        try:
            self.logger.info("Starting API processing")

            raw_definition = self.apiDefinitionLoader.load(api_definition)
            split_definitions = self.splitter.split(raw_definition)
            merged_definitions = self.merger.merge(split_definitions)

            for definition in merged_definitions:
                self.logger.debug(f"\nType: {definition['type']}")
                self.logger.debug(f"Path: {definition['path']}")
                self.logger.debug(f"Verb: {definition['verb']}")

            self.logger.info("Successfully processed API definition.")
            return merged_definitions
        except Exception as e:
            self.logger.error(f"Error processing API definition: {e}")
            raise
