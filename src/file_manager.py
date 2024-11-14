import os
import shutil


def create_files(files, parent_folder):
    """
    Create files from a list of dictionaries containing file paths and content.

    Args:
    - files (list): An array of dictionaries, each containing a 'path' and 'fileContent' key.
    - parent_folder (str): The parent folder to write the files to.
    """

    for item in files:
        file_path = item["path"]
        file_content = item["fileContent"]

        # Set generated-framework as the destination folder
        if file_path.startswith("./"):
            file_path = file_path[2:]
        updated_path = os.path.join(parent_folder, file_path)

        os.makedirs(os.path.dirname(updated_path), exist_ok=True)

        with open(updated_path, "w") as file:
            file.write(file_content)
        print(f"File written: {updated_path}")


def copy_framework_template(destination_folder):
    """
    Copy the API framework template to a new folder.
    """
    src_folder = "../api-framework-template"
    print("\nGenerating new framework...")
    try:
        shutil.copytree(src_folder, destination_folder)
        print(
            f"\033[92mFramework template generated successfully at {destination_folder}\033[0m"
        )
        return destination_folder
    except Exception as e:
        print(f"\033[91mError copying folder: {e}\033[0m")
