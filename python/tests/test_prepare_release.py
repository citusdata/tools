import shutil
import unittest

import pathlib2

from ..prepare_release import *

github_token = os.getenv("GH_TOKEN")

TEST_BASE_PATH = pathlib2.Path(__file__).parent.absolute()
CITUS_PROJECT_TEST_PATH = f"{TEST_BASE_PATH}/projects/citus"
CITUS_PROJECT_TEST_PATH_COPY = f"{TEST_BASE_PATH}/projects/citus_copy"


class PrepareReleaseTestCases(unittest.TestCase):
    def test_major_release(self):
        shutil.copytree(CITUS_PROJECT_TEST_PATH, CITUS_PROJECT_TEST_PATH_COPY)
        try:
            update_release(github_token=github_token, project_name="citus", project_version="10.1.0",
                           main_branch="master",
                           earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
                           exec_path=CITUS_PROJECT_TEST_PATH_COPY)
        # current branch is release-$version number
        # check for configure in
        # check for
        finally:
            # shutil.rmtree(CITUS_PROJECT_TEST_PATH_COPY)
            run(f"rm -r {CITUS_PROJECT_TEST_PATH_COPY}")
