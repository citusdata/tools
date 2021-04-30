import argparse
import glob
import os
import subprocess
from enum import Enum
from typing import List
from typing import Tuple

from .common_tool_methods import run_with_output, PackageType
from .packaging_warning_handler import validate_output
from parameters_validation import no_whitespaces, non_blank, non_empty, non_negative, validate_parameters

supported_platforms = {
    "debian": ["buster", "stretch", "jessie", "wheezy"],
    "el": ["8", "7", "6"],
    "ol": ["7", "8"],
    "ubuntu": ["focal", "bionic", "xenial", "trusty"],
    "pgxn": []
}

docker_image_names = {
    "debian": "debian",
    "el": "centos",
    "ol": "oraclelinux",
    "ubuntu": "ubuntu",
    "pgxn": "pgxn"
}


def get_package_type_by_docker_image_name(docker_image_name: str) -> PackageType:
    return PackageType.deb if docker_image_name in ("debian", "ubuntu") else PackageType.rpm


class BuildType(Enum):
    release = 1
    nightly = 2


class PostgresVersionDockerImage:
    multiple = 1,
    single = 2


platform_postgres_version_source = {
    "el": PostgresVersionDockerImage.multiple,
    "ol": PostgresVersionDockerImage.multiple,
    "debian": PostgresVersionDockerImage.single,
    "ubuntu": PostgresVersionDockerImage.single,
    "pgxn": PostgresVersionDockerImage.single
}

PKGVARS_FILE = "pkgvars"
SINGLE_DOCKER_POSTGRES_PREFIX = "all"
PACKAGES_DIR_NAME = "packages"


def decode_os_and_release(platform_name: str) -> Tuple[str, str]:
    parts = platform_name.split("/")

    if len(parts) == 0 or len(parts) > 2 or (len(parts) == 1 and parts[0] != "pgxn"):
        raise ValueError("Platforms should have two parts divided by '/' or should be 'pgxn' ")
    elif len(parts) == 1 and parts[0] == "pgxn":
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
            raise ValueError(f"{os_release} is not among supported releases for {os_name}. "
                             f"Supported releases are as below:\n {','.join(supported_platforms[os_name])}")
    return os_name, os_release


def is_docker_running() -> bool:
    child = subprocess.Popen(["docker", "info"], stdout=subprocess.PIPE)
    stream_data = child.communicate()[0]
    print(stream_data.decode("ascii"))
    return child.returncode == 0


def get_signing_credentials(packaging_secret_key: str, packaging_passphrase: str) -> Tuple[str, str]:
    if packaging_passphrase is None or len(packaging_passphrase) == 0:
        raise ValueError("packaging_passphrase should not be null")
    if packaging_secret_key is not None and len(packaging_secret_key) > 0:
        secret_key = packaging_secret_key
    else:
        child = subprocess.Popen(["gpg", "--batch", "--fingerprint", "packaging@citusdata.com"], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        streamdata = child.communicate()
        if child.returncode != 0:
            raise ValueError("Gpg key for 'packaging@citusdata.com' does not exist")
        gpg_result = streamdata[0].decode("ascii")
        gpg_result_lines = gpg_result.splitlines()
        if len(gpg_result_lines) != 5:
            raise ValueError(f"GPG Key result is not in desired format. It should have "
                             f"4 lines including pub, uid and sub. Result: {gpg_result} ")
        fingerprint = gpg_result_lines[1].strip()

        try:
            cmd = f'gpg --batch --export-secret-keys -a "{fingerprint}" | base64'
            ps = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=2)
            secret_key = ps.stdout.decode("ascii")
        except subprocess.TimeoutExpired:
            raise ValueError(
                "Error while getting key. Most probably packaging key is stored with password. "
                "Please remove the password when storing key with email packaging@citusdata.com")
    passphrase = packaging_passphrase
    return secret_key, passphrase


def sign_packages(base_output_path: str, sub_folder: str, secret_key: str, passphrase: str, input_files_dir: str,
                  output_validation: bool = False):
    output_path = f"{base_output_path}/{sub_folder}"
    deb_files = glob.glob(f"{output_path}/*.deb", recursive=True)
    rpm_files = glob.glob(f"{output_path}/*.rpm", recursive=True)
    os.environ["PACKAGING_PASSPHRASE"] = passphrase
    os.environ["PACKAGING_SECRET_KEY"] = secret_key

    if len(rpm_files) > 0:
        print("Started RPM Signing...")
        result = run_with_output(f"docker run --rm -v  {output_path}:/packages/{sub_folder} -e PACKAGING_SECRET_KEY -e "
                                 f"PACKAGING_PASSPHRASE citusdata/packaging:rpmsigner")
        print("RPM signing finished successfully.")
        if result.returncode != 0:
            raise ValueError(f"Error while signing rpm files.Err:{result.stdout}")

        output = result.stdout.decode("ascii")
        print(output)

        if output_validation:
            validate_output(output, f"{input_files_dir}/packaging_ignore.yml", PackageType.rpm)

    os.environ["PACKAGING_PASSPHRASE"] = passphrase
    os.environ["PACKAGING_SECRET_KEY"] = secret_key
    if len(deb_files) > 0:
        print("Started DEB Signing...")
        result = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{output_path}:/packages/{sub_folder}",
             "-e", "PACKAGING_SECRET_KEY", "-e", "PACKAGING_PASSPHRASE", "citusdata/packaging:debsigner"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, input=passphrase)
        print(result.stdout)

        if result.returncode != 0:
            raise ValueError(f"Error while signing DEB files.Err:{result.stdout}")

        if output_validation:
            validate_output(result.stdout, f"{input_files_dir}/packaging_ignore.yml", PackageType.deb)
        print("DEB signing finished successfully.")


def get_postgres_versions(os_name: str, input_files_dir: str) -> Tuple[List[str], List[str]]:
    release_versions = []
    nightly_versions = []
    if platform_postgres_version_source[os_name] == PostgresVersionDockerImage.single:
        release_versions = ["all"]
        nightly_versions = ["all"]
    else:
        with open(f"{input_files_dir}/pkgvars", "r") as reader:
            content = reader.read()
            lines = content.splitlines()
            for line in lines:
                if line.startswith("releasepg"):
                    release_version = line
                if line.startswith("nightlypg"):
                    nightly_version = line
            if release_version is None or "=" not in release_version or len(release_version.split("=")) != 2:
                raise ValueError(
                    f"Release version in pkglatest is not well formatted.Expected format: releasepg=12,13 "
                    f"Actual Format:{release_version}")
            if nightly_version is None or "=" not in nightly_version or len(nightly_version.split("=")) != 2:
                raise ValueError(
                    f"Nightly version in pkglatest is not well formatted.Expected format: nightlypg=12,13 "
                    f"Actual Format:{nightly_version}")
            release_versions = release_version.split("=")[1].split(",")
            nightly_versions = nightly_version.split("=")[1].split(",")
    return release_versions, nightly_versions


def build_package(github_token: non_empty(non_blank(str)), build_type: BuildType, output_dir: str, input_files_dir: str,
                  docker_platform: str, postgres_version: str, output_validation: bool = False):
    postgres_extension = "all" if postgres_version == "all" else f"pg{postgres_version}"
    os.environ["GITHUB_TOKEN"] = github_token
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output = run_with_output(f"docker run --rm -v {output_dir}:/packages -v {input_files_dir}:/buildfiles:ro -e "
                             f"GITHUB_TOKEN -e PACKAGE_ENCRYPTION_KEY -e UNENCRYPTED_PACKAGE "
                             f"citus/packaging:{docker_platform}-{postgres_extension} {build_type.name}")
    print(output.stdout.decode("ascii"))
    if output_validation:
        validate_output(output.stdout.decode("ascii"), f"{input_files_dir}/packaging_ignore.yml",
                        get_package_type_by_docker_image_name(docker_platform))


def get_release_package_folder(os_name: str, os_version: str) -> str:
    return f"{os_name}-{os_version}"


def get_docker_image_name(platform: str):
    os_name, os_version = decode_os_and_release(platform)
    return f'{docker_image_names[os_name]}-{os_version}'


def build_packages(github_token: non_empty(non_blank(str)), platform: non_empty(non_blank(str)), build_type: BuildType,
                   packaging_secret_key: non_empty(non_blank(str)),
                   packaging_passphrase: non_empty(non_blank(str)),
                   base_output_dir: non_empty(non_blank(str)),
                   input_files_dir: non_empty(non_blank(str)), output_validation: bool = False) -> None:
    os_name, os_version = decode_os_and_release(platform)
    release_versions, nightly_versions = get_postgres_versions(os_name, input_files_dir)
    secret_key, passphrase = get_signing_credentials(packaging_secret_key, packaging_passphrase)

    if passphrase is None:
        raise ValueError("PACKAGING_PASSPHRASE should be defined as environment parameter")

    postgres_versions = release_versions if build_type == BuildType.release else nightly_versions
    docker_image_name = get_docker_image_name(platform)
    output_sub_folder = get_release_package_folder(os_name, os_version)
    output_dir = f"{base_output_dir}/{output_sub_folder}"
    for postgres_version in postgres_versions:
        print(f"Package build for {os_name}-{os_version} for postgres {postgres_version} started... ")
        build_package(github_token, build_type, output_dir,
                      input_files_dir, docker_image_name,
                      postgres_version, output_validation)
        print(f"Package build for {os_name}-{os_version} for postgres {postgres_version} finished ")

    sign_packages(base_output_dir, output_sub_folder, secret_key, passphrase, input_files_dir, output_validation)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token')
    parser.add_argument('--platform')
    parser.add_argument('--build_type')
    parser.add_argument('--secret_key')
    parser.add_argument('--passphrase')
    parser.add_argument('--output_dir')
    parser.add_argument('--input_files_dir')
    parser.add_argument('--output_validation')

    args = parser.parse_args()

    output_validation = False if args.output_validation is None or args.output_validation.lower() == "false" else True

    build_packages(args.gh_token, args.platform, BuildType[args.build_type], args.secret_key, args.passphrase,
                   args.output_dir, args.input_files_dir, output_validation)
