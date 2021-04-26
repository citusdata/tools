import pathlib2

from .test_utils import generate_new_gpg_key
from ..citus_package import *
from ..common_tool_methods import *

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
RPM_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages/rpm"
DEB_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages/deb"

package_counts = {
    "el-7": 4, "el-8": 6, "ol/7": 4, "debian-stretch": 4, "debian-buster": 4, "ubuntu-xenial": 2, "ubuntu-bionic": 2,
    "ubuntu-focal": 2
}

TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
TEST_GPG_KEY_PASSPHRASE = "Citus123"
GH_TOKEN = os.getenv("GH_TOKEN")
PLATFORM = os.getenv("PLATFORM")


def setup_module():
    if not os.path.exists("packaging_test"):
        run(
            f"git clone --branch all-citus https://github.com/citusdata/packaging.git {PACKAGING_SOURCE_FOLDER}")


def teardown_module():
    if os.path.exists("packaging_test"):
        run("rm -r packaging_test")


def test_build_packages():
    platform = "el/8"
    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_password.gpg")
    gpg_fingerprint = get_gpg_fingerprint_from_name(TEST_GPG_KEY_NAME)
    secret_key = get_secret_key_by_fingerprint_with_password(gpg_fingerprint, TEST_GPG_KEY_PASSPHRASE)
    build_packages(GH_TOKEN, platform, BuildType.release, secret_key,
                   RPM_OUTPUT_FOLDER, DEB_OUTPUT_FOLDER, PACKAGING_EXEC_FOLDER)
    define_rpm_public_key_to_machine(gpg_fingerprint)
    sign_packages(RPM_OUTPUT_FOLDER, DEB_OUTPUT_FOLDER, secret_key, TEST_GPG_KEY_PASSPHRASE)
    verify_rpm_signature_in_dir(RPM_OUTPUT_FOLDER)
    os_name, os_version = decode_os_and_release(platform)
    output_dir = DEB_OUTPUT_FOLDER if os_name in ("debian", "ubuntu") else RPM_OUTPUT_FOLDER
    release_output_folder = get_release_package_folder(output_dir, os_name, os_version)
    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    assert len(os.listdir(release_output_folder)) == package_counts[f"{os_name}-{os_version}"]
