import json
import re
import copy

from src.configuration.config import Config
from src.processors.api_processor import APIProcessor
from src.services.llm_service import LLMService


class PostmanProcessor(APIProcessor):
    """Processes V2 Postman collection .json"""

    service_dict = {}
    numeric_only = r"^\d+$"

    def __init__(self, llm_service: LLMService, config: Config):
        self.llm_service = llm_service
        self.config = config

    def process_api_definition(self, json_file_path):
        with open(json_file_path, encoding="utf-8") as postman_json_export:
            data = json.load(postman_json_export)
            return self.extract_requests(data)

    def extract_env_vars(self, extracted_requests):
        env_vars = set()
        for request in extracted_requests:
            path = request.get("path", "")
            if path.startswith("{{"):
                match = re.match(r"\{\{(.*?)\}\}", path)
                if match:
                    env_vars.add(match.group(1))
                    break
        return list(env_vars)

    def get_api_paths(self, api_definition, endpoints=None):
        all_paths_no_query_params = self.get_all_distinct_paths_no_query_params(
            api_definition
        )

        verb_path_pairs = self._extract_verb_path_info(api_definition)

        paths_grouped_by_service = self._group_paths_by_service(
            all_paths_no_query_params
        )

        self.service_dict = self.map_verb_path_pairs_to_services(
            verb_path_pairs, paths_grouped_by_service
        )

        return copy.deepcopy(self.service_dict).items()

    def get_api_path_name(self, api_path):
        return api_path[0]

    def get_relevant_models(self, api_verb, all_models):
        result = []

        for model in all_models:
            if api_verb["service"] == model["path"]:
                result = [file["fileContent"] for file in model["models"]]

        return result

    def get_other_models(self, api_verb, all_models):
        result = []

        for model in all_models:
            if not api_verb["service"] == model["path"]:
                result.append(
                    {
                        "files": model["files"],
                    }
                )

    def _group_paths_by_service(self, all_distinct_paths_no_query_params):
        paths_grouped_by_service = self.llm_service.group_paths_by_service(
            all_distinct_paths_no_query_params
        )

        one_or_more_paths_left_out = True
        attempts = 0
        while (one_or_more_paths_left_out == True) and (
            attempts < 10  # TODO change for config.fix_json_retry
        ):

            if self._contains_same_items(
                all_distinct_paths_no_query_params,
                self._get_all_paths_from_service_dict(paths_grouped_by_service),
            ):
                one_or_more_paths_left_out = False
            else:
                paths_grouped_by_service = self.llm_service.group_paths_by_service(
                    all_distinct_paths_no_query_params
                )

                attempts = attempts + 1

        return paths_grouped_by_service

    def get_api_verb_path(self, api_verb_definition):
        return api_verb_definition["path"]

    def get_api_verb_name(self, api_verb_definition):
        return api_verb_definition["verb"]

    def get_api_verb_rootpath(self, api_verb_definition):
        return api_verb_definition["service"]

    def _contains_same_items(self, array1, array2):
        """
        Check if two arrays contain the same items
        """
        return sorted(array1) == sorted(array2)

    def _get_all_paths_from_service_dict(self, service_dict):
        all_paths = []
        for paths in service_dict.values():
            all_paths.extend(paths)
        return all_paths

    def get_api_verbs(self, api_definition):
        return self._add_service_name_to_verb_chunks(api_definition, self.service_dict)

    def get_api_verb_content(self, api_verb):
        return api_verb

    def get_api_path_content(self, api_path):
        return api_path

    def extract_requests(self, data, path=""):
        results = []

        def process_item(item, current_path):
            if isinstance(item, dict):
                if "item" in item and isinstance(item["item"], list):
                    new_path = (
                        f'{current_path}/{self._to_camel_case(item["name"])}'
                        if "name" in item
                        else current_path
                    )
                    for sub_item in item["item"]:
                        process_item(sub_item, new_path)
                elif self._item_is_a_test_case(item):
                    result = self._extract_request_data(item, current_path)
                    if result["name"] not in {r["name"] for r in results}:
                        results.append(result)
                else:
                    for sub_key, sub_value in item.items():
                        process_item(sub_value, current_path)
            elif isinstance(item, list):
                for sub_item in item:
                    process_item(sub_item, current_path)

        process_item(data, path)
        return results

    def map_verb_path_pairs_to_services(
        self, verb_path_pairs, no_query_params_routes_grouped_by_service
    ):
        verb_chunks_with_query_params = self._extract_verb_path_info(verb_path_pairs)

        verb_path_pairs_and_services = {}

        for verb_path_pair in verb_chunks_with_query_params:

            for service, routes in no_query_params_routes_grouped_by_service.items():

                if verb_path_pair["path"] in routes:

                    if service not in verb_path_pairs_and_services:
                        verb_path_pairs_and_services[service] = []

                    verb_path_pairs_and_services[service].append(
                        {
                            "verb": verb_path_pair["verb"],
                            "path": verb_path_pair["path"],
                            "query_params": verb_path_pair["query_params"],
                            "body": verb_path_pair["body"],
                        }
                    )

        return verb_path_pairs_and_services

    def _add_service_name_to_verb_chunks(self, verb_chunks, all_services_dict):
        verb_chunks_tagged_with_service = copy.deepcopy(verb_chunks)

        for verb_chunk in verb_chunks_tagged_with_service:

            for service, verbs in all_services_dict.items():

                routes_in_service = [verb["path"] for verb in verbs]

                verb_chunk_path_no_query_params = verb_chunk["path"].split("?")[0]

                if verb_chunk_path_no_query_params in routes_in_service:
                    verb_chunk["service"] = service
                    break

        return verb_chunks_tagged_with_service

    def get_all_distinct_paths_no_query_params(self, extracted_verb_chunks):
        distinct_paths_no_query_params = list(
            set([item["path"].split("?")[0] for item in extracted_verb_chunks])
        )

        return distinct_paths_no_query_params

    def _extract_verb_path_info(self, extracted_requests):

        result = []

        distinct_paths_no_query_params = self.get_all_distinct_paths_no_query_params(
            extracted_requests
        )

        for path_no_query_params in distinct_paths_no_query_params:

            verbs = []
            matching_full_paths = []

            for item in extracted_requests:

                if item["path"].startswith(path_no_query_params):
                    matching_full_paths.append(item)

                    if item["verb"] not in verbs:
                        verbs.append(item["verb"])

            for verb in verbs:

                all_query_params_on_verb_path = {}

                all_body_attributes_on_verb_path = {}

                for path_item in matching_full_paths:

                    if path_item["verb"] == verb:

                        if path_item["body"] is not None:
                            self._accumulate_request_body_attributes(
                                all_body_attributes_on_verb_path, path_item["body"]
                            )

                        path_sliced_on_query_param_start = path_item["path"].split("?")

                        if len(path_sliced_on_query_param_start) > 1:

                            all_query_params = path_sliced_on_query_param_start[
                                1
                            ].split("&")

                            if len(all_query_params) > 0:
                                self._accumulate_query_params(
                                    all_query_params_on_verb_path, all_query_params
                                )

                result.append(
                    {
                        "verb": verb,
                        "root_path": self._get_root_path(path_no_query_params),
                        "path": path_no_query_params,
                        "query_params": all_query_params_on_verb_path,
                        "body": all_body_attributes_on_verb_path,
                    }
                )

        return result

    def _accumulate_query_params(self, all_query_params, current_request_query_params):
        for param in current_request_query_params:

            param_array = param.split("=")
            param_name = param_array[0]

            if (param_name) and (param_name not in all_query_params):
                if len(param_array) > 1:
                    if re.match(PostmanProcessor.numeric_only, param_array[1]):
                        all_query_params[param_name] = "number"
                    else:
                        all_query_params[param_name] = "string"
            elif all_query_params[param_name] == "number" and len(param_array) > 1:
                if not re.match(PostmanProcessor.numeric_only, param_array[1]):
                    all_query_params[param_name] = "string"

    def _accumulate_request_body_attributes(
        self, all_body_attributes, current_request_body
    ):
        for key, value in current_request_body.items():
            if key not in all_body_attributes:
                if isinstance(value, str) and re.match(
                    PostmanProcessor.numeric_only, value
                ):
                    all_body_attributes[key] = "number"
                elif isinstance(value, str):
                    all_body_attributes[key] = "string"
                elif isinstance(value, dict):
                    all_body_attributes[f"{key}Object"] = self._map_object_attributes(
                        value
                    )
                elif isinstance(value, list):
                    all_body_attributes[f"{key}Object"] = "array"
            elif isinstance(value, str) and not re.match(
                PostmanProcessor.numeric_only, value
            ):
                all_body_attributes[key] = "string"

    def _to_camel_case(self, s: str) -> str:
        words = re.split(r"[^a-zA-Z0-9]", s)
        words = [word for word in words if word]
        if not words:
            return ""
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])

    def _extract_request_data(self, data, path):
        result = {
            "file_path": path,
            "path": "",
            "verb": "",
            "body": {},
            "prerequest": [],
            "script": [],
            "name": "",
        }

        if "request" in data and isinstance(data["request"], dict):

            result["verb"] = data["request"].get("method", "")

            if "url" in data["request"]:
                url_value = data["request"].get("url", "")
                raw_url_value = (
                    url_value["raw"] if isinstance(url_value, dict) else url_value
                )
                result["path"] = raw_url_value

            if "body" in data["request"]:
                try:
                    raw_body = data["request"]["body"].get("raw", "")
                    clean_json_body = json.loads(
                        raw_body.replace("\r", "").replace("\n", "")
                    )
                except (KeyError, json.JSONDecodeError):
                    clean_json_body = None
                result["body"] = clean_json_body

        if "event" in data and isinstance(data["event"], list):
            for script in data["event"]:
                if script.get("listen") == "test":
                    result["script"] = script.get("script", {}).get("exec", [])
                elif script.get("listen") == "prerequest":
                    result["prerequest"] = script.get("script", {}).get("exec", [])

        result["name"] = self._to_camel_case(data["name"])

        return result

    def _item_is_a_test_case(self, data: str):
        return "request" in data or (("event" in data) and ("request" in data))

    def _get_root_path(self, full_path):
        match = re.search(r"(?<!/)/([^/]+)/", full_path)
        if match:
            return match.group(1)
        else:
            return ""

    def _map_object_attributes(self, obj):
        mapped_attributes = {}

        for key, value in obj.items():
            if isinstance(value, str) and re.match(
                PostmanProcessor.numeric_only, value
            ):
                mapped_attributes[key] = "number"
            elif isinstance(value, str):
                mapped_attributes[key] = "string"
            elif isinstance(value, dict):
                mapped_attributes[f"{key}Object"] = self._map_object_attributes(value)
            elif isinstance(value, list):
                mapped_attributes[f"{key}Object"] = "array"

        return mapped_attributes
