import argparse
import glob
import os
import subprocess
from enum import Enum
from typing import List
from typing import Tuple

import docker
import gnupg
from attr import dataclass
from dotenv import dotenv_values
from parameters_validation import non_blank, non_empty, validate_parameters

from .common_tool_methods import (run_with_output, PackageType, transform_key_into_base64_str,
                                  get_gpg_fingerprints_by_name, str_array_to_str)
from .packaging_warning_handler import validate_output

GPG_KEY_NAME = "packaging@citusdata.com"

supported_platforms = {
    "debian": ["buster", "stretch", "jessie", "wheezy"],
    "el": ["8", "7", "6"],
    "ol": ["7", "8"],
    "ubuntu": ["focal", "bionic", "xenial", "trusty"]
}


def platform_names() -> List[str]:
    platforms = []
    for platform_os, platform_release in supported_platforms.items():
        platforms.append(f"{platform_os}/{platform_release}")
    platforms.append("pgxn")
    return platforms


docker_image_names = {
    "debian": "debian",
    "el": "centos",
    "ol": "oraclelinux",
    "ubuntu": "ubuntu",
    "pgxn": "pgxn"
}


def get_package_type_by_docker_image_name(docker_image_name: str) -> PackageType:
    return PackageType.deb if docker_image_name.startswith(("ubuntu", "debian")) else PackageType.rpm


class BuildType(Enum):
    release = 1
    nightly = 2


class PostgresVersionDockerImageType(Enum):
    multiple = 1
    single = 2


platform_postgres_version_source = {
    "el": PostgresVersionDockerImageType.multiple,
    "ol": PostgresVersionDockerImageType.multiple,
    "debian": PostgresVersionDockerImageType.single,
    "ubuntu": PostgresVersionDockerImageType.single,
    "pgxn": PostgresVersionDockerImageType.single
}

PKGVARS_FILE = "pkgvars"
SINGLE_DOCKER_POSTGRES_PREFIX = "all"
PACKAGES_DIR_NAME = "packages"


def decode_os_and_release(platform_name: str) -> Tuple[str, str]:
    parts = platform_name.split("/")

    if len(parts) == 0 or len(parts) > 2 or (len(parts) == 1 and parts[0] != "pgxn"):
        raise ValueError("Platforms should have two parts divided by '/' or should be 'pgxn' ")
    if len(parts) == 1 and parts[0] == "pgxn":
        os_name = "pgxn"
        os_release = ""
    else:
        os_name = parts[0]
        os_release = parts[1]
        if os_name not in supported_platforms:
            raise ValueError(
                f"{os_name} is not among supported operating systems. Supported operating systems are as below:\n "
                f"{','.join(supported_platforms.keys())}")
        if os_release not in supported_platforms[os_name]:
            raise ValueError(f"{os_release} is not among supported releases for {os_name}."
                             f"Supported releases are as below:\n {','.join(supported_platforms[os_name])}")
    return os_name, os_release


def is_docker_running() -> bool:
    try:
        docker_client = docker.from_env()
        docker_client.ping()
        return True
    ## Exception type is not defined in API so I keep as is
    except:  # noqa: E722 # pylint: disable=bare-except
        return False


@dataclass
class SigningCredentials:
    secret_key: str
    passphrase: str


@dataclass
class InputOutputParameters:
    input_files_dir: str
    output_dir: str
    output_validation: bool

    @staticmethod
    @validate_parameters
    # disabled since this is related to parameter_validations library methods
    # pylint: disable=no-value-for-parameter
    def build(input_files_dir: non_empty(non_blank(str)), output_dir: non_empty(non_blank(str)),
              output_validation: bool = False):
        return InputOutputParameters(input_files_dir=input_files_dir, output_dir=output_dir,
                                     output_validation=output_validation)


@validate_parameters
# disabled since this is related to parameter_validations library methods
# pylint: disable=no-value-for-parameter
def get_signing_credentials(packaging_secret_key: str,
                            packaging_passphrase: non_empty(
                                non_blank(str))) -> SigningCredentials:
    if packaging_secret_key:
        secret_key = packaging_secret_key
    else:
        fingerprints = get_gpg_fingerprints_by_name(GPG_KEY_NAME)
        if len(fingerprints) == 0:
            raise ValueError(f"Key for {GPG_KEY_NAME} does not exist")

        gpg = gnupg.GPG()

        private_key = gpg.export_keys(fingerprints[0], secret=True, passphrase=packaging_passphrase)
        secret_key = transform_key_into_base64_str(private_key)

    passphrase = packaging_passphrase
    return SigningCredentials(secret_key=secret_key, passphrase=passphrase)


def sign_packages(sub_folder: str, signing_credentials: SigningCredentials,
                  input_output_parameters: InputOutputParameters):
    output_path = f"{input_output_parameters.output_dir}/{sub_folder}"
    deb_files = glob.glob(f"{output_path}/*.deb", recursive=True)
    rpm_files = glob.glob(f"{output_path}/*.rpm", recursive=True)
    os.environ["PACKAGING_PASSPHRASE"] = signing_credentials.passphrase
    os.environ["PACKAGING_SECRET_KEY"] = signing_credentials.secret_key

    if len(rpm_files) > 0:
        print("Started RPM Signing...")
        result = run_with_output(f"docker run --rm -v {output_path}:/packages/{sub_folder} -e PACKAGING_SECRET_KEY -e "
                                 f"PACKAGING_PASSPHRASE citusdata/packaging:rpmsigner", text=True)
        output = result.stdout
        print(f"Result:{output}")

        if result.returncode != 0:
            raise ValueError(f"Error while signing rpm files.Err:{result.stderr}")
        if input_output_parameters.output_validation:
            validate_output(output, f"{input_output_parameters.input_files_dir}/packaging_ignore.yml", PackageType.rpm)

        print("RPM signing finished successfully.")

    if len(deb_files) > 0:
        print("Started DEB Signing...")

        # output is required to understand the error if any so check parameter is not used
        # pylint: disable=subprocess-run-check
        result = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{output_path}:/packages/{sub_folder}",
             "-e", "PACKAGING_SECRET_KEY", "-e", "PACKAGING_PASSPHRASE", "citusdata/packaging:debsigner"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, input=signing_credentials.passphrase)
        output = result.stdout
        print(f"Result:{output}")

        if result.returncode != 0:
            raise ValueError(f"Error while signing deb files.Err:{result.stdout}")

        if input_output_parameters.output_validation:
            validate_output(result.stdout, f"{input_output_parameters.input_files_dir}/packaging_ignore.yml",
                            PackageType.deb)

        print("DEB signing finished successfully.")


def get_postgres_versions(os_name: str, input_files_dir: str) -> Tuple[List[str], List[str]]:
    if platform_postgres_version_source[os_name] == PostgresVersionDockerImageType.single:
        release_versions = ["all"]
        nightly_versions = ["all"]
    else:
        pkgvars_config = dotenv_values(f"{input_files_dir}/{PKGVARS_FILE}")
        release_versions_str = pkgvars_config['releasepg']
        if "nightlypg" in pkgvars_config:
            nightly_versions_str = pkgvars_config['nightlypg']
        else:
            nightly_versions_str = release_versions_str

        release_versions = release_versions_str.split(",")
        nightly_versions = nightly_versions_str.split(",")
    return release_versions, nightly_versions


@validate_parameters
# disabled since this is related to parameter_validations library methods
# pylint: disable=no-value-for-parameter
def build_package(github_token: non_empty(non_blank(str)),
                  build_type: BuildType, docker_platform: str, postgres_version: str,
                  input_output_parameters: InputOutputParameters):
    postgres_extension = "all" if postgres_version == "all" else f"pg{postgres_version}"
    os.environ["GITHUB_TOKEN"] = github_token
    if not os.path.exists(input_output_parameters.output_dir):
        os.makedirs(input_output_parameters.output_dir)

    output = run_with_output(
        f'docker run --rm -v {input_output_parameters.output_dir}:/packages -v '
        f'{input_output_parameters.input_files_dir}:/buildfiles:ro -e '
        f'GITHUB_TOKEN -e PACKAGE_ENCRYPTION_KEY -e UNENCRYPTED_PACKAGE '
        # TODO The below line should be deleted after PG14 official release
        # This line is to override pg_buildext supported PG releases
        f'-e DEB_PG_SUPPORTED_VERSIONS="10\n11\n12\n13\n14"'  
        f'citus/packaging:{docker_platform}-{postgres_extension} {build_type.name}', text=True)

    if output.stdout:
        print("Output:" + output.stdout)
    if output.returncode != 0:
        raise ValueError(output.stderr)

    if input_output_parameters.output_validation:
        validate_output(output.stdout, f"{input_output_parameters.input_files_dir}/packaging_ignore.yml",
                        get_package_type_by_docker_image_name(docker_platform))


def get_release_package_folder_name(os_name: str, os_version: str) -> str:
    return f"{os_name}-{os_version}"


def get_docker_image_name(platform: str):
    os_name, os_version = decode_os_and_release(platform)
    return f'{docker_image_names[os_name]}-{os_version}'


@validate_parameters
# disabled since this is related to parameter_validations library methods
# pylint: disable=no-value-for-parameter
def build_packages(github_token: non_empty(non_blank(str)),
                   platform: non_empty(non_blank(str)),
                   build_type: BuildType, signing_credentials: SigningCredentials,
                   input_output_parameters: InputOutputParameters) -> None:
    os_name, os_version = decode_os_and_release(platform)
    release_versions, nightly_versions = get_postgres_versions(os_name, input_output_parameters.input_files_dir)
    signing_credentials = get_signing_credentials(signing_credentials.secret_key, signing_credentials.passphrase)

    if not signing_credentials.passphrase:
        raise ValueError("PACKAGING_PASSPHRASE should not be null or empty")

    postgres_versions = release_versions if build_type == BuildType.release else nightly_versions
    print(f"Postgres Versions: {str_array_to_str(postgres_versions)}")
    docker_image_name = get_docker_image_name(platform)
    output_sub_folder = get_release_package_folder_name(os_name, os_version)
    input_output_parameters.output_dir = f"{input_output_parameters.output_dir}/{output_sub_folder}"
    for postgres_version in postgres_versions:
        print(f"Package build for {os_name}-{os_version} for postgres {postgres_version} started... ")
        build_package(github_token, build_type, docker_image_name,
                      postgres_version, input_output_parameters)
        print(f"Package build for {os_name}-{os_version} for postgres {postgres_version} finished ")

    sign_packages(output_sub_folder, signing_credentials, input_output_parameters)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--platform', required=True, choices=platform_names())
    parser.add_argument('--build_type', choices=[b.name for b in BuildType])
    parser.add_argument('--secret_key', required=True)
    parser.add_argument('--passphrase', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--input_files_dir', required=True)
    parser.add_argument('--output_validation', action="store_true")

    args = parser.parse_args()

    io_parameters = InputOutputParameters.build(args.input_files_dir, args.output_dir, args.output_validation)
    sign_credentials = SigningCredentials(args.secret_key, args.passphrase)
    build_packages(args.gh_token, args.platform, BuildType[args.build_type], sign_credentials,
                   io_parameters)
