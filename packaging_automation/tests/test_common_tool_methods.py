import os
from datetime import datetime
from shutil import copyfile

import pathlib2
from github import Github
import uuid

from ..common_tool_methods import (
    find_nth_occurrence_position, is_major_release,
    str_array_to_str, run, remove_text_with_parenthesis, get_version_details,
    replace_line_in_file, get_prs_for_patch_release, filter_prs_by_label,
    get_project_version_from_tag_name, find_nth_matching_line_and_line_number, get_minor_version,
    append_line_in_file, prepend_line_in_file, does_remote_branch_exist, get_current_branch, get_patch_version_regex,
    does_local_branch_exist)

GITHUB_TOKEN = os.getenv("GH_TOKEN")
TEST_BASE_PATH = pathlib2.Path(__file__).parent.absolute()


def test_find_nth_occurrence_position():
    assert find_nth_occurrence_position("foofoo foofoo", "foofoo", 2) == 7


def test_find_nth_matching_line_number_by_regex():
    # Two match case
    assert find_nth_matching_line_and_line_number("citusx\n citusx\ncitusx", "^citusx$", 2)[0] == 2
    # No match case
    assert find_nth_matching_line_and_line_number("citusx\n citusx\ncitusx", "^citusy$", 2)[0] == -1


def test_is_major_release():
    assert is_major_release("10.0.0")
    assert not is_major_release("10.0.1")


def test_get_project_version_from_tag_name():
    tag_name = "v10.0.3"
    assert "10.0.3" == get_project_version_from_tag_name(tag_name)


def test_str_array_to_str():
    assert "1\n2\n3\n4\n" == str_array_to_str(["1", "2", "3", "4"])


def test_run():
    result = run("echo 'Run' method is performing fine ")
    assert 0 == result.returncode


def test_remove_paranthesis_from_string():
    assert "out of paranthesis " == remove_text_with_parenthesis("out of paranthesis (inside paranthesis)")


def test_get_version_details():
    assert {"major": "10", "minor": "0", "patch": "1"} == get_version_details("10.0.1")


def test_replace_line_in_file():
    replace_str = "Summary:     Replace Test"
    copy_file_path = f"{TEST_BASE_PATH}/files/citus_copy.spec"
    copyfile(f"{TEST_BASE_PATH}/files/citus.spec", copy_file_path)
    replace_line_in_file(copy_file_path, r"^Summary:	*", replace_str)
    try:
        with open(copy_file_path, "r") as reader:
            content = reader.read()
            lines = content.splitlines()
            assert lines[5] == replace_str
    finally:
        os.remove(copy_file_path)


def test_does_local_branch_exist():
    current_branch_name = get_current_branch(os.getcwd())
    branch_name = "develop-local-test"
    assert does_remote_branch_exist("develop", os.getcwd())
    assert not does_remote_branch_exist("develop2", os.getcwd())
    try:
        run(f"git checkout -b {branch_name}")
        assert does_local_branch_exist(branch_name, os.getcwd())
        run(f"git checkout {current_branch_name} ")
    finally:
        run(f"git branch -D {branch_name}")

    assert not does_remote_branch_exist("develop_test", os.getcwd())


def test_does_remote_branch_exist():
    current_branch_name = get_current_branch(os.getcwd())
    branch_name = "develop-remote-test"
    try:
        try:
            run(f"git branch -D {branch_name}")
        except:
            print(f"{branch_name} already deleted ")
        run(f"git checkout develop")
        run(f"git checkout -b {branch_name}")
        run(f"git push --set-upstream origin {branch_name}")
        run(f"git checkout develop")
        run(f"git branch -D {branch_name}")
        assert does_remote_branch_exist(branch_name, os.getcwd())
        assert not does_remote_branch_exist(f"{branch_name}{uuid.uuid4()}", os.getcwd())
    finally:
        run(f"git checkout {current_branch_name} ")
        run(f"git push origin --delete {branch_name}")


def test_get_minor_version():
    assert "10.0" == get_minor_version("10.0.3")


def test_get_patch_version_regex():
    assert "^10\.0\.\d{1,3}$" == get_patch_version_regex("10.0.3")


def test_append_line_in_file():
    test_file = "test_append.txt"
    try:
        with open(test_file, "a") as writer:
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

        with open(test_file, "r") as reader:
            lines = reader.readlines()
            assert 11 == len(lines)
            assert lines[0] == "Test line 1\n"
            assert lines[1] == "Test line 1.5\n"
            assert lines[2] == "Test line 2\n"
            assert lines[3] == "Test line 2.5\n"
    finally:
        os.remove(test_file)


def test_prepend_line_in_file():
    test_file = "test_prepend.txt"
    try:
        with open(test_file, "a") as writer:
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

        with open(test_file, "r") as reader:
            lines = reader.readlines()
            assert 11, len(lines)
            assert lines[0] == "Test line 0.5\n"
            assert lines[1] == "Test line 1\n"
            assert lines[2] == "Test line 1.5\n"
            assert lines[3] == "Test line 2\n"
    finally:
        os.remove(test_file)


def test_getprs():
    # created at is not seen on Github. Should be checked on API result
    g = Github(GITHUB_TOKEN)
    repository = g.get_repo(f"citusdata/citus")
    prs = get_prs_for_patch_release(repository, datetime.strptime('2021.02.26', '%Y.%m.%d'), "master",
                                    datetime.strptime('2021.03.02', '%Y.%m.%d'))
    assert 1 == len(prs)
    assert 4751 == prs[0].number


def test_getprs_with_backlog_label():
    g = Github(GITHUB_TOKEN)
    repository = g.get_repo(f"citusdata/citus")
    prs = get_prs_for_patch_release(repository, datetime.strptime('2021.02.20', '%Y.%m.%d'), "master",
                                    datetime.strptime('2021.02.27', '%Y.%m.%d'))
    prs_backlog = filter_prs_by_label(prs, "backport")
    assert 1 == len(prs_backlog)
    assert 4746 == prs_backlog[0].number
