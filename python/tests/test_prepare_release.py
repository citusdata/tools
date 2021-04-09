import unittest

import pathlib2

from ..prepare_release import *

github_token = os.getenv("GH_TOKEN")

BASE_PATH = pathlib2.Path(__file__).parents[2] if os.getenv("BASE_PATH") is None else os.getenv("BASE_PATH")
TEST_BASE_PATH = f"{BASE_PATH}/citus"
CITUS_PROJECT_TEST_PATH = f"{TEST_BASE_PATH}/projects/citus"
CITUS_PROJECT_TEST_PATH_COPY = f"{TEST_BASE_PATH}/projects/citus_copy"


class PrepareReleaseTestCases(unittest.TestCase):
    def setUp(self):
        if os.path.exists("citus"):
            run("rm -r citus")
        self.initialize_env()

    def initialize_env(self):
        print("Current Directory:"+os.getcwd())
        if not os.path.exists("citus"):
            run("git clone https://github.com/citusdata/citus.git")

    def test_major_release(self):
        self.initialize_env()
        os.chdir("citus")
        release_branch, upcoming_version_branch, newly_created_sql_file, resource_status = update_release(
            github_token=github_token,
            project_name="citus",
            project_version="10.2.0",
            main_branch="master",
            earliest_pr_date=datetime.strptime(
                '2021.03.25 00:00',
                '%Y.%m.%d %H:%M'),
            exec_path=TEST_BASE_PATH,
            is_test=True)
        # run(f"git checkout {release_branch}")

        # newly_created_sql_file = f"{DISTRIBUTED_DIR_PATH}/citus--10.1-1--10.2-1.sql"

        run(f"git checkout {release_branch}")

        self.assertTrue(has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2.0"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2.0])"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.0'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2.0'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                              "\`configure' configures Citus 10.2.0 to adapt to many kinds of systems."))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                              '     short | recursive ) echo "Configuration of Citus 10.2.0:";;'))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.0'"))

        run(f"git checkout {upcoming_version_branch}")

        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CITUS_CONTROL, "default_version = '10.2-1'"))
        self.assertTrue(
            has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, "ALTER EXTENSION citus UPDATE TO '10.2-1';"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2devel"))
        self.assertEqual(2, line_count_in_file(TEST_BASE_PATH, MULTI_EXTENSION_SQL,
                                               "ALTER EXTENSION citus UPDATE TO '10.2-1';"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIG_PY, "MASTER_VERSION = '10.2'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2devel])"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2devel'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2devel'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                              "\`configure' configures Citus 10.2devel to adapt to many kinds of systems."))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                              '     short | recursive ) echo "Configuration of Citus 10.2devel:";;'))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2devel'"))
        self.assertTrue(os.path.exists(f"{TEST_BASE_PATH}/{newly_created_sql_file}"))
        #

        if resource_status in (ResourceStatus.RELEASE_BRANCH_LOCAL, ResourceStatus.RELEASE_BRANCH_REMOTE,
                               ResourceStatus.UPCOMING_VERSION_LOCAL, ResourceStatus.UPCOMING_VERSION_REMOTE,
                               ResourceStatus.PULL_REQUEST_CREATED):
            run(f"git branch -D {release_branch} ")
        elif resource_status in (ResourceStatus.RELEASE_BRANCH_REMOTE,
                                 ResourceStatus.UPCOMING_VERSION_LOCAL, ResourceStatus.UPCOMING_VERSION_REMOTE,
                                 ResourceStatus.PULL_REQUEST_CREATED):
            run(f"git push origin --delete {release_branch}")
        elif resource_status in (ResourceStatus.UPCOMING_VERSION_LOCAL, ResourceStatus.UPCOMING_VERSION_REMOTE,
                                 ResourceStatus.PULL_REQUEST_CREATED):
            run(f"git branch -D {upcoming_version_branch} ")
        elif resource_status in (ResourceStatus.UPCOMING_VERSION_REMOTE,
                                 ResourceStatus.PULL_REQUEST_CREATED):
            run(f"git push origin --delete {release_branch}")
        self.clear_env()

    def test_patch_release(self):
        self.initialize_env()
        print(os.getcwd())
        os.chdir("citus")

        update_release(github_token=github_token, project_name="citus", project_version="10.2.0",
                       main_branch="master",
                       earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
                       exec_path=TEST_BASE_PATH, is_test=True)

        update_release(github_token=github_token, project_name="citus", project_version="10.2.1",
                       main_branch="master",
                       earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
                       exec_path=TEST_BASE_PATH, is_test=True)
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2.1"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2.1])"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.1'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2.1'"))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                              "\`configure' configures Citus 10.2.1 to adapt to many kinds of systems."))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                              '     short | recursive ) echo "Configuration of Citus 10.2.1:";;'))
        self.assertTrue(has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.1'"))

        self.clear_env()

    # def tearDown(self):
    #     self.clear_env()

    def clear_env(self):

        if os.path.exists("../citus"):
            os.chdir("..")
            run("chmod -R 777 citus")
            run("sudo rm -rf citus")
