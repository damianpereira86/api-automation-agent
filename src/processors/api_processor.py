from abc import ABC, abstractmethod


class APIProcessor(ABC):
    @abstractmethod
    def process_api_definition(self, api_file_path):
        pass

    @abstractmethod
    def get_api_verbs(self, api_definition):
        pass

    @abstractmethod
    def get_api_paths(self, api_definition, endpoints=None):
        pass

    @abstractmethod
    def get_relevant_models(self, all_models, api_verb):
        pass

    @abstractmethod
    def get_other_models(self, all_models, api_verb):
        pass

    @abstractmethod
    def get_api_path_content(self, api_path_definition):
        pass

    @abstractmethod
    def get_api_verb_content(self, api_verb_definition):
        pass

    @abstractmethod
    def get_api_verb_rootpath(self, api_verb_definition):
        pass

    @abstractmethod
    def get_api_verb_path(self, api_verb_definition):
        pass

    @abstractmethod
    def get_api_path_name(self, api_path):
        pass

    @abstractmethod
    def get_api_verb_name(self, api_verb):
        pass

    @abstractmethod
    def extract_env_vars(self, api_defintions):
        pass
