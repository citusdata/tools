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

from .common_tool_methods import (DEFAULT_ENCODING_FOR_FILE_HANDLING,
                                  DEFAULT_UNICODE_ERROR_HANDLER, PackageType,
                                  get_gpg_fingerprints_by_name,
                                  get_supported_postgres_nightly_versions,
                                  get_supported_postgres_release_versions,
                                  platform_names,
                                  run_with_output, str_array_to_str,
                                  supported_platforms,
                                  transform_key_into_base64_str)
from .packaging_warning_handler import validate_output

GPG_KEY_NAME = "packaging@citusdata.com"

POSTGRES_VERSION_FILE = "supported-postgres"
POSTGRES_MATRIX_FILE_NAME = "postgres-matrix.yml"

docker_image_names = {
    "debian": "debian",
    "el": "centos",
    "ol": "oraclelinux",
    "ubuntu": "ubuntu",
    "pgxn": "pgxn"
}

package_docker_platform_dict = {
    "centos,8": "el/8",
    "centos,7": "el/7",
    "debian,bullseye": "debian/bullseye",
    "debian,buster": "debian/buster",
    "debian,stretch": "debian/stretch",
    "oraclelinux,8": "ol/8",
    "oraclelinux,7": "ol/7",
    "oraclelinux,6": "ol/6",
    "ubuntu,focal": "ubuntu/focal",
    "ubuntu,bionic": "ubuntu/bionic",
    "ubuntu,jammy": "ubuntu/jammy",
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


def write_postgres_versions_into_file(input_files_dir: str, package_version: str):
    release_versions = get_supported_postgres_release_versions(f"{input_files_dir}/{POSTGRES_MATRIX_FILE_NAME}",
                                                               package_version)
    nightly_versions = get_supported_postgres_nightly_versions(f"{input_files_dir}/{POSTGRES_MATRIX_FILE_NAME}")
    release_version_str = ','.join(release_versions)
    nightly_version_str = ','.join(nightly_versions)
    with open(f"{input_files_dir}/{POSTGRES_VERSION_FILE}", 'w', encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as f:
        f.write(f"release_versions={release_version_str}\n")
        f.write(f"nightly_versions={nightly_version_str}\n")


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
        package_version = get_package_version_without_release_stage_from_pkgvars(input_files_dir)
        release_versions = get_supported_postgres_release_versions(f"{input_files_dir}/{POSTGRES_MATRIX_FILE_NAME}",
                                                                   package_version)
        nightly_versions = get_supported_postgres_nightly_versions(f"{input_files_dir}/{POSTGRES_MATRIX_FILE_NAME}")

    return release_versions, nightly_versions


@validate_parameters
# disabled since this is related to parameter_validations library methods
# pylint: disable=no-value-for-parameter
def build_package(github_token: non_empty(non_blank(str)),
                  build_type: BuildType, docker_platform: str, postgres_version: str,
                  input_output_parameters: InputOutputParameters, is_test: bool = False):
    docker_image_name = "packaging" if not is_test else "packaging-test"
    postgres_extension = "all" if postgres_version == "all" else f"pg{postgres_version}"
    os.environ["GITHUB_TOKEN"] = github_token
    if not os.path.exists(input_output_parameters.output_dir):
        os.makedirs(input_output_parameters.output_dir)

    output = run_with_output(
        f'docker run --rm -v {input_output_parameters.output_dir}:/packages -v '
        f'{input_output_parameters.input_files_dir}:/buildfiles:ro -e '
        f'GITHUB_TOKEN -e PACKAGE_ENCRYPTION_KEY -e UNENCRYPTED_PACKAGE '
        f'citus/{docker_image_name}:{docker_platform}-{postgres_extension} {build_type.name}', text=True)

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
    return f'{docker_image_names[os_name]}-{os_version}' if os_version else f'{docker_image_names[os_name]}'


@validate_parameters
# disabled since this is related to parameter_validations library methods
# pylint: disable=no-value-for-parameter
def build_packages(github_token: non_empty(non_blank(str)),
                   platform: non_empty(non_blank(str)),
                   build_type: BuildType, signing_credentials: SigningCredentials,
                   input_output_parameters: InputOutputParameters, is_test: bool = False) -> None:
    os_name, os_version = decode_os_and_release(platform)
    release_versions, nightly_versions = get_postgres_versions(os_name, input_output_parameters.input_files_dir)
    signing_credentials = get_signing_credentials(signing_credentials.secret_key, signing_credentials.passphrase)
    if platform != "pgxn":
        package_version = get_package_version_without_release_stage_from_pkgvars(
            input_output_parameters.input_files_dir)
        write_postgres_versions_into_file(input_output_parameters.input_files_dir, package_version)

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
                      postgres_version, input_output_parameters, is_test)
        print(f"Package build for {os_name}-{os_version} for postgres {postgres_version} finished ")

    sign_packages(output_sub_folder, signing_credentials, input_output_parameters)


def get_build_platform(packaging_platform: str, packaging_docker_platform: str) -> str:
    return (
        package_docker_platform_dict[packaging_docker_platform] if packaging_docker_platform else packaging_platform)


def get_package_version_from_pkgvars(input_files_dir: str):
    pkgvars_config = dotenv_values(f"{input_files_dir}/pkgvars")
    package_version_with_suffix = pkgvars_config["pkglatest"]
    version_parts = package_version_with_suffix.split(".")
    # hll is working with minor release format e.g. 2.16.citus-1
    pkg_name = pkgvars_config["pkgname"]

    if len(version_parts) < 3:
        raise ValueError("Version should at least contains three parts seperated with '.'. e.g 10.0.2-1")

    third_part_splitted = version_parts[2].split("-")

    if pkg_name in ('hll', 'azure_gdpr', 'azuregdpr'):
        package_version = f"{version_parts[0]}.{version_parts[1]}"
    else:
        package_version = f"{version_parts[0]}.{version_parts[1]}.{third_part_splitted[0]}"
    return package_version


def get_package_version_without_release_stage_from_pkgvars(input_files_dir: str):
    version = get_package_version_from_pkgvars(input_files_dir)
    return tear_release_stage_from_package_version(version)


def tear_release_stage_from_package_version(package_version: str) -> str:
    return package_version.split("_")[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--platform', required=False, choices=platform_names())
    parser.add_argument('--packaging_docker_platform', required=False, choices=package_docker_platform_dict.keys())
    parser.add_argument('--build_type', choices=[b.name for b in BuildType])
    parser.add_argument('--secret_key', required=True)
    parser.add_argument('--passphrase', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--input_files_dir', required=True)
    parser.add_argument('--output_validation', action="store_true")
    parser.add_argument('--is_test', action="store_true")

    args = parser.parse_args()

    if args.platform and args.packaging_docker_platform:
        raise ValueError("Either platform or packaging_docker_platform should be set.")
    build_platform = get_build_platform(args.platform, args.packaging_docker_platform)

    io_parameters = InputOutputParameters.build(args.input_files_dir, args.output_dir, args.output_validation)
    sign_credentials = SigningCredentials(args.secret_key, args.passphrase)
    build_packages(args.gh_token, build_platform, BuildType[args.build_type], sign_credentials,
                   io_parameters, args.is_test)
