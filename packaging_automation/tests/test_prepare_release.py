import pathlib2
import os
from datetime import datetime

from ..prepare_release import (update_release, MULTI_EXTENSION_OUT, MULTI_EXTENSION_SQL, CONFIGURE,
                               CONFIGURE_IN, CITUS_CONTROL, CONFIG_PY)
from ..common_tool_methods import file_includes_line, count_line_in_file, run

github_token = os.getenv("GH_TOKEN")

BASE_PATH = pathlib2.Path(__file__).parents[2] if os.getenv("BASE_PATH") is None else os.getenv("BASE_PATH")

MAIN_BRANCH = "test-tools-scripts"
TEST_CHECKOUT_DIR = "citus_test"
TEST_BASE_PATH = f"{BASE_PATH}/{TEST_CHECKOUT_DIR}"


def initialize_env():
    clear_env()
    if not os.path.exists(TEST_CHECKOUT_DIR):
        run(f"git clone https://github.com/citusdata/citus.git {TEST_CHECKOUT_DIR}")


def test_major_release():
    initialize_env()
    os.chdir(TEST_CHECKOUT_DIR)
    try:
        update_release_return_value = update_release(
            github_token=github_token, project_name="citus", project_version="10.2.0", main_branch=MAIN_BRANCH,
            earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
            exec_path=TEST_BASE_PATH, is_test=True)

        run(f"git checkout {update_release_return_value.release_branch_name}")

        assert file_includes_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2.0")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2.0])")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.0'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2.0'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE,
                                  r"\`configure' configures Citus 10.2.0 to adapt to many kinds of systems.")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE,
                                  '     short | recursive ) echo "Configuration of Citus 10.2.0:";;')
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.0'")

        run(f"git checkout {update_release_return_value.upcoming_version_branch}")

        assert file_includes_line(TEST_BASE_PATH, CITUS_CONTROL, "default_version = '10.2-1'")
        assert file_includes_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT,
                                  "ALTER EXTENSION citus UPDATE TO '10.1-1';")
        assert file_includes_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT,
                                  "ALTER EXTENSION citus UPDATE TO '10.2-1';")
        assert file_includes_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2devel")
        assert file_includes_line(TEST_BASE_PATH, MULTI_EXTENSION_SQL,
                                  "ALTER EXTENSION citus UPDATE TO '10.2-1';")
        assert count_line_in_file(TEST_BASE_PATH, MULTI_EXTENSION_SQL,
                                  "ALTER EXTENSION citus UPDATE TO '10.2-1';") == 2
        assert file_includes_line(TEST_BASE_PATH, CONFIG_PY, "MASTER_VERSION = '10.2'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2devel])")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2devel'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2devel'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE,
                                  r"\`configure' configures Citus 10.2devel to adapt to many kinds of systems.")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE,
                                  '     short | recursive ) echo "Configuration of Citus 10.2devel:";;')
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2devel'")
        assert os.path.exists(f"{TEST_BASE_PATH}/{update_release_return_value.upgrade_path_sql_file}")
        run(f"git checkout {MAIN_BRANCH}")
    finally:
        clear_env()


def test_patch_release():
    initialize_env()
    os.chdir(TEST_CHECKOUT_DIR)
    try:
        update_release(github_token=github_token, project_name="citus", project_version="10.2.0",
                       main_branch=MAIN_BRANCH,
                       earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
                       exec_path=TEST_BASE_PATH, is_test=True)

        update_release(
            github_token=github_token, project_name="citus", project_version="10.2.1",
            main_branch=MAIN_BRANCH,
            earliest_pr_date=datetime.strptime('2021.03.25 00:00', '%Y.%m.%d %H:%M'),
            exec_path=TEST_BASE_PATH, is_test=True)
        assert file_includes_line(TEST_BASE_PATH, MULTI_EXTENSION_OUT, " 10.2.1")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE_IN, "AC_INIT([Citus], [10.2.1])")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.1'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_STRING='Citus 10.2.1'")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE,
                                  r"\`configure' configures Citus 10.2.1 to adapt to many kinds of systems.")
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE,
                                  '     short | recursive ) echo "Configuration of Citus 10.2.1:";;')
        assert file_includes_line(TEST_BASE_PATH, CONFIGURE, "PACKAGE_VERSION='10.2.1'")
        run(f"git checkout {MAIN_BRANCH}")

    finally:
        clear_env()


def clear_env():
    if os.path.exists(f"../{TEST_CHECKOUT_DIR}"):
        run(f"sudo rm -rf ../{TEST_CHECKOUT_DIR}")
