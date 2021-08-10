import argparse
import os
import uuid
from datetime import datetime
from enum import Enum
import pathlib2

from .common_tool_methods import (process_template_file, write_to_file, run, initialize_env, create_pr,
                                  remove_cloned_code)

REPO_OWNER = "citusdata"
PROJECT_NAME = "docker"
MAIN_BRANCH = "master"


class SupportedDockerImages(Enum):
    latest = 1,
    docker_compose = 2,
    alpine = 3,
    postgres12 = 4


docker_templates = {SupportedDockerImages.latest: "latest/latest.tmpl.dockerfile",
                    SupportedDockerImages.docker_compose: "latest/docker-compose.tmpl.yml",
                    SupportedDockerImages.alpine: "alpine/alpine.tmpl.dockerfile",
                    SupportedDockerImages.postgres12: "postgres-12/postgres-12.tmpl.dockerfile"}

docker_outputs = {SupportedDockerImages.latest: "Dockerfile",
                  SupportedDockerImages.docker_compose: "docker-compose.yml",
                  SupportedDockerImages.alpine: "alpine/Dockerfile",
                  SupportedDockerImages.postgres12: "postgres-12/Dockerfile"}

BASE_PATH = pathlib2.Path(__file__).parent.absolute()


def update_docker_file_for_latest_postgres(project_version: str, template_path: str, exec_path: str,
                                           postgres_version: str):
    content = process_template_file(project_version, template_path,
                                    docker_templates[SupportedDockerImages.latest], postgres_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.latest]}"
    write_to_file(content, dest_file_name)


def update_regular_docker_compose_file(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path,
                                    docker_templates[SupportedDockerImages.docker_compose])
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.docker_compose]}"
    write_to_file(content, dest_file_name)


def update_docker_file_alpine(project_version: str, template_path: str, exec_path: str, postgres_version: str):
    content = process_template_file(project_version, template_path,
                                    docker_templates[SupportedDockerImages.alpine], postgres_version)
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.alpine]}"
    write_to_file(content, dest_file_name)


def update_docker_file_for_postgres12(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path,
                                    docker_templates[SupportedDockerImages.postgres12])
    dest_file_name = f"{exec_path}/{docker_outputs[SupportedDockerImages.postgres12]}"
    write_to_file(content, dest_file_name)


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
    with open(changelog_file_path, "r+") as reader:
        if not (f"({project_version}" in reader.readline()):
            reader.seek(0, 0)
            old_changelog = reader.read()
            changelog = f"{latest_changelog}{old_changelog}"
            reader.seek(0, 0)
            reader.write(changelog)
        else:
            raise ValueError(f"Already using version {project_version} in the changelog")


def update_all_docker_files(project_version: str, exec_path: str, postgres_version: str):
    template_path = f"{BASE_PATH}/templates/docker"
    pkgvars_file = f"{exec_path}/pkgvars"

    if postgres_version:
        update_pkgvars(project_version, template_path, pkgvars_file, postgres_version)

    persisted_postgres_version = read_postgres_version(pkgvars_file)

    update_docker_file_for_latest_postgres(project_version, template_path, exec_path, persisted_postgres_version)
    update_regular_docker_compose_file(project_version, template_path, exec_path)
    update_docker_file_alpine(project_version, template_path, exec_path, persisted_postgres_version)
    update_docker_file_for_postgres12(project_version, template_path, exec_path)
    update_changelog(project_version, exec_path, postgres_version)


def read_postgres_version(pkgvars_file: str) -> str:
    if os.path.exists(pkgvars_file):
        with open(pkgvars_file, "r") as reader:
            lines = reader.readlines()
            for line in lines:
                if line.startswith("latest_postgres_version"):
                    line_parts = line.split("=")
                    if len(line_parts) != 2:
                        raise ValueError("keys and values should be seperated with '=' sign")
                    else:
                        postgres_version = line_parts[1].rstrip("\n")
                        break
            if not postgres_version:
                raise ValueError("pkgvars file should include a line with key latest_postgres_version")
    else:
        # Setting it because pkgvars does not exist initially
        postgres_version = "13.2"
    return postgres_version


def update_pkgvars(project_version: str, template_path: str, pkgvars_file: str, postgres_version: str):
    content = process_template_file(project_version, template_path, "docker-pkgvars.tmpl", postgres_version)
    with open(pkgvars_file, "w") as writer:
        writer.write(content)


CHECKOUT_DIR = "docker_temp"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver', required=True)
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--postgres_version')
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument('--exec_path')
    parser.add_argument('--is_test', action="store_true")
    args = parser.parse_args()

    if args.pipeline:
        if not args.exec_path:
            raise ValueError(f"exec_path should be defined")
        execution_path = args.exec_path
    else:
        execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
        initialize_env(execution_path, PROJECT_NAME, execution_path)

    os.chdir(execution_path)
    pr_branch = f"release-{args.prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    update_all_docker_files(args.prj_ver, execution_path, args.postgres_version)
    run("git add .")

    commit_message = f"Bump docker to version {args.prj_ver}"
    run(f'git commit -m "{commit_message}"')
    if not args.is_test:
        run(f'git push --set-upstream origin {pr_branch}')
        create_pr(args.gh_token, pr_branch, commit_message, REPO_OWNER, PROJECT_NAME, MAIN_BRANCH)
    if not args.pipeline and not args.is_test:
        remove_cloned_code(execution_path)
