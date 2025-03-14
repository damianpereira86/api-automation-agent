import os
import json
import requests


class SwaggerURLProcessor:
    """Downloads Swagger JSON from a URL and saves it locally."""

    def swaggerURL(path: str) -> str:
        if path.startswith("https") and path.endswith(".json"):
            response = requests.get(path)
            if response.status_code == 200:
                swagger_data = response.json()
                dest_folder = "api-definitions"
                os.makedirs(dest_folder, exist_ok=True)
                api_definitions_name = (
                    swagger_data.get("info", {})
                    .get("title", "api_definitions")
                    .replace(" ", "-")
                    .lower()
                )
                file_path = os.path.join(dest_folder, api_definitions_name + ".json")
                print("PATH:" + file_path)

                with open(file_path, "w", encoding="utf-8") as json_file:
                    json.dump(swagger_data, json_file, indent=4)
                return file_path
            else:
                raise Exception(f"Error fetching Swagger JSON: {response.status_code}")
        else:
            return path
