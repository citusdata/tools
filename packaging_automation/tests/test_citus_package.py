import os
import pathlib2

from .test_utils import generate_new_gpg_key
from ..citus_package import *
from ..common_tool_methods import *
from ..upload_to_package_cloud import upload_files_in_directory_to_package_cloud, delete_package_from_package_cloud, \
    does_package_exist

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
BASE_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages"

package_counts = {
    "el/7": 4, "el/8": 6, "ol/7": 4, "debian/stretch": 4, "debian/buster": 4, "ubuntu/xenial": 2, "ubuntu/bionic": 2,
    "ubuntu/focal": 2
}

TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
TEST_GPG_KEY_PASSPHRASE = os.getenv("PACKAGING_PASSPHRASE")
GH_TOKEN = os.getenv("GH_TOKEN")
PLATFORM = os.getenv("PLATFORM")
PACKAGECLOUD_API_TOKEN = os.getenv("PACKAGE_CLOUD_API_TOKEN")
REPO_CLIENT_SECRET = os.getenv("REPO_CLIENT_SECRET")


def setup_module():
    if not os.path.exists("packaging_test"):
        run(
            f"git clone --branch all-citus https://github.com/citusdata/packaging.git {PACKAGING_SOURCE_FOLDER}")


def teardown_module():
    if os.path.exists("packaging_test"):
        run("rm -r packaging_test")


def test_build_packages():
    platform = os.getenv("PLATFORM")

    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_password.gpg")
    gpg_fingerprint = get_gpg_fingerprint_from_name(TEST_GPG_KEY_NAME)
    secret_key = get_secret_key_by_fingerprint_with_password(gpg_fingerprint, TEST_GPG_KEY_PASSPHRASE)
    define_rpm_public_key_to_machine(gpg_fingerprint)

    build_packages(GH_TOKEN, platform, BuildType.release, secret_key,
                   TEST_GPG_KEY_PASSPHRASE, BASE_OUTPUT_FOLDER, PACKAGING_EXEC_FOLDER)
    verify_rpm_signature_in_dir(BASE_OUTPUT_FOLDER)
    os_name, os_version = decode_os_and_release(platform)
    sub_folder = get_release_package_folder(os_name, os_version)
    release_output_folder = f"{BASE_OUTPUT_FOLDER}/{sub_folder}"
    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    assert len(os.listdir(release_output_folder)) == package_counts[platform]


def test_upload_to_package_cloud():
    output = upload_files_in_directory_to_package_cloud(BASE_OUTPUT_FOLDER, PLATFORM, PACKAGECLOUD_API_TOKEN,
                                                        "sample")
    distro_parts = PLATFORM.split("/")
    if len(distro_parts) != 2:
        raise ValueError("Platform should consist of 2 parts splitted with '/'")
    for return_value in output.return_values:
        exists = does_package_exist(PACKAGECLOUD_API_TOKEN, "citus-bot", "sample",
                                    os.path.basename(return_value.file_name),
                                    PLATFORM)
        if not exists:
            raise ValueError(f"{os.path.basename(return_value.file_name)} could not be found on package cloud")

    for return_value in output.return_values:
        delete_output = delete_package_from_package_cloud(PACKAGECLOUD_API_TOKEN, "citus-bot", "sample",
                                                          distro_parts[0], distro_parts[1],
                                                          os.path.basename(return_value.file_name))
        if delete_output.success_status:
            print(f"{os.path.basename(return_value.file_name)} deleted successfully")
        else:
            print(f"{os.path.basename(return_value.file_name)} can not be deleted. Message: {delete_output.message}")
