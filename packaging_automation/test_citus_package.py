import argparse
import os
import subprocess
import shlex
import requests
from enum import Enum
import sys
from typing import List

from .common_tool_methods import (
    get_supported_postgres_release_versions,
    get_minor_version,
)

POSTGRES_MATRIX_FILE = "postgres-matrix.yml"
POSTGRES_MATRIX_WEB_ADDRESS = "https://raw.githubusercontent.com/citusdata/packaging/all-citus-unit-tests/postgres-matrix.yml"


def run_command(command: str) -> int:
    with subprocess.Popen(
        shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as process:
        for line in iter(process.stdout.readline, b""):  # b'\n'-separated lines
            print(line.decode("utf-8"), end=" ")
    exitcode = process.wait()
    return exitcode


class TestPlatform(Enum):
    el_7 = {"name": "el/7", "docker_image_name": "el-7"}
    el_8 = {"name": "el/8", "docker_image_name": "el-8"}
    centos_8 = {"name": "centos/8", "docker_image_name": "centos-8"}
    centos_7 = {"name": "centos/7", "docker_image_name": "centos-7"}
    ol_7 = {"name": "ol/7", "docker_image_name": "ol-7"}
    ol_8 = {"name": "ol/8", "docker_image_name": "ol-8"}
    debian_buster = {
        "name": "debian/buster",
        "docker_image_name": "debian-buster",
    }
    debian_bullseye = {
        "name": "debian/bullseye",
        "docker_image_name": "debian-bullseye",
    }
    debian_stretch = {"name": "debian/stretch", "docker_image_name": "debian-stretch"}
    ubuntu_bionic = {"name": "ubuntu/bionic", "docker_image_name": "ubuntu-bionic"}
    ubuntu_focal = {"name": "ubuntu/focal", "docker_image_name": "ubuntu-focal"}
    undefined = {"name": "undefined", "docker_image_name": "undefined"}


def get_test_platform_for_os_release(os_release: str) -> TestPlatform:
    result = TestPlatform.undefined
    for tp in TestPlatform:
        if tp.value["name"] == os_release:
            result = tp
    return result


def get_postgres_versions_from_matrix_file(project_version: str) -> List[str]:
    r = requests.get(POSTGRES_MATRIX_WEB_ADDRESS, allow_redirects=True)

    with open(POSTGRES_MATRIX_FILE, "wb") as writer:
        writer.write(r.content)
    pg_versions = get_supported_postgres_release_versions(
        POSTGRES_MATRIX_FILE, project_version
    )

    return pg_versions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_version", required=True)
    parser.add_argument("--pg_major_version")
    parser.add_argument("--os_release", choices=[t.value["name"] for t in TestPlatform])

    args = parser.parse_args()
    test_platform = get_test_platform_for_os_release(args.os_release)
    minor_project_version = get_minor_version(args.project_version)

    platform = args.os_release

    postgres_versions = get_postgres_versions_from_matrix_file(args.project_version)

    print(f"This version of Citus supports following pg versions: {postgres_versions}")

    os.chdir("test-images")
    return_codes = {}

    if args.pg_major_version:
        postgres_versions = [p for p in postgres_versions if p == args.pg_major_version]

    if len(postgres_versions) == 0:
        raise ValueError("At least one supported postgres version is required")

    for postgres_version in postgres_versions:
        print(f"Testing package for following pg version: {postgres_version}")
        docker_image_name = (
            f"test:{test_platform.value['docker_image_name']}-{postgres_version}"
        )
        build_command = (
            f"docker build --pull --no-cache "
            f"-t {docker_image_name} "
            f"-f {test_platform.value['docker_image_name']}/Dockerfile "
            f"--build-arg CITUS_VERSION={args.project_version} "
            f"--build-arg PG_MAJOR={postgres_version} "
            f"--build-arg CITUS_MAJOR_VERSION={minor_project_version} ."
        )
        print(build_command)
        return_build = run_command(build_command)
        return_run = run_command(
            f"docker run  -e POSTGRES_VERSION={postgres_version} {docker_image_name} "
        )
        return_codes[f"{docker_image_name}-build"] = return_build
        return_codes[f"{docker_image_name}-run"] = return_run

    error_exists = False
    print("-----------------Summary Report------------------")
    for key, value in return_codes.items():
        if value > 0:
            error_exists = True
        print(f"{key}: {'Success' if value == 0 else f'Fail. ErrorCode: {value}'}")
    summary_error = "FAILED :(" if error_exists else "SUCCESS :)"
    print(f"------------------------{summary_error}------------------------")

    if error_exists:
        sys.exit("Failed")
