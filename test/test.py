from enum import Enum


class DockerImageType(Enum):
    latest = 1
    alpine = 2
    nightly = 3
    postgres_12 = 4


docker_image_files = {DockerImageType.latest: {"file_name": "Dockerfile", "image_name": "latest"},
                      DockerImageType.alpine: "alpine/Dockerfile",
                      DockerImageType.nightly: "nightly/Dockerfile",
                      DockerImageType.postgres_12: "postgres-12/Dockerfile"}

print(docker_image_files[DockerImageType.latest]["file_name"])
