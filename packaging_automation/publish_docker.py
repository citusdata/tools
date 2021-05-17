import argparse
import os.path
from enum import Enum
from typing import Tuple, List

import pathlib2
from parameters_validation import validate_parameters

from .common_tool_methods import get_current_branch, remove_prefix
from .common_validations import is_tag
import docker

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


DEFAULT_BRANCH_NAME = "master"
docker_image_info_dict = {
    DockerImageType.latest: {"file-name": "Dockerfile", "docker-tag": "latest", "trigger": "push"},
    DockerImageType.alpine: {"file-name": "alpine/Dockerfile", "docker-tag": "alpine",
                             "trigger": "push"},
    DockerImageType.postgres_12: {"file-name": "postgres-12/Dockerfile", "docker-tag": "pg12",
                                  "trigger": "push"},
    DockerImageType.nightly: {"file-name": "nightly/Dockerfile", "docker-tag": "nightly",
                              "trigger": "schedule"}}
DOCKER_IMAGE_NAME = "citusdata/citus"

docker_client = docker.from_env()

docker_api_client = docker.APIClient()


# When pipeline triggered, if the event source is
# triggered by branch push or a schedule on pipeline, github_ref format is : refs/heads/{branch_name}
# tiggered by tag push, github_ref format is: refs/heads/{tag_name}
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


def publish_docker_image_automatically(docker_image_type: DockerImageType,
                                       github_pipeline_trigger_type: GithubPipelineTriggerType,
                                       github_ref: str, exec_path: str):
    if github_pipeline_trigger_type == GithubPipelineTriggerType.push:

        triggering_event_info, resource_name = decode_triggering_event_info(github_ref)
        if triggering_event_info == GithubTriggerEventSource.branch_push:
            publish_main_docker_images(docker_image_type, exec_path)
        else:
            publish_tagged_docker_images(docker_image_type, resource_name, exec_path)
    elif github_pipeline_trigger_type == GithubPipelineTriggerType.schedule:
        if docker_image_type == DockerImageType.nightly:
            publish_nightly_docker_image()
        else:
            publish_main_docker_images(docker_image_type, exec_path)
    else:
        raise ValueError("Unsupported Trigger Type")


def publish_docker_image_manually(manual_trigger_type_param: ManualTriggerType, exec_path: str,
                                  tag_name: str = "") -> None:
    non_nightly_image_info_types = [it for it in docker_image_info_dict.keys() if
                                    docker_image_info_dict[it]["trigger"] == "push"]
    if manual_trigger_type_param == ManualTriggerType.main and len(tag_name) == 0:
        for docker_image_info_type in non_nightly_image_info_types:
            publish_main_docker_images(docker_image_info_type, exec_path)
    elif manual_trigger_type_param == ManualTriggerType.main and len(tag_name) > 0:
        for docker_image_info_type in non_nightly_image_info_types:
            publish_tagged_docker_images(docker_image_info_type, tag_name, exec_path)
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
    docker_image_name = f"{DOCKER_IMAGE_NAME}"
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


def validate_and_extract_general_parameters(image_type_param: str, pipeline_trigger_type_param: str,
                                            args_exec_path: str):
    try:
        image_type_param = DockerImageType[image_type_param]
    except KeyError:
        raise ValueError(
            f"image_type parameter is invalid. Valid ones are {','.join([d.name for d in DockerImageType])}.")

    try:
        trigger_type_param = GithubPipelineTriggerType[pipeline_trigger_type_param]
    except KeyError:
        raise ValueError(
            f"trigger_type parameter is invalid. Valid ones are {','.join([d.name for d in GithubPipelineTriggerType])}.")

    if not args.exec_path and not os.path.exists(args.exec_path):
        raise ValueError(
            f"exec_path is invalid. exec_path should be non-empty value and "
            f"there should be a directory with this name on the server")
    return image_type_param, trigger_type_param


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
    parser.add_argument('--image_type')
    parser.add_argument('--github_ref')
    parser.add_argument('--pipeline_trigger_type')
    parser.add_argument('--tag_name')
    parser.add_argument('--exec_path')
    parser.add_argument('--manual_trigger_type')
    args = parser.parse_args()

    image_type, pipeline_trigger_type = validate_and_extract_general_parameters(args.image_type,
                                                                                args.pipeline_trigger_type,
                                                                                args.exec_path)
    if pipeline_trigger_type == GithubPipelineTriggerType.workflow_dispatch:
        manual_trigger_type = validate_and_extract_manual_exec_params(args.manual_trigger_type, args.tag_name)
        publish_docker_image_manually(manual_trigger_type_param=manual_trigger_type, exec_path=args.exec_path,
                                      tag_name=args.tag_name)
    else:
        publish_docker_image_automatically(image_type, pipeline_trigger_type, args.github_ref, args.exec_path)
