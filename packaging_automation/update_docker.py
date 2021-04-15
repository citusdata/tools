import os
import argparse

from .common_tool_methods import *


def process_docker_template_file(project_version: str, templates_path: str, template_file_path: str):
    minor_version = get_minor_project_version(project_version)
    env = get_template_environment(templates_path)
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


def update_nightly_docker_file(project_version: str, template_path: str, exec_path: str):
    content = process_docker_template_file(project_version, template_path,
                                           "nightly/nightly.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/nightly/Dockerfile"
    write_to_file(content, dest_file_name)


def update_docker_file_for_postgres12(project_version: str, template_path: str, exec_path: str):
    content = process_docker_template_file(project_version, template_path,
                                           "postgres-12/postgres-12.tmpl.dockerfile")
    dest_file_name = f"{exec_path}/postgres-12/Dockerfile"
    write_to_file(content, dest_file_name)


def update_all_docker_files(project_version: str, template_path: str, exec_path: str):
    update_docker_file_for_latest_postgres(project_version, template_path, exec_path)
    update_regular_docker_compose_file(project_version, template_path, exec_path)
    update_docker_file_alpine(project_version, template_path, exec_path)
    update_nightly_docker_file(project_version, template_path, exec_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver')
    args = parser.parse_args()

    execution_path = os.getcwd()
    templ_path = f"{execution_path}/tools/python/template/docker"
    update_all_docker_files(args.prj_ver, templ_path, execution_path)
