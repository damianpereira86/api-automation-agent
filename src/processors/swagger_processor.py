from typing import Dict, List, Union

from .swagger import APIDefinitionMerger, APIDefinitionSplitter, FileLoader
from ..utils.logger import Logger


class SwaggerProcessor:
    """Processes API definitions by orchestrating file loading, splitting, and merging."""

    def __init__(
        self,
        file_loader: FileLoader,
        splitter: APIDefinitionSplitter,
        merger: APIDefinitionMerger,
    ):
        """
        Initialize the SwaggerProcessor.

        Args:
            file_loader (FileLoader): Service to load API definition files.
            splitter (APIDefinitionSplitter): Service to split API definitions.
            merger (APIDefinitionMerger): Service to merge API definitions.
        """
        self.file_loader = file_loader
        self.splitter = splitter
        self.merger = merger
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
            self.logger.info(f"Starting API processing")
            raw_definition = self.file_loader.load(api_file_path)
            split_definitions = self.splitter.split(raw_definition)
            merged_definitions = self.merger.merge(split_definitions)
            self.logger.info(f"Successfully processed API definition.")
            return merged_definitions
        except Exception as e:
            self.logger.error(f"Error processing API definition: {e}")
            raise
