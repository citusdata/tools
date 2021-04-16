import argparse
import uuid
from datetime import datetime

from github import Github

from . import common_tool_methods

REPO_OWNER = "citusdata"
PROJECT_NAME = "docker"





def update_docker_file_for_latest_postgres(project_version: str, template_path: str, exec_path: str):
    print(f"Template Path:{template_path}")
    content = common_tool_methods.process_docker_template_file(project_version, template_path,
                                                               "latest/latest.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/Dockerfile"
    common_tool_methods.write_to_file(content, dest_file_name)


def update_regular_docker_compose_file(project_version: str, template_path: str, exec_path: str):
    content = common_tool_methods.process_docker_template_file(project_version, template_path,
                                                               "latest/docker-compose.tmpl.yml")
    dest_file_name = f"{exec_path}/docker-compose.yml"
    common_tool_methods.write_to_file(content, dest_file_name)


def update_docker_file_alpine(project_version: str, template_path: str, exec_path: str):
    content = common_tool_methods.process_docker_template_file(project_version, template_path,
                                                               "alpine/alpine.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/alpine/Dockerfile"
    common_tool_methods.write_to_file(content, dest_file_name)


def update_docker_file_for_postgres12(project_version: str, template_path: str, exec_path: str):
    content = common_tool_methods.process_docker_template_file(project_version, template_path,
                                                               "postgres-12/postgres-12.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/postgres-12/Dockerfile"
    common_tool_methods.write_to_file(content, dest_file_name)


def get_new_changelog_entry(project_version):
    return f"### citus-docker v{project_version}.docker ({datetime.strftime(datetime.now(), '%B %d,%Y')}) ###" \
           f"\n\n* Bump Citus version to {project_version}\n\n"


def update_changelog(project_version: str, exec_path: str):
    latest_changelog = get_new_changelog_entry(project_version)
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


def update_all_docker_files(project_version: str, tools_path: str, exec_path: str):
    template_path = f"{tools_path}/packaging_automation/templates/docker"
    update_docker_file_for_latest_postgres(project_version, template_path, exec_path)
    update_regular_docker_compose_file(project_version, template_path, exec_path)
    update_docker_file_alpine(project_version, template_path, exec_path)
    update_docker_file_for_postgres12(project_version, template_path, exec_path)
    update_changelog(project_version, exec_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver')
    parser.add_argument('--exec_path')
    parser.add_argument('--tools_path')
    parser.add_argument('--gh_token')
    args = parser.parse_args()

    execution_path = args.exec_path
    tool_path = args.tools_path
    github_token = args.gh_token

    print(f"Exec Path: {execution_path}")

    if github_token is None or github_token == "":
        raise ValueError("Github Token should be provided")
    if execution_path is None or execution_path == "":
        raise ValueError("Execution Path should be provided")
    if tool_path is None or tool_path == "":
        tool_path = f"{execution_path}/tools"
        print(f"Tools path is not provided. Default value is set: {tool_path}")

    common_tool_methods.run("git checkout master")
    pr_branch = f"release-{args.prj_ver}-{uuid.uuid4()}"
    common_tool_methods.run(f"git checkout -b {pr_branch}")

    update_all_docker_files(args.prj_ver, tool_path, execution_path)

    common_tool_methods.run(f'git commit -a -m "Bump to version {args.prj_ver}"')
    common_tool_methods.run(f'git push --set-upstream origin {pr_branch}')

    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{PROJECT_NAME}")

    pr_result = repository.create_pull(title=f"Bump Citus to {args.prj_ver}", base="master",
                                       head=pr_branch, body="")
