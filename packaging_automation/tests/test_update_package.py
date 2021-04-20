from ..citus_package import *
from ..common_tool_methods import *
import pytest
import pathlib2

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[0])


def generate_new_gpg_key():
    run(f"gpg --batch --generate-key {TEST_BASE_PATH}/files/gpg/packaging.gpg")


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

    delete_gpg_key_by_email("packaging@citusdata.com")

    generate_new_gpg_key()
    os.environ["PACKAGING_PASSPHRASE"] = "secret_passphrase"
    secret_key, passphrase = get_signing_credentials("")
    assert secret_key == get_secret_key_by_fingerprint(
        get_gpg_key_from_email("packaging@citusdata.com")) and passphrase == "secret_passphrase"


def test_get_postgres_versions():
    release_versions, nightly_versions = get_postgres_versions("debian", f"{TEST_BASE_PATH}/files")
    assert release_versions[0] == "all" and nightly_versions[0] == "all"

    release_versions, nightly_versions = get_postgres_versions("el", f"{TEST_BASE_PATH}/files")
    assert release_versions[0] == "11" and len(release_versions) == 3 and nightly_versions[0] == "12" and len(
        nightly_versions) == 2


def test_build_package():
    
    build_package("GITHUB_TOKEN", BuildType.release, f"{TEST_BASE_PATH}/files",
                  f"{TEST_BASE_PATH}/files/packages", "centos-8", "13")


def test_build_packages():
    assert False


def test_sign_packages():
    assert False
