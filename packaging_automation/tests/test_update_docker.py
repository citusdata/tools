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
    update_docker_file_for_postgres17,
    update_docker_file_for_postgres18,
    update_docker_file_for_postgres19,
    update_changelog,
)

BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_BASE_PATH = f"{BASE_PATH}/docker"
PROJECT_VERSION = "12.0.0"

POSTGRES_19_VERSION = "19.0"
POSTGRES_18_VERSION = "18.1"
POSTGRES_17_VERSION = "17.6"

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
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_19_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_19_VERSION}"
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
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_19_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/alpine/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_19_VERSION}-alpine"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert len(lines) == 58


def test_update_docker_file_for_postgres17():
    update_docker_file_for_postgres17(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_17_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/postgres-17/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_17_VERSION}"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert (
            f"postgresql-$PG_MAJOR-{PROJECT_NAME}-"
            f"{version_details['major']}.{version_details['minor']}=$CITUS_VERSION"
            in lines[21]
        )
        assert len(lines) == 42


def test_update_docker_file_for_postgres18():
    update_docker_file_for_postgres18(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_18_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/postgres-18/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_18_VERSION}"
        assert lines[3].strip() == f"ARG VERSION={PROJECT_VERSION}"
        assert (
            f"postgresql-$PG_MAJOR-{PROJECT_NAME}-"
            f"{version_details['major']}.{version_details['minor']}=$CITUS_VERSION"
            in lines[21]
        )
        assert len(lines) == 42


def test_update_docker_file_for_postgres19():
    update_docker_file_for_postgres19(
        PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH, POSTGRES_19_VERSION
    )
    with open(
        f"{TEST_BASE_PATH}/postgres-19/Dockerfile",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2].strip() == f"FROM postgres:{POSTGRES_19_VERSION}"
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
    assert config["postgres_17_version"]
    assert config["postgres_18_version"]
    assert config["postgres_19_version"]
