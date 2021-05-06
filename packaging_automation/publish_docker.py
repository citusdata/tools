from .common_tool_methods import *


class GithubPipelineTriggerType(Enum):
    push = 1
    schedule = 2
    workflow_dispatch = 3


class DockerImageType(Enum):
    latest = 1
    alpine = 2
    nightly = 3
    postgres_12 = 4


docker_image_files = {DockerImageType.latest: "Dockerfile", DockerImageType.alpine: "alpine/Dockerfile",
                      DockerImageType.nightly: "nightly/Dockerfile",
                      DockerImageType.postgres_12: "postgres-12/Dockerfile"}


def publish_docker_image(docker_image_type: DockerImageType, github_pipeline_trigger_type: GithubPipelineTriggerType,
                         github_ref: str):
    if github_pipeline_trigger_type in (GithubPipelineTriggerType.push, GithubPipelineTriggerType.schedule):
        print("")
        # build docker image
        # if current_branch == default
    elif github_pipeline_trigger_type == GithubPipelineTriggerType.workflow_dispatch:
        print("")
    else:
        raise ValueError("Unsupported Trigger Type")
