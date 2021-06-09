import argparse
import os.path
from enum import Enum
from typing import Tuple, List

import docker
import pathlib2
from parameters_validation import validate_parameters

from .common_tool_methods import get_current_branch, remove_prefix
from .common_validations import is_tag

BASE_PATH = pathlib2.Path(__file__).parents[1]


class GithubPipelineTriggerType(Enum):
    push = 1
    schedule = 2
    workflow_dispatch = 3


class GithubTriggerEventSource(Enum):
    branch_push = 1
    tag_push = 2


class DockerImageType(Enum):
    latest = 1
    alpine = 2
    nightly = 3
    postgres_12 = 4


class ManualTriggerType(Enum):
    main = 1,
    tags = 2,
    nightly = 3


class ScheduleType(Enum):
    regular = 1
    nightly = 2


DEFAULT_BRANCH_NAME = "master"
docker_image_info_dict = {
    DockerImageType.latest: {"file-name": "Dockerfile", "docker-tag": "latest", "schedule-type": ScheduleType.regular},
    DockerImageType.alpine: {"file-name": "alpine/Dockerfile", "docker-tag": "alpine",
                             "schedule-type": ScheduleType.regular},
    DockerImageType.postgres_12: {"file-name": "postgres-12/Dockerfile", "docker-tag": "pg12",
                                  "schedule-type": ScheduleType.regular},
    DockerImageType.nightly: {"file-name": "nightly/Dockerfile", "docker-tag": "nightly",
                              "schedule-type": ScheduleType.nightly}}
DOCKER_IMAGE_NAME = "citusdata/citus"

docker_client = docker.from_env()

docker_api_client = docker.APIClient()


def regular_images_to_be_built(docker_image_type: DockerImageType = None) -> List[DockerImageType]:
    if docker_image_type:
        return [docker_image_type]
    return [it for it in docker_image_info_dict.keys() if
            docker_image_info_dict[it]["schedule-type"] == ScheduleType.regular]


# When pipeline triggered, if the event source is
# triggered by branch push or a schedule on pipeline, github_ref format is : refs/heads/{branch_name}
# if tiggered by tag push, github_ref format is: refs/heads/{tag_name}
def decode_triggering_event_info(github_ref: str) -> Tuple[GithubTriggerEventSource, str]:
    parts = github_ref.split("/")
    if len(parts) != 3 or parts[1] not in ("tags", "heads"):
        raise ValueError(
            "github ref should be like one of the following two formats: "
            "refs/heads/{branch_name}, refs/tags/{tag_name}")
    else:
        if parts[1] == "tags":
            return GithubTriggerEventSource.tag_push, parts[2]
        else:
            return GithubTriggerEventSource.branch_push, parts[2]


@validate_parameters
def decode_tag_parts(tag_name: is_tag(str)) -> List[str]:
    return remove_prefix(tag_name, "v").split(".")


def get_image_tag(tag_prefix: str, docker_image_type: DockerImageType) -> str:
    tag_suffix = ("" if docker_image_type == DockerImageType.latest else
                  f"-{docker_image_info_dict[docker_image_type]['docker-tag']}")
    return f"{tag_prefix}{tag_suffix}"


def publish_docker_image_on_push(docker_image_type: DockerImageType, github_ref: str, exec_path: str, ):
    triggering_event_info, resource_name = decode_triggering_event_info(github_ref)
    for docker_image_type in regular_images_to_be_built(docker_image_type):
        if triggering_event_info == GithubTriggerEventSource.branch_push:
            publish_main_docker_images(docker_image_type, exec_path)
        else:
            publish_tagged_docker_images(docker_image_type, resource_name, exec_path)


def publish_docker_image_on_schedule(docker_image_type: DockerImageType, exec_path: str, ):
    if docker_image_type == DockerImageType.nightly:
        publish_nightly_docker_image()
    else:
        for docker_image_type in regular_images_to_be_built(docker_image_type):
            publish_main_docker_images(docker_image_type, exec_path)


def publish_docker_image_manually(manual_trigger_type_param: ManualTriggerType, exec_path: str,
                                  docker_image_type: DockerImageType, tag_name: str = "") -> None:
    if manual_trigger_type_param == ManualTriggerType.main and not tag_name:
        for it in regular_images_to_be_built(docker_image_type):
            publish_main_docker_images(it, exec_path)
    elif manual_trigger_type_param == ManualTriggerType.tags and tag_name:
        for it in regular_images_to_be_built(docker_image_type):
            publish_tagged_docker_images(it, tag_name, exec_path)
    elif manual_trigger_type_param == ManualTriggerType.nightly:
        publish_nightly_docker_image()


def publish_main_docker_images(docker_image_type: DockerImageType, exec_path: str):
    current_branch = get_current_branch(exec_path)
    docker_image_name = f"{DOCKER_IMAGE_NAME}:{docker_image_type.name}"
    docker_client.images.build(dockerfile=docker_image_info_dict[docker_image_type]['file-name'],
                               tag=docker_image_name,
                               path=".")
    if current_branch.name == DEFAULT_BRANCH_NAME:
        docker_client.images.push(DOCKER_IMAGE_NAME, tag=docker_image_type.name)


def publish_tagged_docker_images(docker_image_type, tag_name: str, exec_path: str):
    current_branch = get_current_branch(exec_path)
    tag_parts = decode_tag_parts(tag_name)
    tag_version_part = ""
    docker_image_name = f"{DOCKER_IMAGE_NAME}:{docker_image_type.name}"
    docker_client.images.build(dockerfile=docker_image_info_dict[docker_image_type]['file-name'],
                               tag=docker_image_name,
                               path=".")
    for tag_part in tag_parts:
        tag_version_part = tag_version_part + tag_part
        image_tag = get_image_tag(tag_version_part, docker_image_type)
        docker_api_client.tag(docker_image_name, docker_image_name, image_tag)
        if current_branch.name == DEFAULT_BRANCH_NAME:
            docker_client.images.push(DOCKER_IMAGE_NAME, tag=image_tag)
        tag_version_part = tag_version_part + "."


def publish_nightly_docker_image():
    docker_image_name = f"{DOCKER_IMAGE_NAME}:{docker_image_info_dict[DockerImageType.nightly]['docker-tag']}"
    docker_client.images.build(dockerfile=docker_image_info_dict[DockerImageType.nightly]['file-name'],
                               tag=docker_image_name,
                               path=".")
    docker_client.images.push(DOCKER_IMAGE_NAME, tag=docker_image_info_dict[DockerImageType.nightly]['docker-tag'])


def validate_and_extract_general_parameters(docker_image_type_param: str, pipeline_trigger_type_param: str,
                                            exec_path_param: str) -> Tuple[GithubPipelineTriggerType, DockerImageType]:
    try:
        trigger_type_param = GithubPipelineTriggerType[pipeline_trigger_type_param]
    except KeyError:
        raise ValueError(
            f"trigger_type parameter is invalid. Valid ones are "
            f"{','.join([d.name for d in GithubPipelineTriggerType])}.")

    image_type_invalid_error_message = (
        f"image_type parameter is invalid. Valid ones are {','.join([d.name for d in regular_images_to_be_built()])}.")
    try:

        if docker_image_type_param == "all" or not docker_image_type_param:
            docker_image_type = None
        elif docker_image_type_param == "nightly":
            raise ValueError(image_type_invalid_error_message)
        else:
            docker_image_type = DockerImageType[docker_image_type_param]
    except KeyError:
        raise ValueError(image_type_invalid_error_message)
    if not exec_path_param and not os.path.exists(exec_path_param):
        raise ValueError(
            f"exec_path is invalid. exec_path should be non-empty value and "
            f"there should be a directory with this name on the server")
    return trigger_type_param, docker_image_type


def validate_and_extract_manual_exec_params(manual_trigger_type_param: str, tag_name_param: str) -> ManualTriggerType:
    try:
        manual_trigger_type_param = ManualTriggerType[manual_trigger_type_param]
    except KeyError:
        raise ValueError(
            f"manual_trigger_type parameter is invalid. Valid ones are {','.join([d.name for d in ManualTriggerType])}.")

    is_tag(tag_name_param)

    return manual_trigger_type_param


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--github_ref')
    parser.add_argument('--pipeline_trigger_type', choices=[e.name for e in GithubPipelineTriggerType], required=True)
    parser.add_argument('--tag_name', nargs='?', default="")
    parser.add_argument('--exec_path')
    parser.add_argument('--manual_trigger_type', choices=[e.name for e in ManualTriggerType])
    parser.add_argument('--image_type', choices=[e.name for e in DockerImageType])
    args = parser.parse_args()

    pipeline_trigger_type, image_type = validate_and_extract_general_parameters(args.image_type,
                                                                                args.pipeline_trigger_type,
                                                                                args.exec_path)
    if pipeline_trigger_type == GithubPipelineTriggerType.workflow_dispatch:
        manual_trigger_type = validate_and_extract_manual_exec_params(args.manual_trigger_type, args.tag_name)
        publish_docker_image_manually(manual_trigger_type_param=manual_trigger_type, exec_path=args.exec_path,
                                      docker_image_type=image_type, tag_name=args.tag_name)
    elif pipeline_trigger_type == GithubPipelineTriggerType.push:
        publish_docker_image_on_push(image_type, args.github_ref, args.exec_path)
    else:
        publish_docker_image_on_schedule(image_type, args.exec_path)
