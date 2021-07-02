import docker

docker_client = docker.from_env()

docker_client.ping()
