import os
import argparse
from datetime import datetime
from . import common_tool_methods
import uuid
from github import Repository, PullRequest, Github

REPO_OWNER = "citusdata"
PROJECT_NAME = "docker"


def process_docker_template_file(project_version: str, templates_path: str, template_file_path: str):
    minor_version = common_tool_methods.get_minor_project_version(project_version)
    env = common_tool_methods.get_template_environment(templates_path)
    template = env.get_template(template_file_path)
    return f"{template.render(project_version=project_version, project_minor_version=minor_version)}\n"


def write_to_file(content: str, dest_file_name: str):
    with open(dest_file_name, "w") as writer:
        writer.write(content)


def update_docker_file_for_latest_postgres(project_version: str, template_path: str, exec_path: str):
    content = process_docker_template_file(project_version, template_path,
                                           "latest/latest.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/Dockerfile"
    write_to_file(content, dest_file_name)


def update_regular_docker_compose_file(project_version: str, template_path: str, exec_path: str):
    content = process_docker_template_file(project_version, template_path,
                                           "latest/docker-compose.tmpl.yml")
    dest_file_name = f"{exec_path}/docker-compose.yml"
    write_to_file(content, dest_file_name)


def update_docker_file_alpine(project_version: str, template_path: str, exec_path: str):
    content = process_docker_template_file(project_version, template_path,
                                           "alpine/alpine.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/alpine/Dockerfile"
    write_to_file(content, dest_file_name)


def update_docker_file_for_postgres12(project_version: str, template_path: str, exec_path: str):
    content = process_docker_template_file(project_version, template_path,
                                           "postgres-12/postgres-12.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/postgres-12/Dockerfile"
    write_to_file(content, dest_file_name)


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
    template_path = f"{tools_path}/python/templates/docker"
    update_docker_file_for_latest_postgres(project_version, template_path, exec_path)
    update_regular_docker_compose_file(project_version, template_path, exec_path)
    update_docker_file_alpine(project_version, template_path, exec_path)
    update_docker_file_for_postgres12(project_version, template_path, exec_path)
    update_changelog(project_version, exec_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver')
    args = parser.parse_args()

    os.chdir("..")
    execution_path = os.getenv("EXEC_PATH", default=os.getcwd())
    tool_path = os.getenv("TOOLS_PATH", default=f"{execution_path}/tools")
    print(f"Exec Path: {execution_path}")
    print(f"Tool Path: {tool_path}")
    github_token = os.getenv("GH_TOKEN")

    if github_token is None or github_token == "":
        raise ValueError("Github Token should be provided")

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