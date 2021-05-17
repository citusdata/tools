import os
from datetime import datetime
from shutil import copyfile

import pathlib2
from github import Github

from ..common_tool_methods import (get_version_number, get_version_number_with_project_name, find_nth_overlapping,
                                   find_nth_overlapping_line_by_regex, run, is_major_release, str_array_to_str,
                                   remove_string_inside_parentheses, remove_prefix,
                                   get_version_details, replace_line_in_file, get_prs, get_pr_issues_by_label)

GITHUB_TOKEN = os.getenv("GH_TOKEN")
TEST_BASE_PATH = pathlib2.Path(__file__).parent.absolute()


def test_get_version_number():
    assert get_version_number("10.0.3", True, 1) == "10.0.3-1"


def test_get_version_number_with_project_name():
    assert get_version_number_with_project_name("citus", "10.0.3", True, 1) == "10.0.3.citus-1"


def test_find_nth_overlapping():
    assert find_nth_overlapping("foofoo foofoo", "foofoo", 2) == 7


def test_find_nth_overlapping_line_by_regex():
    # Two match case
    assert find_nth_overlapping_line_by_regex("citusx\n citusx\ncitusx", "^citusx$", 2) == 2
    # No match case
    assert find_nth_overlapping_line_by_regex("citusx\n citusx\ncitusx", "^citusy$", 2) == -1


def test_is_major_release():
    assert is_major_release("10.0.0")
    assert not is_major_release("10.0.1")


def test_str_array_to_str():
    assert "1\n2\n3\n4\n" == str_array_to_str(["1", "2", "3", "4"])

    def test_run():
        result = run("echo 'Run' method is performing fine ")
        assert 0 == result.returncode


def test_remove_parentheses_from_string():
    assert "out of parentheses " == remove_string_inside_parentheses("out of parentheses (inside parentheses)")


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


def test_getprs():
    # created at is not seen on Github. Should be checked on API result
    g = Github(GITHUB_TOKEN)
    repository = g.get_repo(f"citusdata/citus")
    prs = get_prs(repository, datetime.strptime('2021.02.26', '%Y.%m.%d'), "master",
                  datetime.strptime('2021.03.02', '%Y.%m.%d'))
    assert 5 == len(prs)
    assert 4760 == prs[0].number


def test_getprs_with_backlog_label():
    g = Github(GITHUB_TOKEN)
    repository = g.get_repo(f"citusdata/citus")
    prs = get_prs(repository, datetime.strptime('2021.02.20', '%Y.%m.%d'), "master",
                  datetime.strptime('2021.02.27', '%Y.%m.%d'))
    prs_backlog = get_pr_issues_by_label(prs, "backport")
    assert 1 == len(prs_backlog)
    assert 4746 == prs_backlog[0].number


def test_remove_prefix():
    assert remove_prefix("v10.0.3", "v") == "10.0.3"

