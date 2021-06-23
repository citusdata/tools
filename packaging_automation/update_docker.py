import argparse
import uuid
import os
from datetime import datetime

from github import Github

from .common_tool_methods import (process_template_file, write_to_file, run, initialize_env)

REPO_OWNER = "citusdata"
PROJECT_NAME = "docker"
CHECKOUT_PATH = "docker_temp"


def update_docker_file_for_latest_postgres(project_version: str, template_path: str, exec_path: str,
                                           postgres_version: str):
    content = process_template_file(project_version, template_path,
                                    "latest/latest.tmpl.dockerfile", postgres_version)
    dest_file_name = f"{exec_path}/Dockerfile"
    write_to_file(content, dest_file_name)


def update_regular_docker_compose_file(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path,
                                    "latest/docker-compose.tmpl.yml")
    dest_file_name = f"{exec_path}/docker-compose.yml"
    write_to_file(content, dest_file_name)


def update_docker_file_alpine(project_version: str, template_path: str, exec_path: str, postgres_version: str):
    content = process_template_file(project_version, template_path,
                                    "alpine/alpine.tmpl.dockerfile", postgres_version)
    dest_file_name = f"{exec_path}/alpine/Dockerfile"
    write_to_file(content, dest_file_name)


def update_docker_file_for_postgres12(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path,
                                    "postgres-12/postgres-12.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/postgres-12/Dockerfile"
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
            raise ValueError("Already version in the changelog")


def update_all_docker_files(project_version: str, tools_path: str, exec_path: str, postgres_version: str):
    template_path = f"{tools_path}/packaging_automation/templates/docker"
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
            content = reader.read()
            lines = content.splitlines()
            for line in lines:
                if line.startswith("latest_postgres_version"):
                    line_parts = line.split("=")
                    if len(line_parts) != 2:
                        raise ValueError("keys and values should be seperated with '=' sign")
                    else:
                        postgres_version = line_parts[1]
                else:
                    raise ValueError("pkgvars file should include a line with key latest_postgres_version")
    else:
        # Setting it because pkgvars does not exist initially
        postgres_version = "13.2"
    return postgres_version


def update_pkgvars(project_version: str, template_path: str, pkgvars_file: str, postgres_version: str):
    if postgres_version:
        content = process_template_file(project_version, template_path, "docker-pkgvars.tmpl", postgres_version)
        with open(pkgvars_file, "w") as writer:
            writer.write(content)


CHECKOUT_DIR = "docker_temp"


def create_pr():
    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{PROJECT_NAME}")
    repository.create_pull(title=f"Bump Citus to {args.prj_ver}", base="master",
                           head=pr_branch, body="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver', required=True)
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--postgres_version')
    parser.add_argument('--is_test', action="store_true")
    args = parser.parse_args()

    execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
    github_token = args.gh_token

    tools_path = os.getcwd()

    initialize_env(execution_path, PROJECT_NAME, CHECKOUT_PATH)
    os.chdir(execution_path)
    run("git checkout master")
    pr_branch = f"release-{args.prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    update_all_docker_files(args.prj_ver, tools_path, execution_path, args.postgres_version)
    run("git add .")
    run(f'git commit -m "Bump to version {args.prj_ver}"')
    if not args.is_test:
        run(f'git push --set-upstream origin {pr_branch}')

    if not args.is_test:
        create_pr()
