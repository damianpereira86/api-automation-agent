class EndpointLister:
    """
    Utility class for listing API endpoints.

    This class provides a static method to process an API definition and list available API paths.
    """

    @staticmethod
    def list_endpoints(api_definition):
        """
        Process the API definition and logs each unique API path.
        """
        endpoints_dict = {endpoint["path"] for endpoint in api_definition if endpoint.get("type") == "path"}

        print("\nEndpoints that can be used with the --endpoints flag:")
        for path in sorted(endpoints_dict):
            message = f"- {path}"
            print(message)
