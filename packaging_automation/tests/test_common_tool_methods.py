import os
import unittest
from shutil import copyfile

import pathlib2
from github import Github
from datetime import datetime

from ..common_tool_methods import (
    find_nth_occurrence_position, is_major_release,
    str_array_to_str, run, remove_text_with_parenthesis, get_version_details,
    replace_line_in_file, get_prs_for_patch_release, filter_prs_by_label,
    get_project_version_from_tag_name, find_nth_matching_line_and_line_number, get_minor_version,
    get_patch_version_regex)

GITHUB_TOKEN = os.getenv("GH_TOKEN")
TEST_BASE_PATH = pathlib2.Path(__file__).parent.absolute()


class CommonToolMethodsTestCases(unittest.TestCase):

    def test_find_nth_occurrence_position(self):
        self.assertEqual(find_nth_occurrence_position("foofoo foofoo", "foofoo", 2), 7)

    def test_find_nth_matching_line_number_by_regex(self):
        # Two match case
        self.assertEqual(find_nth_matching_line_and_line_number("citusx\n citusx\ncitusx", "^citusx$", 2)[0], 2)
        # No match case
        self.assertEqual(find_nth_matching_line_and_line_number("citusx\n citusx\ncitusx", "^citusy$", 2)[0], -1)

    def test_is_major_release(self):
        self.assertEqual(True, is_major_release("10.0.0"))
        self.assertEqual(False, is_major_release("10.0.1"))

    def test_get_project_version_from_tag_name(self):
        tag_name = "v10.0.3"
        self.assertEqual("10.0.3", get_project_version_from_tag_name(tag_name))

    def test_str_array_to_str(self):
        self.assertEqual("1\n2\n3\n4\n", str_array_to_str(["1", "2", "3", "4"]))

    def test_run(self):
        result = run("echo 'Run' method is performing fine ")
        self.assertEqual(0, result.returncode)

    def test_remove_parentheses_from_string(self):
        self.assertEqual("out of parentheses ",
                         remove_text_with_parenthesis("out of parentheses (inside parentheses)"))

    def test_get_version_details(self):
        self.assertEqual({"major": "10", "minor": "0", "patch": "1"}, get_version_details("10.0.1"))

    def test_replace_line_in_file(self):
        replace_str = "Summary:     Replace Test"
        copy_file_path = f"{TEST_BASE_PATH}/files/citus_copy.spec"
        copyfile(f"{TEST_BASE_PATH}/files/citus.spec", copy_file_path)
        replace_line_in_file(copy_file_path, r"^Summary:	*", replace_str)
        try:
            with open(copy_file_path, "r") as reader:
                content = reader.read()
                lines = content.splitlines()
                self.assertEqual(lines[5], replace_str)
        finally:
            os.remove(copy_file_path)

    def test_getprs(self):
        # created at is not seen on Github. Should be checked on API result
        g = Github(GITHUB_TOKEN)
        repository = g.get_repo(f"citusdata/citus")
        prs = get_prs_for_patch_release(repository, datetime.strptime('2021.02.26', '%Y.%m.%d'), "master",
                                        datetime.strptime('2021.03.02', '%Y.%m.%d'))
        self.assertEqual(1, len(prs))
        self.assertEqual(4751, prs[0].number)

    def test_getprs_with_backlog_label(self):
        g = Github(GITHUB_TOKEN)
        repository = g.get_repo(f"citusdata/citus")
        prs = get_prs_for_patch_release(repository, datetime.strptime('2021.02.20', '%Y.%m.%d'), "master",
                                        datetime.strptime('2021.02.27', '%Y.%m.%d'))
        prs_backlog = filter_prs_by_label(prs, "backport")
        self.assertEqual(1, len(prs_backlog))
        self.assertEqual(4746, prs_backlog[0].number)

    def test_get_minor_version(self):
        self.assertEqual("10.0", get_minor_version("10.0.3"))

    def test_get_patch_version_regex(self):
        self.assertEqual("10\.0\.\d{1,3}", get_patch_version_regex("10.0.3"))


if __name__ == '__main__':
    unittest.main()
