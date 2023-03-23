import os
import uuid
from datetime import datetime

import pathlib2

from ..common_tool_methods import (
    file_includes_line,
    count_line_in_file,
    run,
    get_last_commit_message,
    remove_cloned_code,
)
from ..prepare_release import (
    update_release,
    MULTI_EXTENSION_OUT,
    MULTI_EXTENSION_SQL,
    CONFIGURE,
    CONFIGURE_IN,
    CITUS_CONTROL,
    CONFIG_PY,
    ProjectParams,
)

github_token = os.getenv("GH_TOKEN")

BASE_PATH = (
    pathlib2.Path(__file__).parents[2]
    if os.getenv("BASE_PATH") is None
    else os.getenv("BASE_PATH")
)

MAIN_BRANCH = "test-tools-scripts"
TEST_CHECKOUT_DIR = "citus_test"

resources_to_be_deleted = []


def initialize_env() -> str:
    test_base_path_major = f"{BASE_PATH}/{uuid.uuid4()}"
    remove_cloned_code(test_base_path_major)
    if not os.path.exists(test_base_path_major):
        run(f"git clone https://github.com/citusdata/citus.git {test_base_path_major}")
    return test_base_path_major


def test_major_release():
    test_base_path_major = initialize_env()
    os.chdir(test_base_path_major)
    run(f"git checkout {MAIN_BRANCH}")
    resources_to_be_deleted.append(test_base_path_major)

    previous_print_extension_changes = count_line_in_file(
        test_base_path_major,
        MULTI_EXTENSION_OUT,
        "SELECT * FROM print_extension_changes();",
    )

    project_params = ProjectParams(
        project_version="10.1.0",
        project_name="citus",
        main_branch=MAIN_BRANCH,
        schema_version="",
    )
    update_release_return_value = update_release(
        github_token=github_token,
        project_params=project_params,
        earliest_pr_date=datetime.strptime("2021.03.25 00:00", "%Y.%m.%d %H:%M"),
        exec_path=test_base_path_major,
        is_test=True,
    )

    run(f"git checkout {update_release_return_value.release_branch_name}")

    assert file_includes_line(test_base_path_major, MULTI_EXTENSION_OUT, " 10.1.0")
    assert file_includes_line(
        test_base_path_major, CONFIGURE_IN, "AC_INIT([Citus], [10.1.0])"
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE, "PACKAGE_VERSION='10.1.0'"
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE, "PACKAGE_STRING='Citus 10.1.0'"
    )
    assert file_includes_line(
        test_base_path_major,
        CONFIGURE,
        r"\`configure' configures Citus 10.1.0 to adapt to many kinds of systems.",
    )
    assert file_includes_line(
        test_base_path_major,
        CONFIGURE,
        '     short | recursive ) echo "Configuration of Citus 10.1.0:";;',
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE, "PACKAGE_VERSION='10.1.0'"
    )
    assert (
        get_last_commit_message(test_base_path_major)
        == "Bump citus version to 10.1.0\n"
    )

    run(f"git checkout {update_release_return_value.upcoming_version_branch}")

    assert file_includes_line(
        test_base_path_major, CITUS_CONTROL, "default_version = '10.2-1'"
    )
    assert file_includes_line(
        test_base_path_major,
        MULTI_EXTENSION_OUT,
        "-- Test downgrade to 10.1-1 from 10.2-1",
    )
    assert file_includes_line(
        test_base_path_major,
        MULTI_EXTENSION_OUT,
        "ALTER EXTENSION citus UPDATE TO '10.1-1';",
    )
    assert (
        count_line_in_file(
            test_base_path_major,
            MULTI_EXTENSION_OUT,
            "ALTER EXTENSION citus UPDATE TO '10.2-1';",
        )
        == 2
    )
    assert file_includes_line(
        test_base_path_major,
        MULTI_EXTENSION_OUT,
        "-- Should be empty result since upgrade+downgrade should be a no-op",
    )
    assert (
        count_line_in_file(
            test_base_path_major,
            MULTI_EXTENSION_OUT,
            "SELECT * FROM print_extension_changes();",
        )
        - previous_print_extension_changes
        == 2
    )
    assert file_includes_line(
        test_base_path_major, MULTI_EXTENSION_OUT, "-- Snapshot of state at 10.2-1"
    )
    assert file_includes_line(test_base_path_major, MULTI_EXTENSION_OUT, " 10.2devel")

    assert (
        count_line_in_file(
            test_base_path_major,
            MULTI_EXTENSION_SQL,
            "ALTER EXTENSION citus UPDATE TO '10.2-1';",
        )
        == 2
    )
    assert file_includes_line(
        test_base_path_major, CONFIG_PY, "MASTER_VERSION = '10.2'"
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE_IN, "AC_INIT([Citus], [10.2devel])"
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE, "PACKAGE_VERSION='10.2devel'"
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE, "PACKAGE_STRING='Citus 10.2devel'"
    )
    assert file_includes_line(
        test_base_path_major,
        CONFIGURE,
        r"\`configure' configures Citus 10.2devel to adapt to many kinds of systems.",
    )
    assert file_includes_line(
        test_base_path_major,
        CONFIGURE,
        '     short | recursive ) echo "Configuration of Citus 10.2devel:";;',
    )
    assert file_includes_line(
        test_base_path_major, CONFIGURE, "PACKAGE_VERSION='10.2devel'"
    )
    assert os.path.exists(
        f"{test_base_path_major}/{update_release_return_value.upgrade_path_sql_file}"
    )
    assert os.path.exists(
        f"{test_base_path_major}/{update_release_return_value.downgrade_path_sql_file}"
    )
    assert (
        get_last_commit_message(test_base_path_major)
        == "Bump citus version to 10.2devel\n"
    )
    run(f"git checkout {MAIN_BRANCH}")


def test_patch_release():
    test_base_path_patch = initialize_env()
    resources_to_be_deleted.append(test_base_path_patch)
    os.chdir(test_base_path_patch)
    project_params = ProjectParams(
        project_version="10.0.4",
        project_name="citus",
        main_branch=MAIN_BRANCH,
        schema_version="10.1-5",
    )
    try:
        update_release(
            github_token=github_token,
            project_params=project_params,
            earliest_pr_date=datetime.strptime("2021.03.25 00:00", "%Y.%m.%d %H:%M"),
            exec_path=test_base_path_patch,
            is_test=True,
        )
        assert file_includes_line(
            test_base_path_patch,
            MULTI_EXTENSION_OUT,
            f" {project_params.project_version}",
        )
        assert file_includes_line(
            test_base_path_patch,
            CONFIGURE_IN,
            f"AC_INIT([Citus], [{project_params.project_version}])",
        )
        assert file_includes_line(
            test_base_path_patch,
            CONFIGURE,
            f"PACKAGE_VERSION='{project_params.project_version}'",
        )
        assert file_includes_line(
            test_base_path_patch,
            CONFIGURE,
            f"PACKAGE_STRING='Citus {project_params.project_version}'",
        )
        assert file_includes_line(
            test_base_path_patch,
            CONFIGURE,
            rf"\`configure' configures Citus {project_params.project_version} to adapt to many kinds of systems.",
        )
        assert file_includes_line(
            test_base_path_patch,
            CONFIGURE,
            f'     short | recursive ) echo "Configuration of Citus {project_params.project_version}:";;',
        )
        assert file_includes_line(
            test_base_path_patch,
            CONFIGURE,
            f"PACKAGE_VERSION='{project_params.project_version}'",
        )
        assert file_includes_line(
            test_base_path_patch,
            CITUS_CONTROL,
            f"default_version = '{project_params.schema_version}'",
        )
        run(f"git checkout {MAIN_BRANCH}")
    finally:
        for path in resources_to_be_deleted:
            remove_cloned_code(path)
