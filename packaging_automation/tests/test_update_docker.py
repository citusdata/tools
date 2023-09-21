import os
from datetime import datetime

import pathlib2

from ..common_tool_methods import (
    run,
    get_version_details,
    DEFAULT_ENCODING_FOR_FILE_HANDLING,
    DEFAULT_UNICODE_ERROR_HANDLER,
)
from dotenv import dotenv_values
from ..update_docker import (
    update_docker_file_for_latest_postgres,
    update_regular_docker_compose_file,
    update_docker_file_alpine,
    update_docker_file_for_postgres15,
    update_docker_file_for_postgres14,
    update_changelog,
)

BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_BASE_PATH = f"{BASE_PATH}/docker"
PROJECT_VERSION = "10.0.3"

POSTGRES_15_VERSION = "15.4"
POSTGRES_14_VERSION = "14.9"

PROJECT_NAME = "citus"
version_details = get_version_details(PROJECT_VERSION)
TEMPLATE_PATH = f"{BASE_PATH}/packaging_automation/templates/docker"
PKGVARS_FILE = f"{TEST_BASE_PATH}/pkgvars"


def setup_module():
    if not os.path.exists("docker"):
        run("git clone https://github.com/citusdata/docker.git")


def teardown_module():
    if os.path.exists("docker"):
        run("chmod -R 777 docker")
        run("sudo rm -rf docker")


def test_update_docker_file_for_latest_postgres():
    update_docker_file_for_latest_postgres(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_14_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_14_VERSION}"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert (
            f"postgresql-$PG_MAJOR-{PROJECT_NAME}-"
            f"{version_details['major']}.{version_details['minor']}=$CITUS_VERSION"
            in lines[21]
        )
        assert len(lines) == 42


def test_update_regular_docker_compose_file():
    update_regular_docker_compose_file(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    parameterized_str = f'    image: "citusdata/{PROJECT_NAME}:{PROJECT_VERSION}"'
    with open(
        f"{TEST_BASE_PATH}/docker-compose.yml",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[7] == parameterized_str
        assert lines[17] == parameterized_str
        assert len(lines) == 34


def test_update_docker_file_alpine():
    update_docker_file_alpine(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_14_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/alpine/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_14_VERSION}-alpine"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert len(lines) == 58


def test_update_docker_file_for_postgres14():
    update_docker_file_for_postgres14(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_14_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/postgres-14/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_14_VERSION}"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert (
            f"postgresql-$PG_MAJOR-{PROJECT_NAME}-"
            f"{version_details['major']}.{version_details['minor']}=$CITUS_VERSION"
            in lines[21]
        )
        assert len(lines) == 42


def test_update_docker_file_for_postgres13():
    update_docker_file_for_postgres15(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_15_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/postgres-13/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_15_VERSION}"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert (
            f"postgresql-$PG_MAJOR-{PROJECT_NAME}-"
            f"{version_details['major']}.{version_details['minor']}=$CITUS_VERSION"
            in lines[21]
        )
        assert len(lines) == 42


def test_update_changelog_with_postgres():
    update_changelog(PROJECT_VERSION, TEST_BASE_PATH)
    with open(
        f"{TEST_BASE_PATH}/CHANGELOG.md",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert (
            lines[0] == f"### citus-docker v{PROJECT_VERSION}.docker "
            f"({datetime.strftime(datetime.now(), '%B %d,%Y')}) ###"
        )
        assert lines[2] == f"* Bump Citus version to {PROJECT_VERSION}"


def test_update_changelog_without_postgres():
    with open(
        f"{TEST_BASE_PATH}/CHANGELOG.md",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert (
            lines[0] == f"### citus-docker v{PROJECT_VERSION}.docker "
            f"({datetime.strftime(datetime.now(), '%B %d,%Y')}) ###"
        )
        assert lines[2] == f"* Bump Citus version to {PROJECT_VERSION}"


def test_pkgvar_postgres_version_existence():
    config = dotenv_values(PKGVARS_FILE)
    assert config["postgres_15_version"]
    assert config["postgres_14_version"]
    assert config["postgres_13_version"]
