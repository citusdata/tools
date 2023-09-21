import os

import docker
import pathlib2
import pytest

from ..common_tool_methods import remove_prefix, run, run_with_output
from ..publish_docker import (
    decode_triggering_event_info,
    GithubTriggerEventSource,
    decode_tag_parts,
    get_image_tag,
    DockerImageType,
    publish_main_docker_images,
    publish_tagged_docker_images,
    publish_nightly_docker_image,
)

NON_DEFAULT_BRANCH_NAME = "10.0.3_test"
DEFAULT_BRANCH_NAME = "master"
TAG_NAME = "v12.0.0"
INVALID_TAG_NAME = "v12.x"
DOCKER_IMAGE_NAME = "citusdata/citus"
docker_client = docker.from_env()

BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
EXEC_PATH = f"{BASE_PATH}/docker"


def initialize_env():
    if not os.path.exists("docker"):
        run("git clone https://github.com/citusdata/docker.git")


def test_decode_triggering_event_info():
    event_source, branch_name = decode_triggering_event_info(
        f"refs/heads/{NON_DEFAULT_BRANCH_NAME}"
    )
    assert (
        event_source == GithubTriggerEventSource.branch_push
        and branch_name == NON_DEFAULT_BRANCH_NAME
    )

    event_source, tag_name = decode_triggering_event_info(f"refs/tags/{TAG_NAME}")
    assert event_source == GithubTriggerEventSource.tag_push and tag_name == TAG_NAME


def test_decode_tag_parts():
    tag_parts = decode_tag_parts(TAG_NAME)
    assert (
        len(tag_parts) == 3
        and tag_parts[0] == "12"
        and tag_parts[1] == "0"
        and tag_parts[2] == "0"
    )

    with pytest.raises(ValueError):
        decode_tag_parts(INVALID_TAG_NAME)


def test_get_image_tag():
    image_name = get_image_tag(remove_prefix(TAG_NAME, "v"), DockerImageType.latest)
    assert image_name == "12.0.0"

    image_name = get_image_tag(
        remove_prefix(TAG_NAME, "v"), DockerImageType.postgres_15
    )
    assert image_name == "12.0.0-pg15"


def test_publish_main_docker_images():
    initialize_env()
    os.chdir("docker")

    try:
        run_with_output("git checkout -b docker-unit-test")
        publish_main_docker_images(DockerImageType.latest, False)
        docker_client.images.get("citusdata/citus:latest")
    finally:
        run_with_output("git checkout master")
        run_with_output("git branch -D docker-unit-test")


def test_publish_tagged_docker_images_latest():
    initialize_env()
    os.chdir("docker")
    try:
        run_with_output("git checkout -b docker-unit-test")
        publish_tagged_docker_images(DockerImageType.latest, "v12.0.0", False)
        docker_client.images.get("citusdata/citus:12")
        docker_client.images.get("citusdata/citus:12.0")
        docker_client.images.get("citusdata/citus:12.0.0")
    finally:
        run_with_output("git checkout master")
        run_with_output("git branch -D docker-unit-test")


def test_publish_tagged_docker_images_alpine():
    initialize_env()
    os.chdir("docker")
    try:
        run_with_output("git checkout -b docker-unit-test")
        publish_tagged_docker_images(DockerImageType.alpine, TAG_NAME, False)
        docker_client.images.get("citusdata/citus:12-alpine")
        docker_client.images.get("citusdata/citus:12.0-alpine")
        docker_client.images.get("citusdata/citus:12.0.0-alpine")
    finally:
        run_with_output("git checkout master")
        run_with_output("git branch -D docker-unit-test")


def test_publish_nightly_docker_image():
    initialize_env()
    os.chdir("docker")
    try:
        run_with_output("git checkout -b docker-unit-test")
        publish_nightly_docker_image(False)
        docker_client.images.get("citusdata/citus:nightly")
    finally:
        run_with_output("git checkout master")
        run_with_output("git branch -D docker-unit-test")


def clear_env():
    if os.path.exists("../docker"):
        os.chdir("..")
        run("chmod -R 777 docker")
        run("sudo rm -rf docker")
