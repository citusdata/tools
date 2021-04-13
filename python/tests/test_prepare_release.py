import pathlib2

from ..prepare_release import *

github_token = os.getenv("GH_TOKEN")

BASE_PATH = pathlib2.Path(__file__).parents[2] if os.getenv("BASE_PATH") is None else os.getenv("BASE_PATH")
TEST_BASE_PATH = f"{BASE_PATH}/citus"
CITUS_PROJECT_TEST_PATH = f"{TEST_BASE_PATH}/projects/citus"
CITUS_PROJECT_TEST_PATH_COPY = f"{TEST_BASE_PATH}/projects/citus_copy"
MAIN_BRANCH = "test-tools-scripts"


def initialize_env():
    if not os.path.exists("citus"):
        run("git clone https://github.com/citusdata/citus.git")


def test_major_release():
    initialize_env()
    os.chdir("citus")

    release_branch, upcoming_version_branch, newly_created_sql_file, resource_status = update_release(
        github_token=github_token,
        project_name="citus",
        project_version="10.2.0",
        main_branch=MAIN_BRANCH,
        earliest_pr_date=datetime.strptime(
            '2021.03.25 00:00',
            '%Y.%m.%d %H:%M'),
        exec_path=TEST_BASE_PATH,
        is_test=True)

    run(f"git checkout {release_branch}")

    assert has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2.0")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2.0])")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.0'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2.0'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                 r"\`configure' configures Citus 10.2.0 to adapt to many kinds of systems.")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                 '     short | recursive ) echo "Configuration of Citus 10.2.0:";;')
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.0'")

    run(f"git checkout {upcoming_version_branch}")

    assert has_file_include_line(TEST_BASE_PATH, CITUS_CONTROL, "default_version = '10.2-1'")
    assert has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT,
                                 "ALTER EXTENSION citus UPDATE TO '10.2-1';")
    assert has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2devel")
    assert line_count_in_file(TEST_BASE_PATH, MULTI_EXTENSION_SQL,
                              "ALTER EXTENSION citus UPDATE TO '10.2-1';") == 2
    assert has_file_include_line(TEST_BASE_PATH, CONFIG_PY, "MASTER_VERSION = '10.2'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2devel])")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2devel'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2devel'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                 r"\`configure' configures Citus 10.2devel to adapt to many kinds of systems.")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                 '     short | recursive ) echo "Configuration of Citus 10.2devel:";;')
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2devel'")
    assert os.path.exists(f"{TEST_BASE_PATH}/{newly_created_sql_file}")
    #
    run(f"git checkout {MAIN_BRANCH}")
    clear_branches(release_branch, resource_status, upcoming_version_branch)
    clear_env()


def clear_branches(release_branch, resource_status, upcoming_version_branch):
    if resource_status in (ResourceStatus.RELEASE_BRANCH_LOCAL, ResourceStatus.RELEASE_BRANCH_REMOTE,
                           ResourceStatus.UPCOMING_VERSION_LOCAL, ResourceStatus.UPCOMING_VERSION_REMOTE,
                           ResourceStatus.PULL_REQUEST_CREATED):
        run(f"git branch -D {release_branch} ")

    if resource_status in (ResourceStatus.UPCOMING_VERSION_LOCAL, ResourceStatus.UPCOMING_VERSION_REMOTE,
                           ResourceStatus.PULL_REQUEST_CREATED):
        run(f"git branch -D {upcoming_version_branch} ")


def test_patch_release():
    initialize_env()
    os.chdir("citus")

    update_release(github_token=github_token, project_name="citus", project_version="10.2.0",
                   main_branch=MAIN_BRANCH,
                   earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
                   exec_path=TEST_BASE_PATH, is_test=True)

    release_branch, upcoming_version_branch, newly_created_sql_file, resource_status = update_release(
        github_token=github_token, project_name="citus", project_version="10.2.1",
        main_branch=MAIN_BRANCH,
        earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
        exec_path=TEST_BASE_PATH, is_test=True)
    assert has_file_include_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2.1")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2.1])")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.1'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2.1'")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                 r"\`configure' configures Citus 10.2.1 to adapt to many kinds of systems.")
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE,
                                 '     short | recursive ) echo "Configuration of Citus 10.2.1:";;')
    assert has_file_include_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.1'")
    run(f"git checkout {MAIN_BRANCH}")

    clear_branches(release_branch, resource_status, upcoming_version_branch)

    clear_env()

    # def tearDown(self):
    #     self.clear_env()


def clear_env():
    if os.path.exists("../citus"):
        os.chdir("..")
        run("chmod -R 777 citus")
        run("sudo rm -rf citus")
