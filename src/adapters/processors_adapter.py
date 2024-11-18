from dependency_injector import containers, providers

from src.processors.swagger import APIDefinitionMerger, APIDefinitionSplitter, FileLoader
from src.processors.swagger_processor import SwaggerProcessor


class ProcessorsAdapter(containers.DeclarativeContainer):
    """Container for Swagger processing components."""

    file_loader = providers.Factory(
        FileLoader
    )
    splitter = providers.Factory(
        APIDefinitionSplitter
    )
    merger = providers.Factory(
        APIDefinitionMerger
    )
    swagger_processor = providers.Factory(
        SwaggerProcessor,
        file_loader=file_loader,
        splitter=splitter,
        merger=merger
    )
