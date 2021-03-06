import os
import subprocess

import pathlib2
import pytest

from .test_utils import generate_new_gpg_key
from ..citus_package import (decode_os_and_release, is_docker_running, get_signing_credentials, get_postgres_versions,
                             build_package, BuildType, sign_packages)
from ..common_tool_methods import (delete_all_gpg_keys_by_name, get_gpg_fingerprints_by_name, run,
                                   get_private_key_by_fingerprint_without_passphrase, define_rpm_public_key_to_machine,
                                   delete_rpm_key_by_name, get_private_key_by_fingerprint_with_passphrase,
                                   verify_rpm_signature_in_dir, transform_key_into_base64_str)

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
TEST_GPG_KEY_PASSPHRASE = "Citus123"
GH_TOKEN = os.getenv("GH_TOKEN")

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages"


def setup_module():
    if not os.path.exists("packaging_test"):
        run(f"git clone --branch all-citus https://github.com/citusdata/packaging.git {PACKAGING_SOURCE_FOLDER}")


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
        decode_os_and_release("debian")

    with pytest.raises(ValueError):
        decode_os_and_release("debian/anders")


def test_is_docker_running():
    assert is_docker_running()


def test_get_signing_credentials():
    secret_key, passphrase = get_signing_credentials("verysecretkey", "123")
    assert secret_key == "verysecretkey" and passphrase == "123"

    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)

    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging.gpg")
    os.environ["PACKAGING_PASSPHRASE"] = TEST_GPG_KEY_PASSPHRASE
    secret_key, passphrase = get_signing_credentials("", TEST_GPG_KEY_PASSPHRASE)
    fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(fingerprints) > 0
    expected_gpg_key = get_private_key_by_fingerprint_without_passphrase(fingerprints[0])
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    assert secret_key == transform_key_into_base64_str(expected_gpg_key) and passphrase == TEST_GPG_KEY_PASSPHRASE


def test_delete_rpm_key_by_name():
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_passphrase.gpg")
    fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(fingerprints) > 0
    define_rpm_public_key_to_machine(fingerprints[0])
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
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
                  f"{OUTPUT_FOLDER}/debian-stretch",
                  f"{PACKAGING_EXEC_FOLDER}", "debian-stretch", "all")


def test_build_package_rpm():
    build_package(GH_TOKEN, BuildType.release,
                  f"{OUTPUT_FOLDER}/centos-8",
                  f"{PACKAGING_EXEC_FOLDER}", "centos-8", "13")


def test_sign_packages():
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_passphrase.gpg")
    gpg_fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(gpg_fingerprints) > 0
    private_key = get_private_key_by_fingerprint_with_passphrase(gpg_fingerprints[0], TEST_GPG_KEY_PASSPHRASE)
    secret_key = transform_key_into_base64_str(private_key)
    define_rpm_public_key_to_machine(gpg_fingerprints[0])
    sign_packages(OUTPUT_FOLDER, "centos-8", secret_key, TEST_GPG_KEY_PASSPHRASE, PACKAGING_EXEC_FOLDER)
    sign_packages(OUTPUT_FOLDER, "debian-stretch", secret_key, TEST_GPG_KEY_PASSPHRASE, PACKAGING_EXEC_FOLDER)
    verify_rpm_signature_in_dir(OUTPUT_FOLDER)

    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    run(f"rm -r {OUTPUT_FOLDER}")
