import shutil
import unittest
import os

import pathlib2

from ..prepare_release import *
from ..common_tool_methods import *

github_token = os.getenv("GH_TOKEN")

BASE_PATH = pathlib2.Path(__file__).parents[2] if os.getenv("BASE_PATH") is None else os.getenv("BASE_PATH")
TEST_BASE_PATH = f"{BASE_PATH}/citus"
CITUS_PROJECT_TEST_PATH = f"{TEST_BASE_PATH}/projects/citus"
CITUS_PROJECT_TEST_PATH_COPY = f"{TEST_BASE_PATH}/projects/citus_copy"


class PrepareReleaseTestCases(unittest.TestCase):
    def test_major_release(self):
        # shutil.copytree(CITUS_PROJECT_TEST_PATH, CITUS_PROJECT_TEST_PATH_COPY)
        if not os.path.exists("citus"):
            run("git clone https://github.com/citusdata/citus.git")
        os.chdir("citus")
        # try:
        update_release(github_token=github_token, project_name="citus", project_version="10.2.0",
                       main_branch="master",
                       earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
                       exec_path=TEST_BASE_PATH)

    # current branch is release-$version number
    # check for configure in
    # check for
    # finally:
    #     # shutil.rmtree(CITUS_PROJECT_TEST_PATH_COPY)
    #     run(f"rm -r {CITUS_PROJECT_TEST_PATH_COPY}")
