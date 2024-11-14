from .utilities import run_command


def install_dependencies(destination_folder):
    """Install npm dependencies"""
    print("\nInstalling dependencies...")
    return run_command("npm install --loglevel=error", cwd=destination_folder)


def format_files(destination_folder):
    """Format the generated files"""
    print("\nFormatting files...")
    return run_command("npm run prettify", cwd=destination_folder)


def run_linter(destination_folder):
    """Run the linter with auto-fix"""
    print("\nRunning linter...")
    return run_command("npm run lint:fix", cwd=destination_folder)


def run_typescript_compiler(destination_folder):
    """Run the TypeScript compiler"""
    print("\nRunning TypeScript compiler...")
    return run_command("npx tsc --noEmit", cwd=destination_folder)


def run_typescript_compiler_for_files(files, destination_folder):
    """Run the TypeScript compiler for the given files"""
    file_paths = " ".join(file["path"] for file in files)
    print(f"Running TypeScript compiler for files: {file_paths}")
    return run_command(
        f"npx tsc {file_paths} --target ESNext --moduleResolution nodenext --module nodenext --esModuleInterop --skipLibCheck --isolatedModules --strict --noUnusedLocals --noUnusedParameters --noEmit",
        cwd=destination_folder,
    )


def run_tests(destination_folder):
    """Run the tests"""
    print("\nRunning tests...")
    return run_command("npm run test", cwd=destination_folder)


def run_specific_test(destination_folder, files):
    """Run a specific test"""
    file_paths = " ".join(file["path"] for file in files)
    print(f"\nRunning tests: {file_paths}")
    return run_command(f"mocha {file_paths} --timeout 10000", cwd=destination_folder)
