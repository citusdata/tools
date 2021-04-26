from ..citus_package import *
from ..common_tool_methods import *
from .test_utils import generate_new_gpg_key
import pytest
import pathlib2

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
TEST_GPG_KEY_PASSPHRASE = "Citus123"
GH_TOKEN = os.getenv("GH_TOKEN")
PLATFORM = os.getenv("PLATFORM")

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
RPM_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages/rpm"
DEB_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages/deb"


def setup_module():
    if not os.path.exists("packaging_test"):
        run(
            f"git clone --branch all-citus https://github.com/citusdata/packaging.git {PACKAGING_SOURCE_FOLDER}")


def teardown_module():
    if os.path.exists("packaging_test"):
        run("rm -r packaging_test")


def test_decode_os_and_release():
    os_name, os_version = decode_os_and_release("el/7")
    assert os_name == "el" and os_version == "7"

    os_name, os_version = decode_os_and_release("debian/buster")
    assert os_name == "debian" and os_version == "buster"

    os_name, os_version = decode_os_and_release("pgxn")
    assert os_name == "pgxn" and os_version == ""

    with pytest.raises(ValueError):
        os_name, os_version = decode_os_and_release("debian")

    with pytest.raises(ValueError):
        os_name, os_version = decode_os_and_release("debian/anders")


def test_is_docker_running():
    assert is_docker_running()


def test_get_signing_credentials():
    secret_key, passphrase = get_signing_credentials("verysecretkey")
    assert secret_key == "verysecretkey" and passphrase == "123"

    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)

    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging.gpg")
    os.environ["PACKAGING_PASSPHRASE"] = TEST_GPG_KEY_PASSPHRASE
    secret_key, passphrase = get_signing_credentials("")
    expected_gpg_key = get_secret_key_by_fingerprint(
        get_gpg_fingerprint_from_name(TEST_GPG_KEY_NAME))
    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    assert secret_key == expected_gpg_key and passphrase == TEST_GPG_KEY_PASSPHRASE


def test_delete_rpm_key_by_name():
    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_password.gpg")
    fingerprint = get_gpg_fingerprint_from_name(TEST_GPG_KEY_NAME)
    define_rpm_public_key_to_machine(fingerprint)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    output = subprocess.run(["rpm", "-q gpg-pubkey", "--qf %{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    assert TEST_GPG_KEY_NAME not in output.stdout.decode("ascii") and output.returncode == 1


def test_get_postgres_versions():
    release_versions, nightly_versions = get_postgres_versions("debian",
                                                               f"{TEST_BASE_PATH}/packaging_automation/tests/files")
    assert release_versions[0] == "all" and nightly_versions[0] == "all"

    release_versions, nightly_versions = get_postgres_versions("el",
                                                               f"{TEST_BASE_PATH}/packaging_automation/tests/files")
    assert release_versions[0] == "11" and len(release_versions) == 3 and nightly_versions[0] == "12" and \
           len(nightly_versions) == 2


def test_build_package_debian():
    build_package(GH_TOKEN, BuildType.release,
                  f"{DEB_OUTPUT_FOLDER}",
                  f"{PACKAGING_EXEC_FOLDER}", "debian-stretch", "all")


def test_build_package_rpm():
    build_package(GH_TOKEN, BuildType.release,
                  f"{RPM_OUTPUT_FOLDER}",
                  f"{PACKAGING_EXEC_FOLDER}", "centos-8", "13")


def test_sign_packages():
    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_password.gpg")
    gpg_fingerprint = get_gpg_fingerprint_from_name(TEST_GPG_KEY_NAME)
    secret_key = get_secret_key_by_fingerprint_with_password(gpg_fingerprint, TEST_GPG_KEY_PASSPHRASE)
    define_rpm_public_key_to_machine(gpg_fingerprint)
    sign_packages(RPM_OUTPUT_FOLDER, DEB_OUTPUT_FOLDER, secret_key, TEST_GPG_KEY_PASSPHRASE)
    verify_rpm_signature_in_dir(RPM_OUTPUT_FOLDER)

    delete_gpg_key_by_name(TEST_GPG_KEY_NAME)
    run(f"rm -r {DEB_OUTPUT_FOLDER}")
    run(f"rm -r {RPM_OUTPUT_FOLDER}")
