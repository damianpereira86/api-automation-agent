import argparse
from datetime import datetime


def parse_arguments():
    parser = argparse.ArgumentParser(description="API Framework Generation Tool")
    parser.add_argument(
        "api_file_path", help="The path of the OpenAPI definition file to process."
    )
    parser.add_argument(
        "--destination-folder",
        type=str,
        default=f"./generated-framework_{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        help="Destination folder in which the files will be created (optional).",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        help="Specify the endpoint to generate the framework for (optional).",
    )
    return parser.parse_args()


def get_user_choice():
    print("\nPlease choose an option:")
    print("1. Generate Models")
    print("2. Generate Models and Tests")

    choice = input("Enter your choice (1 or 2): ").strip()
    if choice not in ["1", "2"]:
        raise ValueError("Invalid choice")

    return choice == "2"  # Returns True if tests should be generated
