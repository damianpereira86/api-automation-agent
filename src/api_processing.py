import copy
import json

import yaml


def process_api_definition(api_file_path):
    """
    Loads and processes an API definition file, splitting and merging the definitions.

    Parameters:
        api_file_path (str): Path to the API definition file

    Returns:
        list: A list of merged API definitions
    """
    print("\nLoading API definition...")
    raw_api_definition = load_api_definition(api_file_path)
    api_definition_list = split_api_definitions(raw_api_definition)
    merged_api_definition_list = merge_api_definitions_by_base_resource(
        api_definition_list
    )
    print(f"\033[92mAPI definition processed successfully.\033[0m")
    return merged_api_definition_list


def load_api_definition(file_path):
    if not file_path or not isinstance(file_path, str):
        raise ValueError("Invalid file path")

    try:
        if file_path.endswith(".yml"):
            with open(file_path, "r") as file:
                raw_api_definition = yaml.safe_load(file)
        elif file_path.endswith(".json"):
            with open(file_path, "r") as file:
                raw_api_definition = json.load(file)
        else:
            raise ValueError("Unsupported file format")
    except FileNotFoundError:
        raise FileNotFoundError(f"API definition file not found: {file_path}")
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Error parsing file {file_path}: {str(e)}")

    return raw_api_definition


def split_api_definitions(api_definition):
    """
    Splits an OpenAPI definition into individual path and HTTP verb components,
    each represented as separate entries in a list.

    Parameters:
        api_definition (dict): The original OpenAPI definition in dictionary format.

    Returns:
        api_definition_list (list): A list of dictionaries where each dictionary
        represents a path or an HTTP verb with its associated YAML definition.
        Each entry in the list has the following keys:
            - type (str): Indicates whether the entry is a "base", "path" or a "verb".
            - path (str): The specific path in the API.
            - verb (str or None): The HTTP verb associated with the path. This is `None` for path entries.
            - yaml (str): The YAML string representation of the isolated path or verb.
    """
    api_definition_list = []

    base_copy = copy.deepcopy(api_definition)
    del base_copy["paths"]
    api_definition_list.append(_create_api_entry("base", None, None, base_copy))

    for path, path_data in api_definition["paths"].items():
        path_copy = copy.deepcopy(api_definition)
        path_copy["paths"] = {path: path_data}
        api_definition_list.append(_create_api_entry("path", path, None, path_copy))

        for verb in path_data.keys():
            verb_copy = copy.deepcopy(path_copy)
            verb_copy["paths"][path] = {verb: path_data[verb]}
            api_definition_list.append(
                _create_api_entry("verb", path, f"{verb.upper()}", verb_copy)
            )

    return api_definition_list


def merge_api_definitions_by_base_resource(api_definition_list):
    """
    Merges individual path and verb components of an API definition by their base resource,
    resulting in a combined list of merged API definitions.

    Parameters:
        api_definition_list (list): A list of dictionaries where each dictionary
        represents a path or an HTTP verb with its associated YAML definition.
        This list is typically generated by the `split_api_definitions` function.

    Returns:
        merged_api_definition_list (list): A list of merged API definitions.
        Each entry in the list represents either a merged path or an individual verb.
    """
    merged_definitions = {}
    for item in api_definition_list:
        if item["type"] == "path":
            base_path = "/" + item["path"].split("/", 2)[1]
            if base_path not in merged_definitions:
                item["path"] = base_path
                merged_definitions[base_path] = copy.deepcopy(item)
            else:
                item_yaml = yaml.safe_load(item["yaml"])
                merged_yaml = yaml.safe_load(merged_definitions[base_path]["yaml"])
                for path, path_data in item_yaml["paths"].items():
                    if path not in merged_yaml["paths"]:
                        merged_yaml["paths"].update({path: path_data})
                merged_definitions[base_path]["yaml"] = yaml.dump(
                    merged_yaml, sort_keys=False
                )
        elif item["type"] == "verb":
            merged_definitions[f"{item['path']}-{item['verb']}"] = copy.deepcopy(item)

    merged_api_definition_list = list(merged_definitions.values())

    return merged_api_definition_list


def _create_api_entry(entry_type, path, verb, yaml_content):
    """Helper function to create standardized API definition entries."""
    return {
        "type": entry_type,
        "path": path,
        "verb": verb,
        "yaml": yaml.dump(yaml_content, sort_keys=False),
    }
