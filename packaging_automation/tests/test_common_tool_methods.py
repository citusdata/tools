import os
import uuid
from datetime import datetime
from shutil import copyfile

import pathlib2
from github import Github

from .test_utils import generate_new_gpg_key
from ..common_tool_methods import (
    DEFAULT_ENCODING_FOR_FILE_HANDLING,
    DEFAULT_UNICODE_ERROR_HANDLER,
    append_line_in_file,
    define_rpm_public_key_to_machine,
    delete_all_gpg_keys_by_name,
    delete_rpm_key_by_name,
    filter_prs_by_label,
    find_nth_matching_line_and_line_number,
    find_nth_occurrence_position,
    get_current_branch,
    get_gpg_fingerprints_by_name,
    get_last_commit_message,
    get_minor_version,
    get_patch_version_regex,
    get_project_version_from_tag_name,
    get_prs_for_patch_release,
    get_supported_postgres_release_versions,
    get_upcoming_minor_version,
    get_version_details,
    is_major_release,
    is_tag_on_branch,
    local_branch_exists,
    prepend_line_in_file,
    process_template_file,
    remote_branch_exists,
    remove_prefix,
    remove_text_with_parenthesis,
    replace_line_in_file,
    rpm_key_matches_summary,
    run, run_with_output, str_array_to_str)

GITHUB_TOKEN = os.getenv("GH_TOKEN")
BASE_PATH = pathlib2.Path(__file__).parents[1]
TEST_BASE_PATH = pathlib2.Path(__file__).parent.absolute()
TEST_GPG_KEY_NAME = "Citus Data <packaging@citusdata.com>"


def test_find_nth_occurrence_position():
    assert find_nth_occurrence_position("foofoo foofoo", "foofoo", 2) == 7


def test_find_nth_matching_line_number_by_regex():
    assert find_nth_matching_line_and_line_number("citusx\n citusx\ncitusx", "^citusx$", 2)[0] == 2
    assert find_nth_matching_line_and_line_number("citusx\n citusx\ncitusx", "^citusy$", 2)[0] == -1


def test_is_major_release():
    assert is_major_release("10.0.0")
    assert not is_major_release("10.0.1")


def test_get_project_version_from_tag_name():
    tag_name = "v10.0.3"
    assert get_project_version_from_tag_name(tag_name) == "10.0.3"


def test_str_array_to_str():
    assert str_array_to_str(["1", "2", "3", "4"]) == "1\n2\n3\n4\n"


def test_run():
    result = run("echo 'Run' method is performing fine ")
    assert result.returncode == 0


def test_remove_paranthesis_from_string():
    assert remove_text_with_parenthesis("out of paranthesis (inside paranthesis)") == "out of paranthesis "


def test_get_version_details():
    assert get_version_details("10.0.1") == {"major": "10", "minor": "0", "patch": "1"}


def test_is_tag_on_branch():
    current_branch = get_current_branch(os.getcwd())
    run("git checkout develop")
    assert is_tag_on_branch("v0.8.3", "develop")
    assert not is_tag_on_branch("v1.8.3", "develop")
    run(f"git checkout {current_branch}")


def test_replace_line_in_file():
    replace_str = "Summary:     Replace Test"
    copy_file_path = f"{TEST_BASE_PATH}/files/citus_copy.spec"
    copyfile(f"{TEST_BASE_PATH}/files/citus.spec", copy_file_path)
    replace_line_in_file(copy_file_path, r"^Summary:	*", replace_str)
    try:
        with open(copy_file_path, "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
                  errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
            content = reader.read()
            lines = content.splitlines()
            assert lines[5] == replace_str
    finally:
        os.remove(copy_file_path)


def test_get_upcoming_minor_version():
    assert get_upcoming_minor_version("10.1.0") == "10.2"


def test_get_last_commit_message():
    current_branch_name = get_current_branch(os.getcwd())
    test_branch_name = f"test{uuid.uuid4()}"
    run(f"git checkout -b {test_branch_name}")
    try:
        with open(test_branch_name, "w", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
                  errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
            writer.write("Test content")
        run("git add .")
        commit_message = f"Test message for {test_branch_name}"
        run(f"git commit -m '{commit_message}'")
        assert get_last_commit_message(os.getcwd()) == f"{commit_message}\n"
    finally:
        run(f"git checkout {current_branch_name}")
        run(f"git branch -D {test_branch_name}")


def test_local_branch_exist():
    run("git fetch")
    current_branch_name = get_current_branch(os.getcwd())
    branch_name = "develop-local-test"
    assert remote_branch_exists("develop", os.getcwd())
    assert not remote_branch_exists("develop2", os.getcwd())
    try:
        run(f"git checkout -b {branch_name}")
        assert local_branch_exists(branch_name, os.getcwd())
        run(f"git checkout {current_branch_name} ")
    finally:
        run(f"git branch -D {branch_name}")

    assert not remote_branch_exists("develop_test", os.getcwd())


def test_remote_branch_exist():
    run("git fetch")
    assert remote_branch_exists("develop", os.getcwd())
    assert not remote_branch_exists(f"develop{uuid.uuid4()}", os.getcwd())


def test_get_minor_version():
    assert get_minor_version("10.0.3") == "10.0"


def test_get_patch_version_regex():
    assert get_patch_version_regex("10.0.3") == r"^10\.0\.\d{1,3}$"


def test_append_line_in_file():
    test_file = "test_append.txt"
    try:
        with open(test_file, "a", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
                  errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
            writer.write("Test line 1\n")
            writer.write("Test line 2\n")
            writer.write("Test line 3\n")
            writer.write("Test line 4\n")
            writer.write("Test line 5\n")
            writer.write("Test line 6\n")
            writer.write("Test line 7\n")
            writer.write("Test line 8\n")
        append_line_in_file(test_file, "^Test line 1", "Test line 1.5")
        append_line_in_file(test_file, "^Test line 2", "Test line 2.5")
        append_line_in_file(test_file, "^Test line 5", "Test line 5.5")

        with open(test_file, "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
                  errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
            lines = reader.readlines()
            assert len(lines) == 11
            assert lines[0] == "Test line 1\n"
            assert lines[1] == "Test line 1.5\n"
            assert lines[2] == "Test line 2\n"
            assert lines[3] == "Test line 2.5\n"
    finally:
        os.remove(test_file)


def test_prepend_line_in_file():
    test_file = "test_prepend.txt"
    try:
        with open(test_file, "a", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
                  errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
            writer.write("Test line 1\n")
            writer.write("Test line 2\n")
            writer.write("Test line 3\n")
            writer.write("Test line 4\n")
            writer.write("Test line 5\n")
            writer.write("Test line 6\n")
            writer.write("Test line 7\n")
            writer.write("Test line 8\n")
        prepend_line_in_file(test_file, "^Test line 1", "Test line 0.5")
        prepend_line_in_file(test_file, "^Test line 2", "Test line 1.5")
        prepend_line_in_file(test_file, "^Test line 5", "Test line 4.5")

        with open(test_file, "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
                  errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
            lines = reader.readlines()
            assert len(lines) == 11
            assert lines[0] == "Test line 0.5\n"
            assert lines[1] == "Test line 1\n"
            assert lines[2] == "Test line 1.5\n"
            assert lines[3] == "Test line 2\n"
    finally:
        os.remove(test_file)


def test_getprs():
    # created at is not seen on Github. Should be checked on API result
    g = Github(GITHUB_TOKEN)
    repository = g.get_repo("citusdata/citus")
    prs = get_prs_for_patch_release(repository, datetime.strptime('2021.02.26', '%Y.%m.%d'), "master",
                                    datetime.strptime('2021.03.02', '%Y.%m.%d'))
    assert len(prs) == 6
    assert prs[0].number == 4748


def test_getprs_with_backlog_label():
    g = Github(GITHUB_TOKEN)
    repository = g.get_repo("citusdata/citus")
    prs = get_prs_for_patch_release(repository, datetime.strptime('2021.02.20', '%Y.%m.%d'), "master",
                                    datetime.strptime('2021.02.27', '%Y.%m.%d'))
    prs_backlog = filter_prs_by_label(prs, "backport")
    assert len(prs_backlog) == 1
    assert prs_backlog[0].number == 4746


def test_process_template_file():
    content = process_template_file("10.0.3", f"{BASE_PATH}/templates", "docker/alpine/alpine.tmpl.dockerfile", "13.2")
    with open(f"{TEST_BASE_PATH}/files/verify/expected_alpine_10.0.3.txt", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        expected_content = reader.read()
        assert expected_content == content


def test_remove_prefix():
    assert remove_prefix("test_prefix", "test_") == "prefix"
    assert remove_prefix("test_prefix", "part") == "test_prefix"


def test_delete_rpm_key_by_name():
    delete_all_gpg_keys_by_name(TEST_GPG_KEY_NAME)
    generate_new_gpg_key(f"{TEST_BASE_PATH}/files/gpg/packaging_with_passphrase.gpg")
    fingerprints = get_gpg_fingerprints_by_name(TEST_GPG_KEY_NAME)
    assert len(fingerprints) > 0
    define_rpm_public_key_to_machine(fingerprints[0])
    delete_rpm_key_by_name(TEST_GPG_KEY_NAME)
    result = run_with_output("rpm -q gpg-pubkey")
    output = result.stdout.decode("ascii")
    key_lines = output.splitlines()
    for key_line in key_lines:
        assert not rpm_key_matches_summary(key_line, TEST_GPG_KEY_NAME)


def test_get_supported_postgres_versions():
    postgres_release_versions_10_0_0 = get_supported_postgres_release_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml", "10.0.0")
    assert postgres_release_versions_10_0_0 == (['11', '12', '13'])

    postgres_release_versions_9_2_1 = get_supported_postgres_release_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml", "9.2.1")
    assert postgres_release_versions_9_2_1 == (['11', '12'])

    postgres_release_versions_10_1_1 = get_supported_postgres_release_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml", "10.1.1")
    assert postgres_release_versions_10_1_1 == (['12', '13'])

    postgres_release_versions_7_2_1 = get_supported_postgres_release_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml", "7.2.1")
    assert postgres_release_versions_7_2_1 == (['10', '11'])

    postgres_release_versions_10_2_0 = get_supported_postgres_release_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml", "10.2.0")
    assert postgres_release_versions_10_2_0 == (['12', '13', '14'])

    postgres_release_versions_10_2_1 = get_supported_postgres_release_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml", "10.2.1")
    assert postgres_release_versions_10_2_1 == (['12', '13', '14'])

    postgres_nightly_versions_10_2_1 = get_supported_postgres_nightly_versions(
        f"{TEST_BASE_PATH}/files/postgres-matrix/postgres-matrix-success.yml")
    assert postgres_nightly_versions_10_2_1 == (['12', '13', '14'])
