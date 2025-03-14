import requests


class SwaggerURLProcessor:
    """Downloads Swagger JSON from a URL and saves in memory."""

    def getApiSpecification(self, path: str) -> str:
        if path.startswith("https") and path.endswith(".json"):
            response = requests.get(path)
            if response.status_code == 200:
                swagger_data = response.json()
                return swagger_data
            else:
                raise Exception(f"Error fetching Swagger JSON: {response.status_code}")
        else:
            return path
