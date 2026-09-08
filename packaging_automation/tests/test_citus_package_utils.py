import os
import subprocess
from unittest.mock import patch

import pathlib2
import pytest

from .test_utils import generate_new_gpg_key
from .. import upload_to_package_cloud
from ..citus_package import (
    decode_os_and_release,
    get_build_platform,
    get_docker_image_name,
    is_docker_running,
    get_signing_credentials,
    get_postgres_versions,
    build_package,
    BuildType,
    sign_packages,
    SigningCredentials,
    InputOutputParameters,
    get_package_version_without_release_stage_from_pkgvars,
    write_postgres_versions_into_file,
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
    platform_names,
)
from ..test_citus_package import (
    TestPlatform as PackageTestPlatform,
    get_test_platform_for_os_release,
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


def test_bullseye_is_not_an_active_platform():
    assert "debian/bullseye" not in platform_names()
    with pytest.raises(ValueError, match="bullseye is not among supported releases"):
        decode_os_and_release("debian/bullseye")
    with pytest.raises(ValueError, match="bullseye is not among supported releases"):
        get_docker_image_name("debian/bullseye")
    with pytest.raises(KeyError):
        get_build_platform(None, "debian,bullseye")
    assert (
        get_test_platform_for_os_release("debian/bullseye")
        == PackageTestPlatform.undefined
    )
    assert "debian/bullseye" not in upload_to_package_cloud.supported_distros


@pytest.mark.parametrize("release", ["bookworm", "trixie"])
def test_supported_debian_platforms(release):
    platform = f"debian/{release}"
    assert platform in platform_names()
    assert decode_os_and_release(platform) == ("debian", release)
    assert get_build_platform(None, f"debian,{release}") == platform
    assert get_docker_image_name(platform) == f"debian-{release}"
    test_platform = get_test_platform_for_os_release(platform)
    assert test_platform.value["docker_image_name"] == f"debian-{release}"
    assert platform in upload_to_package_cloud.supported_distros


def test_legacy_bullseye_package_operations():
    with patch.object(upload_to_package_cloud.requests, "get") as get:
        get.return_value.ok = True
        assert upload_to_package_cloud.package_exists(
            "test-token", "citus-bot", "sample", "old.deb", "debian/bullseye"
        )
        assert get.call_args.args[0] == (
            "https://packagecloud.io/api/v1/repos/citus-bot/sample/search?"
            "q=old.deb&filter=all&dist=debian%2Fbullseye"
        )
    with patch.object(upload_to_package_cloud.requests, "delete") as delete:
        delete.return_value.ok = True
        delete.return_value.content = b"deleted"
        result = upload_to_package_cloud.delete_package_from_package_cloud(
            "test-token", "citus-bot", "sample", "debian", "bullseye", "old.deb"
        )
        assert result.success_status
        delete.assert_called_once_with(
            "https://test-token:@packagecloud.io/api/v1/repos/citus-bot/sample/"
            "debian/bullseye/old.deb",
            timeout=60,
        )


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
        platform="el/8",
        input_files_dir=f"{TEST_BASE_PATH}/packaging_automation/tests/files",
    )
    assert release_versions == ["11", "12", "13"] and nightly_versions == [
        "12",
        "13",
        "14",
    ]


def test_build_package_debian():
    input_output_parameters = InputOutputParameters.build(
        PACKAGING_EXEC_FOLDER,
        f"{OUTPUT_FOLDER}/debian-bookworm",
        output_validation=False,
    )

    package_version = get_package_version_without_release_stage_from_pkgvars(
        input_output_parameters.input_files_dir
    )
    write_postgres_versions_into_file(
        input_output_parameters.input_files_dir, package_version
    )

    build_package(
        github_token=GH_TOKEN,
        build_type=BuildType.release,
        docker_platform="debian-bookworm",
        postgres_version="all",
        input_output_parameters=input_output_parameters,
        is_test=True,
    )


def test_build_package_rpm():
    input_output_parameters = InputOutputParameters.build(
        PACKAGING_EXEC_FOLDER,
        f"{OUTPUT_FOLDER}/rpm_build",
        output_validation=False,
    )

    build_package(
        github_token=GH_TOKEN,
        build_type=BuildType.release,
        docker_platform="almalinux-9",
        postgres_version="17",
        input_output_parameters=input_output_parameters,
        is_test=True,
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
        sub_folder="rpm_build",
        signing_credentials=signing_credentials,
        input_output_parameters=input_output_parameters,
    )
    sign_packages(
        sub_folder="debian-bookworm",
        signing_credentials=signing_credentials,
        input_output_parameters=input_output_parameters,
    )
    verify_rpm_signature_in_dir(OUTPUT_FOLDER)

    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    run(f"rm -r {OUTPUT_FOLDER}")
