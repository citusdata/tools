import argparse
import os
from enum import Enum
from typing import Tuple, List

import docker
import pathlib2
from parameters_validation import validate_parameters

from .common_tool_methods import remove_prefix, get_current_branch, is_tag_on_branch
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
    postgres_13 = 5


class ManualTriggerType(Enum):
    main = 1
    tags = 2
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
    DockerImageType.postgres_13: {"file-name": "postgres-13/Dockerfile", "docker-tag": "pg13",
                                  "schedule-type": ScheduleType.regular},
    DockerImageType.nightly: {"file-name": "nightly/Dockerfile", "docker-tag": "nightly",
                              "schedule-type": ScheduleType.nightly}}
DOCKER_IMAGE_NAME = "citusdata/citus"

docker_client = docker.from_env()

docker_api_client = docker.APIClient()


def regular_images_to_be_built(docker_image_type: DockerImageType = None) -> List[DockerImageType]:
    if docker_image_type:
        return [docker_image_type]
    return [key for key, value in docker_image_info_dict.items() if
            value["schedule-type"] == ScheduleType.regular]


# When pipeline triggered, if the event source is
# triggered by branch push or a schedule on pipeline, github_ref format is : refs/heads/{branch_name}
# if tiggered by tag push, github_ref format is: refs/heads/{tag_name}
def decode_triggering_event_info(github_ref: str) -> Tuple[GithubTriggerEventSource, str]:
    parts = github_ref.split("/")
    if len(parts) != 3 or parts[1] not in ("tags", "heads"):
        raise ValueError(
            "github ref should be like one of the following two formats: "
            "refs/heads/{branch_name}, refs/tags/{tag_name}")
    if parts[1] == "tags":
        return GithubTriggerEventSource.tag_push, parts[2]
    return GithubTriggerEventSource.branch_push, parts[2]


@validate_parameters
def decode_tag_parts(tag_name: is_tag(str)) -> List[str]:
    return remove_prefix(tag_name, "v").split(".")


def get_image_tag(tag_prefix: str, docker_image_type: DockerImageType) -> str:
    tag_suffix = ("" if docker_image_type == DockerImageType.latest else
                  f"-{docker_image_info_dict[docker_image_type]['docker-tag']}")
    return f"{tag_prefix}{tag_suffix}"


def publish_docker_image_on_push(docker_image_type: DockerImageType, github_ref: str, will_image_be_published: bool):
    triggering_event_info, resource_name = decode_triggering_event_info(github_ref)
    for regular_image_type in regular_images_to_be_built(docker_image_type):
        if triggering_event_info == GithubTriggerEventSource.branch_push:
            publish_main_docker_images(regular_image_type, will_image_be_published)
        else:
            publish_tagged_docker_images(regular_image_type, resource_name, will_image_be_published)


def publish_docker_image_on_schedule(docker_image_type: DockerImageType, will_image_be_published: bool):
    if docker_image_type == DockerImageType.nightly:
        publish_nightly_docker_image(will_image_be_published)
    else:
        for regular_image_type in regular_images_to_be_built(docker_image_type):
            publish_main_docker_images(regular_image_type, will_image_be_published)


def publish_docker_image_manually(manual_trigger_type_param: ManualTriggerType, will_image_be_published: bool,
                                  docker_image_type: DockerImageType, tag_name: str = "") -> None:
    if manual_trigger_type_param == ManualTriggerType.main and not tag_name:
        for it in regular_images_to_be_built(docker_image_type):
            publish_main_docker_images(it, will_image_be_published)
    elif manual_trigger_type_param == ManualTriggerType.tags and tag_name:
        for it in regular_images_to_be_built(docker_image_type):
            publish_tagged_docker_images(it, tag_name, will_image_be_published)
    elif manual_trigger_type_param == ManualTriggerType.nightly:
        publish_nightly_docker_image(will_image_be_published)


def publish_main_docker_images(docker_image_type: DockerImageType, will_image_be_published: bool):
    print(f"Building main docker image for {docker_image_type.name}...")
    docker_image_name = f"{DOCKER_IMAGE_NAME}:{docker_image_type.name}"
    _, logs = docker_client.images.build(dockerfile=docker_image_info_dict[docker_image_type]['file-name'],
                                         tag=docker_image_name,
                                         path=".")
    for log in logs:
        log_str = log.get("stream")
        if log_str:
            print(log_str, end='')
    print(f"Main docker image for {docker_image_type.name} built.")
    if will_image_be_published:
        print(f"Publishing main docker image for {docker_image_type.name}...")
        docker_client.images.push(DOCKER_IMAGE_NAME, tag=docker_image_type.name)
        print(f"Publishing main docker image for {docker_image_type.name} finished")
    else:
        current_branch = get_current_branch(os.getcwd())
        if current_branch != DEFAULT_BRANCH_NAME:
            print(
                f"Since current branch {current_branch} is not equal to "
                f"{DEFAULT_BRANCH_NAME} {docker_image_name} will not be pushed.")


def publish_tagged_docker_images(docker_image_type, tag_name: str, will_image_be_published: bool):
    print(f"Building and publishing tagged image {docker_image_type.name} for tag {tag_name}...")
    tag_parts = decode_tag_parts(tag_name)
    tag_version_part = ""
    docker_image_name = f"{DOCKER_IMAGE_NAME}:{docker_image_type.name}"
    _, logs = docker_client.images.build(dockerfile=docker_image_info_dict[docker_image_type]['file-name'],
                                         tag=docker_image_name,
                                         path=".")
    for log in logs:
        log_str = log.get("stream")
        if log_str:
            print(log_str, end='')
    print(f"{docker_image_type.name} image built.Now starting tagging and pushing...")
    for tag_part in tag_parts:
        tag_version_part = tag_version_part + tag_part
        image_tag = get_image_tag(tag_version_part, docker_image_type)
        print(f"Tagging {docker_image_name} with the tag {image_tag}...")
        docker_api_client.tag(docker_image_name, docker_image_name, image_tag)
        print(f"Tagging {docker_image_name} with the tag {image_tag} finished.")
        if will_image_be_published:
            print(f"Pushing {docker_image_name} with the tag {image_tag}...")
            push_logs = docker_client.images.push(DOCKER_IMAGE_NAME, tag=image_tag)
            print("Push logs:")
            print(push_logs)
            print(f"Pushing {docker_image_name} with the tag {image_tag} finished")
        else:
            print(
                f"Skipped pushing {docker_image_type} with the tag {image_tag} since will_image_be_published flag is false")

        tag_version_part = tag_version_part + "."
    print(f"Building and publishing tagged image {docker_image_type.name} for tag {tag_name} finished.")


def publish_nightly_docker_image(will_image_be_published: bool):
    print("Building nightly image...")
    docker_image_name = f"{DOCKER_IMAGE_NAME}:{docker_image_info_dict[DockerImageType.nightly]['docker-tag']}"
    _, logs = docker_client.images.build(dockerfile=docker_image_info_dict[DockerImageType.nightly]['file-name'],
                                         tag=docker_image_name,
                                         path=".")
    for log in logs:
        log_str = log.get("stream")
        if log_str:
            print(log_str, end='')
    print("Nightly image build finished.")

    if will_image_be_published:
        print("Pushing nightly image...")
        docker_client.images.push(DOCKER_IMAGE_NAME, tag=docker_image_info_dict[DockerImageType.nightly]['docker-tag'])
        print("Nightly image push finished.")
    else:
        print("Nightly image will not be pushed since will_image_be_published flag is false")


def validate_and_extract_general_parameters(docker_image_type_param: str, pipeline_trigger_type_param: str) -> Tuple[
    GithubPipelineTriggerType, DockerImageType]:
    try:
        trigger_type_param = GithubPipelineTriggerType[pipeline_trigger_type_param]
    except KeyError:
        raise ValueError(
            f"trigger_type parameter is invalid. Valid ones are "
            f"{','.join([d.name for d in GithubPipelineTriggerType])}.") from KeyError

    image_type_invalid_error_message = (
        f"image_type parameter is invalid. Valid ones are {','.join([d.name for d in regular_images_to_be_built()])}.")
    try:

        if docker_image_type_param == "all" or not docker_image_type_param:
            docker_image_type = None
        else:
            docker_image_type = DockerImageType[docker_image_type_param]
    except KeyError:
        raise ValueError(image_type_invalid_error_message) from KeyError

    return trigger_type_param, docker_image_type


def validate_and_extract_manual_exec_params(manual_trigger_type_param: str, tag_name_param: str) -> ManualTriggerType:
    try:
        manual_trigger_type_param = ManualTriggerType[manual_trigger_type_param]
    except KeyError:
        raise ValueError(
            f"manual_trigger_type parameter is invalid. "
            f"Valid ones are {','.join([d.name for d in ManualTriggerType])}.") from KeyError

    is_tag(tag_name_param)

    return manual_trigger_type_param


def get_image_publish_status(github_ref: str, is_test: bool):
    if is_test:
        return False
    triggering_event_info, resource_name = decode_triggering_event_info(github_ref)
    if triggering_event_info == GithubTriggerEventSource.tag_push:
        if not is_tag_on_branch(tag_name=resource_name, branch_name=DEFAULT_BRANCH_NAME):
            return False
        return True
    current_branch = get_current_branch(os.getcwd())
    if current_branch != DEFAULT_BRANCH_NAME:
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--github_ref', required=True)
    parser.add_argument('--pipeline_trigger_type', choices=[e.name for e in GithubPipelineTriggerType], required=True)
    parser.add_argument('--tag_name', nargs='?', default="")
    parser.add_argument('--manual_trigger_type', choices=[e.name for e in ManualTriggerType])
    parser.add_argument('--image_type', choices=[e.name for e in DockerImageType])
    parser.add_argument('--is_test', action="store_true")
    args = parser.parse_args()

    pipeline_trigger_type, image_type = validate_and_extract_general_parameters(args.image_type,
                                                                                args.pipeline_trigger_type)
    if args.is_test:
        print("Script is working in test mode. Images will not be published")

    publish_status = get_image_publish_status(args.github_ref, args.is_test)
    if pipeline_trigger_type == GithubPipelineTriggerType.workflow_dispatch:
        manual_trigger_type = validate_and_extract_manual_exec_params(args.manual_trigger_type, args.tag_name)
        publish_docker_image_manually(manual_trigger_type_param=manual_trigger_type,
                                      will_image_be_published=publish_status,
                                      docker_image_type=image_type, tag_name=args.tag_name)
    elif pipeline_trigger_type == GithubPipelineTriggerType.push:
        publish_docker_image_on_push(image_type, args.github_ref, publish_status)
    else:
        publish_docker_image_on_schedule(image_type, publish_status)
