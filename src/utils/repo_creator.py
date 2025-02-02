import os
import logging
import base64
import requests
import fnmatch

GITHUB_API_URL = "https://api.github.com"


def create_github_repo(repo_name, github_token):
    logger = logging.getLogger(__name__)

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"name": repo_name, "private": False, "auto_init": False}

    response = requests.post(f"{GITHUB_API_URL}/user/repos", json=data, headers=headers)

    if response.status_code == 201:
        repo_url = response.json()["html_url"]
        logger.info(f"✅ Repository '{repo_name}' created successfully at {repo_url}")
        return repo_url, response.json()["full_name"]
    else:
        logger.error(f"❌ Failed to create repository: {response.json()}")
        return None, None


def read_gitignore(repo_path):
    gitignore_path = os.path.join(repo_path, ".gitignore")
    ignored_patterns = []

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as gitignore_file:
            for line in gitignore_file:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignored_patterns.append(line)

    return ignored_patterns


def should_ignore(file_path, repo_path, ignored_patterns):
    rel_path = os.path.relpath(file_path, repo_path)
    for pattern in ignored_patterns:
        if fnmatch.fnmatch(rel_path, pattern) or rel_path.startswith(pattern):
            return True
    return False


def upload_file_to_github(owner_repo, file_path, repo_path, github_token):
    logger = logging.getLogger(__name__)

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    with open(file_path, "rb") as file:
        file_content = base64.b64encode(file.read()).decode("utf-8")

    relative_path = os.path.relpath(file_path, repo_path)
    github_api_url = f"{GITHUB_API_URL}/repos/{owner_repo}/contents/{relative_path}"

    data = {"message": f"Add {relative_path}", "content": file_content}

    response = requests.put(github_api_url, json=data, headers=headers)

    if response.status_code in [200, 201]:
        return True
    else:
        logger.error(f"❌ Failed to upload {relative_path}: {response.json()}")
        return False


def upload_directory_to_github(owner_repo, repo_path, github_token):
    logger = logging.getLogger(__name__)

    ignored_patterns = read_gitignore(repo_path)
    logged_folders = set()

    success = True
    for root, dirs, files in os.walk(repo_path):
        for dir_name in dirs[:]:
            dir_path = os.path.join(root, dir_name)
            base_folder = os.path.relpath(dir_path, repo_path).split(os.sep)[0]

            if (
                should_ignore(dir_path, repo_path, ignored_patterns)
                and base_folder not in logged_folders
            ):
                logger.info(f"🚫 Skipping ignored folder: {base_folder}/*")
                logged_folders.add(base_folder)
                dirs[:] = [
                    d
                    for d in dirs
                    if not should_ignore(
                        os.path.join(root, d), repo_path, ignored_patterns
                    )
                ]

        for file in files:
            file_path = os.path.join(root, file)
            if should_ignore(file_path, repo_path, ignored_patterns):
                continue

            if not upload_file_to_github(
                owner_repo, file_path, repo_path, github_token
            ):
                success = False

    if success:
        logger.info(
            f"🚀 All allowed files successfully uploaded to GitHub: {owner_repo}"
        )
    else:
        logger.error("❌ Some files failed to upload!")

    return success
