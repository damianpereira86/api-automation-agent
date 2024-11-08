from config import load_environment
from cli import parse_arguments, get_user_choice
from framework_generator import FrameworkGenerator


def main():
    try:
        print("🚀 Starting the API Framework Generation Process! 🌟")

        try:
            args = parse_arguments()
            load_environment()
            generator = FrameworkGenerator(
                args.api_file_path, args.destination_folder, args.endpoint
            )
            generate_tests = get_user_choice()
            api_definitions = generator.process_api_definition()
            generator.setup_framework()
            generator.create_env_file(api_definitions[0])
            generator.process_definitions(api_definitions, generate_tests)
            generator.run_final_checks(generate_tests)
        except FileNotFoundError as e:
            print(f"Error: File not found - {e}")
            return
        except PermissionError as e:
            print(f"Error: Permission denied - {e}")
            return
        except ValueError as e:
            print(f"Error: Invalid data - {e}")
            return
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return

    except Exception as e:
        print(f"A critical error occurred: {e}")
        raise


if __name__ == "__main__":
    main()
