from typing import Dict, List, Union

from .swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    FileLoader,
    SwaggerURLProcessor,
)
from ..utils.logger import Logger


class SwaggerProcessor:
    """Processes API definitions by orchestrating file loading, splitting, and merging."""

    def __init__(
        self,
        file_loader: FileLoader,
        splitter: APIDefinitionSplitter,
        merger: APIDefinitionMerger,
        getSwaggerData: SwaggerURLProcessor = None,
    ):
        """
        Initialize the SwaggerProcessor.

        Args:
            file_loader (FileLoader): Service to load API definition files.
            splitter (APIDefinitionSplitter): Service to split API definitions.
            merger (APIDefinitionMerger): Service to merge API definitions.
            getSwaggerData (SwaggerURLProcessor): Service to get API definition from URL.
        """
        self.file_loader = file_loader
        self.splitter = splitter
        self.merger = merger
        self.getSwaggerData = getSwaggerData or SwaggerURLProcessor()
        self.logger = Logger.get_logger(__name__)

    def process_api_definition(
        self, api_file_path: str
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Processes an API definition by loading, splitting, and merging its components.

        Args:
            api_file_path (str): Path to the API definition file.

        Returns:
            List of merged API definitions.
        """
        try:
            self.logger.info("Starting API processing")
            swagger_spec = self.getSwaggerData.getApiSpecification(api_file_path)
            if isinstance(swagger_spec, dict):
                raw_definition = swagger_spec
            else:
                raw_definition = self.file_loader.load(swagger_spec)
            split_definitions = self.splitter.split(raw_definition)
            merged_definitions = self.merger.merge(split_definitions)
            for definition in merged_definitions:
                self.logger.debug(f"\nType: {definition['type']}")
                self.logger.debug(f"Path: {definition['path']}")
                self.logger.debug(f"Verb: {definition['verb']}")

            self.logger.info(f"Successfully processed API definition.")
            return merged_definitions
        except Exception as e:
            self.logger.error(f"Error processing API definition: {e}")
            raise
