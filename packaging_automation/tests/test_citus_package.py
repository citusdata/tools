import glob
import os

import pathlib2
import pytest
from dotenv import dotenv_values

from .test_utils import generate_new_gpg_key
from ..citus_package import (
    POSTGRES_VERSION_FILE,
    BuildType,
    InputOutputParameters,
    PostgresVersionDockerImageType,
    SigningCredentials,
    build_packages,
    decode_os_and_release,
    get_build_platform,
    get_release_package_folder_name,
    get_postgres_versions,
    platform_postgres_version_source,
)
from ..common_tool_methods import (
    define_rpm_public_key_to_machine,
    delete_all_gpg_keys_by_name,
    delete_rpm_key_by_name,
    get_gpg_fingerprints_by_name,
    get_private_key_by_fingerprint_with_passphrase,
    is_rpm_file_signed,
    run,
    transform_key_into_base64_str,
    verify_rpm_signature_in_dir,
)
from ..upload_to_package_cloud import (
    delete_package_from_package_cloud,
    package_exists,
    upload_files_in_directory_to_package_cloud,
)

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])

PACKAGING_SOURCE_FOLDER = "packaging_test"
PACKAGING_EXEC_FOLDER = f"{TEST_BASE_PATH}/{PACKAGING_SOURCE_FOLDER}"
BASE_OUTPUT_FOLDER = f"{PACKAGING_EXEC_FOLDER}/packages"

single_postgres_package_counts = {
    "el/7": 2,
    "el/8": 1,
    "ol/7": 2,
    "ol/8": 1,
    "almalinux/9": 1,
    "almalinux/8": 1,
    "rockylinux/9": 3,
    "el/9": 1,
    "ol/9": 1,
    "debian/stretch": 2,
    "debian/bullseye": 2,
    "debian/bookworm": 2,
    "debian/trixie": 2,
    "ubuntu/bionic": 2,
    "ubuntu/focal": 2,
    "ubuntu/jammy": 2,
    "ubuntu/kinetic": 2,
    "ubuntu/noble": 2,
    "ubuntu/resolute": 2,
}

TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"
# Use the literal passphrase baked into the throwaway test key
# (tests/files/gpg/packaging_with_passphrase.gpg -> Passphrase: Citus123) rather
# than the prod PACKAGING_PASSPHRASE secret, so this unit test stays self-contained
# and immune to production signing-key/passphrase rotations. Matches the convention
# already used in test_citus_package_utils.py.
TEST_GPG_KEY_PASSPHRASE = "Citus123"
GH_TOKEN = os.getenv("GH_TOKEN")
PACKAGE_CLOUD_API_TOKEN = os.getenv("PACKAGE_CLOUD_API_TOKEN")
REPO_CLIENT_SECRET = os.getenv("REPO_CLIENT_SECRET")
PLATFORM = get_build_platform(
    os.getenv("PLATFORM"), os.getenv("PACKAGING_IMAGE_PLATFORM")
)
POSTGRES_VERSION = os.getenv("POSTGRES_VERSION")
PACKAGING_BRANCH_NAME = os.getenv("PACKAGING_BRANCH_NAME", "all-citus-unit-tests")


def get_required_package_count(input_files_dir: str, platform: str):
    release_versions, _ = get_postgres_versions(
        platform=platform, input_files_dir=input_files_dir
    )
    print(
        f"get_required_package_count: Release versions:{release_versions}:{single_postgres_package_counts[platform]}"
    )
    return len(release_versions) * single_postgres_package_counts[platform]


def setup_module():
    # Run tests against "all-citus-unit-tests" since we don't want to deal with the changes
    # made to "all-citus" in each release.
    packaging_branch_name = (
        "pgxn-citus" if PLATFORM == "pgxn" else PACKAGING_BRANCH_NAME
    )
    if not os.path.exists(PACKAGING_EXEC_FOLDER):
        run(
            f"git clone --branch {packaging_branch_name} https://github.com/citusdata/packaging.git"
            f" {PACKAGING_EXEC_FOLDER}"
        )


def teardown_module():
    if os.path.exists("packaging_test"):
        run("rm -rf packaging_test")


def test_build_packages():
    # postgres_version only narrows the build for "multiple"-image platforms (rpm distros),
    # where build_packages iterates one docker image per pg version. For "single"-image platforms
    # (debian/ubuntu/pgxn) the iterator is always ["all"], so postgres_version is a no-op and every
    # release version is built regardless of what is passed. Gate the filter-aware branches below on
    # that distinction so the test's skip/count logic always matches what build_packages actually
    # does, no matter what the external packaging matrix passes for a single-image platform.
    os_name, _ = decode_os_and_release(PLATFORM)
    version_filter_active = bool(POSTGRES_VERSION) and (
        platform_postgres_version_source[os_name]
        == PostgresVersionDockerImageType.multiple
    )
    # The packaging per-pg CI matrix enumerates pg{14..18} per rpm distro to drive
    # update_image into building every {os}-pg{N} base image, but the rpm release set is only
    # a subset (e.g. [15,16,17]). When POSTGRES_VERSION targets a version outside that set, there
    # is nothing for this test to build/sign, so skip gracefully (skip == success) rather than
    # letting build_packages raise. The image for that pg was still built by update_image, so
    # push_images downstream still reseeds it.
    if version_filter_active:
        release_versions, _ = get_postgres_versions(
            platform=PLATFORM, input_files_dir=PACKAGING_EXEC_FOLDER
        )
        if POSTGRES_VERSION not in release_versions:
            pytest.skip(
                f"pg{POSTGRES_VERSION} not in release set {release_versions} for {PLATFORM}"
            )

    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(
        f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_passphrase.gpg"
    )
    gpg_fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(gpg_fingerprints) > 0
    secret_key = transform_key_into_base64_str(
        get_private_key_by_fingerprint_with_passphrase(
            gpg_fingerprints[0], TEST_GPG_KEY_PASSPHRASE
        )
    )
    define_rpm_public_key_to_machine(gpg_fingerprints[0])
    signing_credentials = SigningCredentials(secret_key, TEST_GPG_KEY_PASSPHRASE)
    input_output_parameters = InputOutputParameters.build(
        PACKAGING_EXEC_FOLDER, BASE_OUTPUT_FOLDER, output_validation=False
    )

    build_packages(
        GH_TOKEN,
        PLATFORM,
        BuildType.release,
        signing_credentials,
        input_output_parameters,
        is_test=True,
        postgres_version=POSTGRES_VERSION,
    )
    verify_rpm_signature_in_dir(BASE_OUTPUT_FOLDER)
    _, os_version = decode_os_and_release(PLATFORM)
    sub_folder = get_release_package_folder_name(os_name, os_version)
    release_output_folder = f"{BASE_OUTPUT_FOLDER}/{sub_folder}"
    # Regression guard for the sign_packages path-doubling bug: the build output folder and the
    # folder sign_packages signs in must resolve to the SAME path. If build_packages leaks its
    # build-time output_dir mutation into sign_packages again, the sign path becomes a doubled
    # "{sub_folder}/{sub_folder}", matches no packages, and signing is silently skipped, leaving
    # the produced rpms unsigned. Assert every rpm actually produced at the build path carries a
    # real signature (no-op for deb/pgxn platforms, which produce no rpm files here).
    produced_rpms = glob.glob(f"{release_output_folder}/*.rpm")
    for produced_rpm in produced_rpms:
        assert is_rpm_file_signed(produced_rpm), (
            f"Produced package '{produced_rpm}' is unsigned; sign_packages path-doubling "
            f"regression detected (signing was silently skipped)."
        )
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)

    postgres_version_file_path = f"{PACKAGING_EXEC_FOLDER}/{POSTGRES_VERSION_FILE}"
    if PLATFORM != "pgxn":
        # When POSTGRES_VERSION restricts the build to a single in-set version (multiple-image
        # platforms only), only that version's packages are produced, so the expected count is the
        # per-version package count (single_postgres_package_counts), not the full
        # len(release_versions) * per-version count. When the filter is inactive — POSTGRES_VERSION
        # empty/None, or a single-image platform where it is a no-op — keep the all-versions
        # expectation.
        if version_filter_active:
            expected_package_count = single_postgres_package_counts[PLATFORM]
        else:
            expected_package_count = get_required_package_count(
                input_files_dir=PACKAGING_EXEC_FOLDER, platform=PLATFORM
            )
        assert len(os.listdir(release_output_folder)) == expected_package_count
        assert os.path.exists(postgres_version_file_path)
        config = dotenv_values(postgres_version_file_path)
        assert config["release_versions"] == "15,16,17"
        assert config["nightly_versions"] == "16,17,18"


def test_get_required_package_count():
    assert (
        get_required_package_count(
            input_files_dir=PACKAGING_EXEC_FOLDER, platform="el/8"
        )
        == 3
    )


def test_decode_os_packages():
    os, release = decode_os_and_release("el/7")
    assert os == "el" and release == "7"


def test_get_postgres_versions_ol_7():
    release_versions, nightly_versions = get_postgres_versions(
        input_files_dir=f"{os.getcwd()}/packaging_automation/tests/files/get_postgres_versions_tests",
        platform="ol/7",
    )
    # pg 15 is excluded for all releases with pg_exclude file
    assert len(release_versions) == 2 and release_versions == ["13", "14"]
    assert len(nightly_versions) == 2 and nightly_versions == ["13", "14"]


def test_get_postgres_versions_el_7():
    release_versions, nightly_versions = get_postgres_versions(
        input_files_dir=f"{os.getcwd()}/packaging_automation/tests/files/get_postgres_versions_tests",
        platform="el/7",
    )
    # pg 15 is excluded for all releases with pg_exclude file
    assert len(release_versions) == 2 and release_versions == ["13", "14"]
    assert len(nightly_versions) == 2 and nightly_versions == ["14", "15"]


def test_get_postgres_versions_debain_bullseye():
    release_versions, nightly_versions = get_postgres_versions(
        input_files_dir=f"{os.getcwd()}/packaging_automation/tests/files/get_postgres_versions_tests",
        platform="debian/bullseye",
    )
    # pg 15 is excluded for all releases with pg_exclude file
    assert len(release_versions) == 2 and release_versions == ["13", "14"]
    assert len(nightly_versions) == 2 and nightly_versions == ["14", "15"]


def test_upload_to_package_cloud():
    platform = get_build_platform(
        os.getenv("PLATFORM"), os.getenv("PACKAGING_IMAGE_PLATFORM")
    )
    current_branch = "all-citus"
    main_branch = "all-citus"
    output = upload_files_in_directory_to_package_cloud(
        BASE_OUTPUT_FOLDER,
        platform,
        PACKAGE_CLOUD_API_TOKEN,
        "citus-bot/sample",
        current_branch,
        main_branch,
    )
    distro_parts = platform.split("/")
    if len(distro_parts) != 2:
        raise ValueError(
            "Platform should consist of two parts splitted with '/' e.g. el/8"
        )
    for return_value in output.return_values:
        exists = package_exists(
            PACKAGE_CLOUD_API_TOKEN,
            "citus-bot",
            "sample",
            os.path.basename(return_value.file_name),
            platform,
        )
        if not exists:
            raise ValueError(
                f"{os.path.basename(return_value.file_name)} could not be found on package cloud"
            )

    for return_value in output.return_values:
        delete_output = delete_package_from_package_cloud(
            PACKAGE_CLOUD_API_TOKEN,
            "citus-bot",
            "sample",
            distro_parts[0],
            distro_parts[1],
            os.path.basename(return_value.file_name),
        )
        if delete_output.success_status:
            print(f"{os.path.basename(return_value.file_name)} deleted successfully")
        else:
            print(
                f"{os.path.basename(return_value.file_name)} can not be deleted. Message: {delete_output.message}"
            )
