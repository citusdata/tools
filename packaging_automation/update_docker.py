import argparse
import os
import uuid
from datetime import datetime
from enum import Enum
from dotenv import dotenv_values
from typing import Tuple

import pathlib2

from .common_tool_methods import (process_template_file_with_minor, write_to_file, run, initialize_env, create_pr,
                                  remove_cloned_code, DEFAULT_ENCODING_FOR_FILE_HANDLING, DEFAULT_UNICODE_ERROR_HANDLER,
                                  get_minor_project_version_for_docker)

REPO_OWNER = "citusdata"
PROJECT_NAME = "docker"
MAIN_BRANCH = "master"


class SupportedDockerImages(Enum):
    latest = 1
    docker_compose = 2
    alpine = 3
    postgres13 = 4
    postgres14 = 5


docker_templates = {SupportedDockerImages.latest: "latest/latest.tmpl.dockerfile",
                    SupportedDockerImages.docker_compose: "latest/docker-compose.tmpl.yml",
                    SupportedDockerImages.alpine: "alpine/alpine.tmpl.dockerfile",
                    SupportedDockerImages.postgres13: "postgres-13/postgres-13.tmpl.dockerfile",
                    SupportedDockerImages.postgres14: "postgres-13/postgres-14.tmpl.dockerfile"}

docker_outputs = {SupportedDockerImages.latest: "Dockerfile",
                  SupportedDockerImages.docker_compose: "docker-compose.yml",
                  SupportedDockerImages.alpine: "alpine/Dockerfile",
                  SupportedDockerImages.postgres13: "postgres-13/Dockerfile",
                  SupportedDockerImages.postgres14: "postgres-14/Dockerfile"}

BASE_PATH = pathlib2.Path(__file__).parent.absolute()


def update_docker_file_for_latest_postgres(project_version: str, template_path: str, exec_path: str,
                                           postgres_version: str):
    minor_version = get_minor_project_version_for_docker(project_version)
    debian_project_version = project_version.replace("_", "-")
    content = process_template_file_with_minor(debian_project_version, template_path,
                                               docker_templates[SupportedDockerImages.latest], minor_version,
                                               postgres_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.latest]}"
    write_to_file(content, dest_file_name)


def update_regular_docker_compose_file(project_version: str, template_path: str, exec_path: str):
    minor_version = get_minor_project_version_for_docker(project_version)
    content = process_template_file_with_minor(project_version, template_path,
                                               docker_templates[SupportedDockerImages.docker_compose], minor_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.docker_compose]}"
    write_to_file(content, dest_file_name)


def update_docker_file_alpine(project_version: str, template_path: str, exec_path: str, postgres_version: str):
    minor_version = get_minor_project_version_for_docker(project_version)
    content = process_template_file_with_minor(project_version, template_path,
                                               docker_templates[SupportedDockerImages.alpine], minor_version,
                                               postgres_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.alpine]}"
    write_to_file(content, dest_file_name)


def update_docker_file_for_postgres13(project_version: str, template_path: str, exec_path: str, postgres_version: str):
    minor_version = get_minor_project_version_for_docker(project_version)
    debian_project_version = project_version.replace("_", "-")
    content = process_template_file_with_minor(debian_project_version, template_path,
                                               docker_templates[SupportedDockerImages.postgres13], minor_version,
                                               postgres_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.postgres13]}"
    create_directory_if_not_exists(dest_file_name)
    write_to_file(content, dest_file_name)


def update_docker_file_for_postgres14(project_version: str, template_path: str, exec_path: str, postgres_version: str):
    minor_version = get_minor_project_version_for_docker(project_version)
    debian_project_version = project_version.replace("_", "-")
    content = process_template_file_with_minor(debian_project_version, template_path,
                                               docker_templates[SupportedDockerImages.postgres14], minor_version,
                                               postgres_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.postgres14]}"
    create_directory_if_not_exists(dest_file_name)
    write_to_file(content, dest_file_name)


def create_directory_if_not_exists(dest_file_name):
    dir_name = os.path.dirname(dest_file_name)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


def get_new_changelog_entry(project_version: str, postgres_version: str = ""):
    header = f"### citus-docker v{project_version}.docker ({datetime.strftime(datetime.now(), '%B %d,%Y')}) ###\n"
    citus_bump_str = f"\n* Bump Citus version to {project_version}\n"
    postgres_bump_str = f"\n* Bump PostgreSQL version to {postgres_version}\n"

    changelog_entry = f"{header}{citus_bump_str}"
    if postgres_version:
        changelog_entry = f"{changelog_entry}{postgres_bump_str}"
    changelog_entry = f"{changelog_entry}\n"
    return changelog_entry


def update_changelog(project_version: str, exec_path: str, postgres_version: str = ""):
    latest_changelog = get_new_changelog_entry(project_version, postgres_version)
    changelog_file_path = f"{exec_path}/CHANGELOG.md"
    with open(changelog_file_path, "r+", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        if not (f"({project_version}" in reader.readline()):
            reader.seek(0, 0)
            old_changelog = reader.read()
            changelog = f"{latest_changelog}{old_changelog}"
            reader.seek(0, 0)
            reader.write(changelog)
        else:
            raise ValueError(f"Already using version {project_version} in the changelog")


def update_all_docker_files(project_version: str, exec_path: str):
    template_path = f"{BASE_PATH}/templates/docker"
    pkgvars_file = f"{exec_path}/pkgvars"

    postgres_15_version, postgres_14_version, postgres_13_version = read_postgres_versions(pkgvars_file)

    latest_postgres_version = postgres_15_version

    update_docker_file_for_latest_postgres(project_version, template_path, exec_path, latest_postgres_version)
    update_regular_docker_compose_file(project_version, template_path, exec_path)
    update_docker_file_alpine(project_version, template_path, exec_path, latest_postgres_version)
    update_docker_file_for_postgres13(project_version, template_path, exec_path, postgres_13_version)
    update_docker_file_for_postgres14(project_version, template_path, exec_path, postgres_14_version)
    update_changelog(project_version, exec_path, latest_postgres_version)


def read_postgres_versions(pkgvars_file: str) -> Tuple[str, str, str]:
    if os.path.exists(pkgvars_file):
        config = dotenv_values(pkgvars_file)
        return config["postgres_15_version"], config["postgres_14_version"], config["postgres_13_version"]

    return "14.1", "13.5", "12.9"


CHECKOUT_DIR = "docker_temp"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver', required=True)
    parser.add_argument('--gh_token', required=True)
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument('--exec_path')
    parser.add_argument('--is_test', action="store_true")
    args = parser.parse_args()

    if args.pipeline:
        if not args.exec_path:
            raise ValueError("exec_path should be defined")
        execution_path = args.exec_path
    else:
        execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
        initialize_env(execution_path, PROJECT_NAME, execution_path)

    os.chdir(execution_path)
    pr_branch = f"release-{args.prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    update_all_docker_files(args.prj_ver, execution_path)
    run("git add .")

    commit_message = f"Bump docker to version {args.prj_ver}"
    run(f'git commit -m "{commit_message}"')
    if not args.is_test:
        run(f'git push --set-upstream origin {pr_branch}')
        create_pr(args.gh_token, pr_branch, commit_message, REPO_OWNER, PROJECT_NAME, MAIN_BRANCH)
        remove_cloned_code(execution_path)
