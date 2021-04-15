import os

import pathlib2
from datetime import datetime

from .. import update_docker
from .. import common_tool_methods

BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_BASE_PATH = f"{BASE_PATH}/docker"
PROJECT_VERSION = "10.0.3"
PROJECT_NAME = "citus"
version_details = common_tool_methods.get_version_details(PROJECT_VERSION)
TEMPLATE_PATH = f"{BASE_PATH}/python/templates/docker"


def setup_module():
    if not os.path.exists("docker"):
        common_tool_methods.run("git clone https://github.com/citusdata/docker.git")


def teardown_module():
    if os.path.exists("docker"):
        common_tool_methods.run("chmod -R 777 docker")
        common_tool_methods.run("sudo rm -rf docker")


def file_controls(file_name: str):
    with open(file_name, "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[1].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert lines[19] in f"postgresql-$PG_MAJOR-{PROJECT_NAME}-" \
                            f"{version_details['major']}.{version_details['minor']}.=$CITUS_VERSION "
        assert len(lines) == 41


def test_update_docker_file_for_latest_postgres():
    update_docker.update_docker_file_for_latest_postgres(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    with open(f"{TEST_BASE_PATH}/Dockerfile", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[1].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert f"postgresql-$PG_MAJOR-{PROJECT_NAME}-" \
               f"{version_details['major']}.{version_details['minor']}.=$CITUS_VERSION" in lines[19]
        assert len(lines) == 40


def test_update_regular_docker_compose_file():
    update_docker.update_regular_docker_compose_file(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    parameterized_str = f"    image: 'citusdata/{PROJECT_NAME}:{PROJECT_VERSION}'"
    with open(f"{TEST_BASE_PATH}/docker-compose.yml", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[5] == parameterized_str
        assert lines[15] == parameterized_str
        assert len(lines) == 32


def test_update_docker_file_alpine():
    update_docker.update_docker_file_alpine(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    with open(f"{TEST_BASE_PATH}/alpine/Dockerfile", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[1].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert len(lines) == 53


def test_update_docker_file_for_postgres12():
    update_docker.update_docker_file_for_postgres12(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    with open(f"{TEST_BASE_PATH}/postgres-12/Dockerfile", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[1].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert f"postgresql-$PG_MAJOR-{PROJECT_NAME}-" \
               f"{version_details['major']}.{version_details['minor']}.=$CITUS_VERSION" in lines[19]
        assert len(lines) == 40


def test_update_changelog():
    update_docker.update_changelog(PROJECT_VERSION, TEST_BASE_PATH)
    with open(f"{TEST_BASE_PATH}/CHANGELOG.md", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[0] == f"### citus-docker v{PROJECT_VERSION}.docker " \
                           f"({datetime.strftime(datetime.now(), '%B %d,%Y')}) ###"
        assert lines[2] == f"* Bump Citus version to {PROJECT_VERSION}"
