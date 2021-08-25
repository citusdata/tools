import os

import pathlib2

from .test_utils import generate_new_gpg_key
from ..citus_package import (build_packages, BuildType, decode_os_and_release, get_release_package_folder_name,
                             SigningCredentials, InputOutputParameters, get_build_platform,
                             POSTGRES_VERSION_FILE, get_package_version_from_pkgvars, POSTGRES_MATRIX_FILE_NAME,
                             SigningCredentials, InputOutputParameters)

from ..common_tool_methods import (run, delete_rpm_key_by_name, get_gpg_fingerprints_by_name,
                                   get_private_key_by_fingerprint_with_passphrase, define_rpm_public_key_to_machine,
                                   transform_key_into_base64_str,
                                   verify_rpm_signature_in_dir, delete_all_gpg_keys_by_name,
                                   get_supported_postgres_versions)
from ..upload_to_package_cloud import (upload_files_in_directory_to_package_cloud, delete_package_from_package_cloud,
                                       package_exists)

from dotenv import dotenv_values

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
BASE_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages"

package_counts = {
    "el/7": 4,
    "el/8": 6,
    "ol/7": 4,
    "ol/8": 6,
    "debian/stretch": 4,
    "debian/buster": 4,
    "debian/bullseye": 4,
    "ubuntu/xenial": 2,
    "ubuntu/bionic": 4,
    "ubuntu/focal": 4,
    "pgxn": 1
}

TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
TEST_GPG_KEY_PASSPHRASE = os.getenv("PACKAGING_PASSPHRASE")
GH_TOKEN = os.getenv("GH_TOKEN")
PACKAGE_CLOUD_API_TOKEN = os.getenv("PACKAGE_CLOUD_API_TOKEN")
REPO_CLIENT_SECRET = os.getenv("REPO_CLIENT_SECRET")
PLATFORM = get_build_platform(os.getenv("PLATFORM"), os.getenv("PACKAGING_IMAGE_PLATFORM"))


def get_required_package_count(input_files_dir: str, platform: str):
    package_version = get_package_version_from_pkgvars(input_files_dir)
    postgres_versions = get_supported_postgres_versions(f"{input_files_dir}/{POSTGRES_MATRIX_FILE_NAME}",
                                                        package_version)
    return len(postgres_versions) * single_postgres_package_counts[platform]


def setup_module():
    # Run tests against "all-citus-unit-tests" since we don't want to deal with the changes
    # made to "all-citus" in each release.
    packaging_branch_name = "pgxn-citus" if PLATFORM == "pgxn" else "all-citus-unit-tests"
    if not os.path.exists(PACKAGING_EXEC_FOLDER):
        run(
            f"git clone --branch {packaging_branch_name} https://github.com/citusdata/packaging.git"
            f" {PACKAGING_EXEC_FOLDER}")


def teardown_module():
    if os.path.exists("packaging_test"):
        run("rm -r packaging_test")


def test_build_packages():
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_passphrase.gpg")
    gpg_fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(gpg_fingerprints) > 0
    secret_key = transform_key_into_base64_str(
        get_private_key_by_fingerprint_with_passphrase(gpg_fingerprints[0], TEST_GPG_KEY_PASSPHRASE))
    define_rpm_public_key_to_machine(gpg_fingerprints[0])
    signing_credentials = SigningCredentials(secret_key, TEST_GPG_KEY_PASSPHRASE)
    input_output_parameters = InputOutputParameters.build(PACKAGING_EXEC_FOLDER, BASE_OUTPUT_FOLDER,
                                                          output_validation=False)
    build_packages(GH_TOKEN, PLATFORM, BuildType.release, signing_credentials, input_output_parameters)
    verify_rpm_signature_in_dir(BASE_OUTPUT_FOLDER)
    os_name, os_version = decode_os_and_release(PLATFORM)
    sub_folder = get_release_package_folder_name(os_name, os_version)
    release_output_folder = f"{BASE_OUTPUT_FOLDER}/{sub_folder}"
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    assert len(os.listdir(release_output_folder)) == get_required_package_count(input_files_dir=PACKAGING_EXEC_FOLDER,
                                                                                platform=PLATFORM)
    postgres_version_file_path = f"{PACKAGING_EXEC_FOLDER}/{POSTGRES_VERSION_FILE}"
    assert os.path.exists(postgres_version_file_path)
    config = dotenv_values(postgres_version_file_path)
    assert config["postgres_versions"] == "11,12,13"

def test_get_required_package_count():
    assert get_required_package_count(PACKAGING_EXEC_FOLDER, platform="el/8") == 9

def test_decode_os_packages():
    os, release = decode_os_and_release("el/7")
    assert os == "el" and release == "7"


def test_upload_to_package_cloud():
    platform = get_build_platform(os.getenv("PLATFORM"), os.getenv("PACKAGING_IMAGE_PLATFORM"))
    current_branch = "all-citus"
    main_branch = "all-citus"
    output = upload_files_in_directory_to_package_cloud(BASE_OUTPUT_FOLDER, platform, PACKAGE_CLOUD_API_TOKEN,
                                                        "citus-bot/sample",
                                                        current_branch, main_branch)
    distro_parts = platform.split("/")
    if len(distro_parts) != 2:
        raise ValueError("Platform should consist of two parts splitted with '/' e.g. el/8")
    for return_value in output.return_values:
        exists = package_exists(PACKAGE_CLOUD_API_TOKEN, "citus-bot", "sample",
                                os.path.basename(return_value.file_name),
                                platform)
        if not exists:
            raise ValueError(f"{os.path.basename(return_value.file_name)} could not be found on package cloud")

    for return_value in output.return_values:
        delete_output = delete_package_from_package_cloud(PACKAGE_CLOUD_API_TOKEN, "citus-bot", "sample",
                                                          distro_parts[0], distro_parts[1],
                                                          os.path.basename(return_value.file_name))
        if delete_output.success_status:
            print(f"{os.path.basename(return_value.file_name)} deleted successfully")
        else:
            print(f"{os.path.basename(return_value.file_name)} can not be deleted. Message: {delete_output.message}")
