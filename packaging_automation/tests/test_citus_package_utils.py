import os
import subprocess

import pathlib2
import pytest

from .test_utils import generate_new_gpg_key
from ..citus_package import (
    decode_os_and_release,
    is_docker_running,
    get_signing_credentials,
    get_postgres_versions,
    build_package,
    BuildType,
    sign_packages,
    SigningCredentials,
    InputOutputParameters,
)
from ..common_tool_methods import (
    delete_all_gpg_keys_by_name,
    get_gpg_fingerprints_by_name,
    run,
    get_private_key_by_fingerprint_without_passphrase,
    define_rpm_public_key_to_machine,
    delete_rpm_key_by_name,
    get_private_key_by_fingerprint_with_passphrase,
    verify_rpm_signature_in_dir,
    transform_key_into_base64_str,
)

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
TEST_GPG_KEY_PASSPHRASE = "Citus123"
GH_TOKEN = os.getenv("GH_TOKEN")

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages"
INPUT_OUTPUT_PARAMETERS = InputOutputParameters.build(
    PACKAGING_EXEC_FOLDER, OUTPUT_FOLDER, output_validation=False
)


def setup_module():
    if not os.path.exists("packaging_test"):
        run(
            f"git clone --branch all-citus-unit-tests https://github.com/citusdata/packaging.git {PACKAGING_SOURCE_FOLDER}"
        )


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
    signing_credentials = get_signing_credentials("verysecretkey", "123")
    assert (
        signing_credentials.secret_key == "verysecretkey"
        and signing_credentials.passphrase == "123"
    )

    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)

    generate_new_gpg_key(
        f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging.gpg"
    )
    os.environ["PACKAGING_PASSPHRASE"] = TEST_GPG_KEY_PASSPHRASE
    signing_credentials = get_signing_credentials("", TEST_GPG_KEY_PASSPHRASE)
    fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(fingerprints) > 0
    expected_gpg_key = get_private_key_by_fingerprint_without_passphrase(
        fingerprints[0]
    )
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    assert (
        signing_credentials.secret_key
        == transform_key_into_base64_str(expected_gpg_key)
        and signing_credentials.passphrase == TEST_GPG_KEY_PASSPHRASE
    )


def test_delete_rpm_key_by_name():
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(
        f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_passphrase.gpg"
    )
    fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(fingerprints) > 0
    define_rpm_public_key_to_machine(fingerprints[0])
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)

    # return code is checked so check is not required
    # pylint: disable=subprocess-run-check
    output = subprocess.run(
        ["rpm", "-q gpg-pubkey", "--qf %{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert (
        TEST_GPG_KEY_NAME not in output.stdout.decode("ascii")
        and output.returncode == 1
    )


def test_get_postgres_versions():
    release_versions, nightly_versions = get_postgres_versions(
        "debian", f"{TEST_BASE_PATH}/packaging_automation/tests/files"
    )
    assert release_versions[0] == "all" and nightly_versions[0] == "all"

    release_versions, nightly_versions = get_postgres_versions(
        "el", f"{TEST_BASE_PATH}/packaging_automation/tests/files"
    )
    assert release_versions == ["11", "12", "13"] and nightly_versions == [
        "12",
        "13",
        "14",
    ]


def test_build_package_debian():
    input_output_parameters = InputOutputParameters.build(
        PACKAGING_EXEC_FOLDER,
        f"{OUTPUT_FOLDER}/debian-stretch",
        output_validation=False,
    )

    build_package(
        github_token=GH_TOKEN,
        build_type=BuildType.release,
        docker_platform="debian-stretch",
        postgres_version="all",
        input_output_parameters=input_output_parameters,
    )


def test_build_package_rpm():
    input_output_parameters = InputOutputParameters.build(
        PACKAGING_EXEC_FOLDER,
        f"{OUTPUT_FOLDER}/debian-stretch",
        output_validation=False,
    )

    build_package(
        github_token=GH_TOKEN,
        build_type=BuildType.release,
        docker_platform="centos-8",
        postgres_version="13",
        input_output_parameters=input_output_parameters,
    )


def test_sign_packages():
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(
        f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_passphrase.gpg"
    )
    gpg_fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(gpg_fingerprints) > 0
    private_key = get_private_key_by_fingerprint_with_passphrase(
        gpg_fingerprints[0], TEST_GPG_KEY_PASSPHRASE
    )
    secret_key = transform_key_into_base64_str(private_key)
    define_rpm_public_key_to_machine(gpg_fingerprints[0])
    signing_credentials = SigningCredentials(
        secret_key=secret_key, passphrase=TEST_GPG_KEY_PASSPHRASE
    )
    input_output_parameters = InputOutputParameters.build(
        PACKAGING_EXEC_FOLDER, f"{OUTPUT_FOLDER}", output_validation=False
    )
    sign_packages(
        sub_folder="centos-8",
        signing_credentials=signing_credentials,
        input_output_parameters=input_output_parameters,
    )
    sign_packages(
        sub_folder="debian-stretch",
        signing_credentials=signing_credentials,
        input_output_parameters=input_output_parameters,
    )
    verify_rpm_signature_in_dir(OUTPUT_FOLDER)

    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    run(f"rm -r {OUTPUT_FOLDER}")
