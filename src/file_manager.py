import shutil

def copy_framework_template(destination_folder):
    """
    Copy the API framework template to a new folder.
    """
    src_folder = "./api-framework-template"
    print("\nGenerating new framework...")
    try:
        shutil.copytree(src_folder, destination_folder)
        print(
            f"\033[92mFramework template generated successfully at {destination_folder}\033[0m"
        )
        return destination_folder
    except Exception as e:
        print(f"\033[91mError copying folder: {e}\033[0m")
