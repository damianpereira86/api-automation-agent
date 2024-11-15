import os
import sys
import subprocess


def run_command(command, cwd=None):
    """Run a shell command and print its output in real-time"""
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # Unbuffered
            universal_newlines=True,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )

        output_lines = []
        while True:
            output = process.stdout.readline()
            if output:
                output_lines.append(output.rstrip())
                print(output.rstrip(), flush=True)  # Force flush after each line

            if output == "" and process.poll() is not None:
                break

        success = process.returncode == 0
        if success:
            print(f"\033[92mCommand succeeded.\033[0m")
        else:
            print(f"\033[91mCommand failed.\033[0m")
        return success, "\n".join(output_lines)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return False, str(e)


def run_command_with_fix(command_func, fix_func, files, *args, **kwargs):
    """
    Generic retry function that attempts to run a command and recovers from failures.

    Args:
        command_func: Function that returns (success, message) tuple
        fix_func: Function to call when command fails, receives files and message as parameters
        files: Files to pass to fix_func
        max_retries: Maximum number of retry attempts (default: 3)
        *args, **kwargs: Additional arguments to pass to command_func

    Returns:
        tuple: (success, messages) from the last attempt
    """
    retry_count = 0
    max_retries = kwargs.get("max_retries", 3)
    while retry_count < max_retries:
        print(f"\nAttempt {retry_count + 1}/{max_retries}.")
        result = command_func(files, *args, **kwargs)
        success, messages = result

        if success:
            return result

        if fix_func:
            fix_func(files, messages)
        retry_count += 1

    result = command_func(files, *args, **kwargs)
    if not result[0]:
        print(f"Command failed after {max_retries} attempts.")
    return result
