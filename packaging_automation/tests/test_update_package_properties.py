import pytest
import os
from shutil import copyfile

from .test_utils import are_strings_equal
from ..update_package_properties import *

TEST_BASE_PATH = pathlib2.Path(__file__).parent.absolute()
BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[1])
GITHUB_TOKEN = os.getenv("GH_TOKEN")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", default="10.0.3")
TAG_NAME = os.getenv("TAG_NAME", default="v10.0.3")
PROJECT_NAME = os.getenv("PROJECT_NAME", default="citus")
MICROSOFT_EMAIL = os.getenv("MICROSOFT_EMAIL", default="gindibay@microsoft.com")
NAME_SURNAME = os.getenv("NAME_SURNAME", default="Gurkan Indibay")
CHANGELOG_DATE_STR = os.getenv("CHANGELOG_DATE", 'Thu, 18 Mar 2021 01:40:08 +0000')
CHANGELOG_DATE = datetime.strptime(CHANGELOG_DATE_STR, '%a, %d %b %Y %H:%M:%S %z')


def default_changelog_param_for_test(latest_changelog, changelog_date):
    changelog_param = PackagePropertiesParams(project_name=PROJECT_NAME, project_version=PROJECT_VERSION, fancy=True,
                                              fancy_version_number=1, microsoft_email=MICROSOFT_EMAIL,
                                              name_surname=NAME_SURNAME, changelog_date=changelog_date,
                                              latest_changelog=latest_changelog)
    return changelog_param


DEFAULT_CHANGELOG_PARAM_FOR_TEST = default_changelog_param_for_test("", CHANGELOG_DATE)


def test_get_version_number():
    assert DEFAULT_CHANGELOG_PARAM_FOR_TEST.version_number() == "10.0.3-1"


def test_get_version_number_with_project_name():
    assert DEFAULT_CHANGELOG_PARAM_FOR_TEST.version_number_with_project_name() == "10.0.3.citus-1"


def test_find_nth_overlapping():
    assert find_nth_overlapping("foofoo foofoo", "foofoo", 2) == 7


def test_get_changelog_for_tag():
    changelog = changelog_for_tag(GITHUB_TOKEN, "citus", "v10.0.3")
    with open(f"{TEST_BASE_PATH}/files/verify/expected_changelog_10.0.3.txt", "r") as reader:
        expected_changelog = reader.read()
    assert expected_changelog == changelog


def test_get_debian_changelog_header():
    header = debian_changelog_header("### citus v10.0.3 (March 16, 2021) ###", True, 2)
    assert header == "citus (10.0.3.citus-2) stable; urgency=low"


def test_get_last_changelog_from_debian():
    refer_file_path = f"{TEST_BASE_PATH}/files/verify/debian_changelog_with_10.0.3.txt"
    expected_file_path = f"{TEST_BASE_PATH}/files/verify/expected_debian_latest_v10.0.3.txt"
    with open(refer_file_path, "r") as reader:
        changelog = reader.read()

    latest_changelog = get_last_changelog_content_from_debian(changelog)

    with open(expected_file_path, "r") as reader:
        expected_output = reader.read()

    are_strings_equal(expected_output, latest_changelog)


def test_prepend_latest_changelog_into_debian_changelog():
    refer_file_path = f"{TEST_BASE_PATH}/files/debian.changelog.refer"
    changelog_file_path = f"{TEST_BASE_PATH}/files/debian.changelog"
    copyfile(refer_file_path, changelog_file_path)
    latest_changelog = changelog_for_tag(GITHUB_TOKEN, PROJECT_NAME, TAG_NAME)

    changelog_param = default_changelog_param_for_test(latest_changelog, CHANGELOG_DATE)

    try:
        prepend_latest_changelog_into_debian_changelog(changelog_param, changelog_file_path)
        verify_prepend_debian_changelog(changelog_file_path)
    finally:
        os.remove(changelog_file_path)


def test_prepend_latest_changelog_into_debian_changelog_10_0_3_already_included():
    refer_file_path = f"{TEST_BASE_PATH}/files/debian.changelog_include_10_0_3.refer"
    changelog_file_path = f"{TEST_BASE_PATH}/files/debian.changelog"
    copyfile(refer_file_path, changelog_file_path)
    latest_changelog = changelog_for_tag(GITHUB_TOKEN, PROJECT_NAME, TAG_NAME)
    changelog_param = default_changelog_param_for_test(latest_changelog, datetime.now())
    try:

        with pytest.raises(ValueError):
            prepend_latest_changelog_into_debian_changelog(changelog_param, changelog_file_path)
    finally:
        os.remove(changelog_file_path)


def verify_prepend_debian_changelog(changelog_file_path):
    with open(changelog_file_path, "r") as reader:
        content = reader.read()
        latest_changelog = get_last_changelog_content_from_debian(content)
    with open(f"{TEST_BASE_PATH}/files/verify/expected_debian_latest_v10.0.3.txt", "r") as reader:
        expected_content = reader.read()
    are_strings_equal(expected_content, latest_changelog)


def test_convert_citus_changelog_into_rpm_changelog():
    changelog_param = default_changelog_param_for_test("", CHANGELOG_DATE)
    changelog = convert_citus_changelog_into_rpm_changelog(changelog_param)
    with open(f"{TEST_BASE_PATH}/files/verify/rpm_latest_changelog_reference.txt", "r") as reader:
        content = reader.read()
    assert content == changelog


def test_update_rpm_spec():
    project_name = "citus"
    spec_file = f"{TEST_BASE_PATH}/files/{spec_file_name(project_name)}"
    spec_file_copy = f"{os.getcwd()}/{spec_file_name(project_name)}_copy"
    spec_file_reference = f"{TEST_BASE_PATH}/files/citus_include_10_0_3.spec"
    templates_path = f"{BASE_PATH}/templates"
    copyfile(spec_file, spec_file_copy)
    try:
        changelog_param = default_changelog_param_for_test("", CHANGELOG_DATE)
        update_rpm_spec(changelog_param, spec_file, templates_path)
        verify_rpm_spec(spec_file_reference, spec_file)
    finally:
        copyfile(spec_file_copy, spec_file)
        os.remove(spec_file_copy)


def test_update_rpm_spec_include_10_0_3():
    project_name = "citus"
    spec_file = f"{TEST_BASE_PATH}/files/citus_include_10_0_3.spec"
    spec_file_copy = f"{os.getcwd()}/{spec_file_name(project_name)}_copy"
    templates_path = f"{BASE_PATH}/templates"
    copyfile(spec_file, spec_file_copy)
    try:
        changelog_param = default_changelog_param_for_test("", CHANGELOG_DATE)
        with pytest.raises(ValueError):
            update_rpm_spec(changelog_param, spec_file, templates_path)
    finally:
        copyfile(spec_file_copy, spec_file)
        os.remove(spec_file_copy)


def verify_rpm_spec(spec_file_reference, spec_file_for_test):
    with open(spec_file_for_test, "r") as reader_test:
        with open(spec_file_reference, "r") as reader_reference:
            test_str = reader_test.read()
            reference_str = reader_reference.read()
            are_strings_equal(reference_str, test_str)


def test_update_pkg_vars():
    templates_path = f"{BASE_PATH}/templates"
    pkgvars_path = f"{TEST_BASE_PATH}/files/pkgvars"
    pkgvars_copy_path = f"{pkgvars_path}_copy"
    copyfile(pkgvars_path, pkgvars_copy_path)
    try:
        update_pkgvars(PROJECT_NAME, PROJECT_VERSION, True, 1, templates_path, f"{TEST_BASE_PATH}/files/")
        verify_pkgvars(pkgvars_path)
    finally:
        copyfile(pkgvars_copy_path, pkgvars_path)
        os.remove(pkgvars_copy_path)


def verify_pkgvars(pkgvars_path):
    with open(pkgvars_path, "r") as reader:
        content = reader.read()
        index = content.find(f"pkglatest={PROJECT_VERSION}.{PROJECT_NAME}-1")
        assert index > -1


def test_update_all_changes():
    pkgvars_path = f"{TEST_BASE_PATH}/files/pkgvars"
    pkgvars_copy_path = f"{pkgvars_path}_copy"
    spec_file = f"{TEST_BASE_PATH}/files/{spec_file_name(PROJECT_NAME)}"
    spec_file_copy = f"{spec_file}_copy"
    spec_file_reference = f"{TEST_BASE_PATH}/files/{spec_file_name(PROJECT_NAME)}"

    changelog_file_path = f"{TEST_BASE_PATH}/files/debian/changelog"
    changelog_file_copy_path = f"{changelog_file_path}_copy"
    copyfile(changelog_file_path, changelog_file_copy_path)
    copyfile(pkgvars_path, pkgvars_copy_path)
    copyfile(spec_file, spec_file_copy)

    try:
        package_properties_param = PackagePropertiesParams(project_name=PROJECT_NAME,
                                                           project_version=PROJECT_VERSION, fancy=True,
                                                           fancy_version_number=1,
                                                           name_surname=NAME_SURNAME, microsoft_email=MICROSOFT_EMAIL,
                                                           changelog_date=CHANGELOG_DATE)
        update_all_changes(GITHUB_TOKEN, package_properties_param, TAG_NAME, f"{TEST_BASE_PATH}/files")
        verify_prepend_debian_changelog(changelog_file_path)
        verify_pkgvars(pkgvars_path)
        verify_rpm_spec(spec_file_reference, spec_file)
    finally:
        copyfile(changelog_file_copy_path, changelog_file_path)
        copyfile(pkgvars_copy_path, pkgvars_path)
        copyfile(spec_file_copy, spec_file)

        os.remove(changelog_file_copy_path)
        os.remove(pkgvars_copy_path)
        os.remove(spec_file_copy)


def test_regex():
    print(re.match(r"^### \w+\sv\d+\.\d+\.\d+\s\(\w+\s\d+,\s\d+\)\s###$", "### citus v10.0.3 (March 16, 2021) ###"))
