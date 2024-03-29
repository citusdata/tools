import argparse
import os
import uuid
from dataclasses import dataclass
from datetime import datetime

import pathlib2
from github import Github, Repository
from parameters_validation import non_blank, non_empty
from typing import Dict

from .common_tool_methods import (
    get_version_details,
    is_major_release,
    get_prs_for_patch_release,
    filter_prs_by_label,
    cherry_pick_prs,
    run,
    replace_line_in_file,
    get_current_branch,
    find_nth_matching_line_and_line_number,
    get_patch_version_regex,
    remote_branch_exists,
    local_branch_exists,
    prepend_line_in_file,
    get_template_environment,
    get_upcoming_minor_version,
    remove_cloned_code,
    initialize_env,
    create_pr_with_repo,
    DEFAULT_ENCODING_FOR_FILE_HANDLING,
    DEFAULT_UNICODE_ERROR_HANDLER,
)
from .common_validations import CITUS_MINOR_VERSION_PATTERN, CITUS_PATCH_VERSION_PATTERN

MULTI_EXTENSION_SQL = "src/test/regress/sql/multi_extension.sql"
CITUS_CONTROL = "src/backend/distributed/citus.control"
MULTI_EXTENSION_OUT = "src/test/regress/expected/multi_extension.out"
CONFIG_PY = "src/test/regress/upgrade/config.py"
DISTRIBUTED_SQL_DIR_PATH = "src/backend/distributed/sql"
DOWNGRADES_DIR_PATH = f"{DISTRIBUTED_SQL_DIR_PATH}/downgrades"
CONFIGURE_IN = "configure.in"
CONFIGURE = "configure"
CITUS_CONTROL_SEARCH_PATTERN = r"^default_version*"

MULTI_EXT_DEVEL_SEARCH_PATTERN = rf"^\s*{CITUS_MINOR_VERSION_PATTERN}devel$"
MULTI_EXT_PATCH_SEARCH_PATTERN = rf"^\s*{CITUS_PATCH_VERSION_PATTERN}$"

MULTI_EXT_DETAIL_PREFIX = r"DETAIL:  Loaded library requires "
MULTI_EXT_DETAIL1_SUFFIX = r", but 8.0-1 was specified."
MULTI_EXT_DETAIL2_SUFFIX = r", but the installed extension version is 8.1-1."
MULTI_EXT_DETAIL1_PATTERN = (
    rf"^{MULTI_EXT_DETAIL_PREFIX}\d+\.\d+{MULTI_EXT_DETAIL1_SUFFIX}$"
)

MULTI_EXT_DETAIL2_PATTERN = (
    rf"^{MULTI_EXT_DETAIL_PREFIX}\d+\.\d+{MULTI_EXT_DETAIL2_SUFFIX}$"
)

CONFIG_PY_MASTER_VERSION_SEARCH_PATTERN = r"^MASTER_VERSION = '\d+\.\d+'"

CONFIGURE_IN_SEARCH_PATTERN = "AC_INIT*"
REPO_OWNER = "citusdata"

BASE_PATH = pathlib2.Path(__file__).parent.absolute()
TEMPLATES_PATH = f"{BASE_PATH}/templates"

MULTI_EXT_OUT_TEMPLATE_FILE = "multi_extension_out_prepare_release.tmpl"
MULTI_EXT_SQL_TEMPLATE_FILE = "multi_extension_sql_prepare_release.tmpl"

repo_details = {
    "citus": {"configure-in-str": "Citus", "branch": "master"},
    "citus-enterprise": {
        "configure-in-str": "Citus Enterprise",
        "branch": "enterprise-master",
    },
}


@dataclass
class UpdateReleaseReturnValue:
    release_branch_name: str
    upcoming_version_branch: str
    upgrade_path_sql_file: str
    downgrade_path_sql_file: str


@dataclass
class MajorReleaseParams:
    configure_in_path: str
    devel_version: str
    is_test: bool
    main_branch: str
    multi_extension_out_path: str
    project_name: str
    project_version: str
    release_branch_name: str


@dataclass
class UpcomingVersionBranchParams:
    citus_control_file_path: str
    config_py_path: str
    configure_in_path: str
    upcoming_devel_version: str
    distributed_dir_path: str
    downgrades_dir_path: str
    is_test: bool
    main_branch: str
    multi_extension_out_path: str
    multi_extension_sql_path: str
    project_name: str
    project_version: str
    repository: Repository
    upcoming_minor_version: str
    upcoming_version_branch: str


@dataclass
class PatchReleaseParams:
    cherry_pick_enabled: bool
    configure_in_path: str
    earliest_pr_date_value: datetime
    is_test: bool
    main_branch: str
    citus_control_file_path: str
    multi_extension_out_path: str
    project_name: str
    project_version: str
    release_branch_name: str
    schema_version: str
    repository: Repository


@dataclass
class ProjectParams:
    project_name: str
    project_version: str
    main_branch: str
    schema_version: str


@dataclass
class PathParams:
    multi_extension_sql_path: str
    citus_control_file_path: str
    multi_extension_out_path: str
    configure_in_path: str
    config_py_path: str
    distributed_dir_path: str
    downgrades_dir_path: str


@dataclass
class BranchParams:
    release_branch_name: str
    upcoming_version_branch: str


@dataclass
class VersionParams:
    project_version_details: Dict[str, str]
    upcoming_minor_version: str
    upcoming_devel_version: str


BASE_GIT_PATH = pathlib2.Path(__file__).parents[1]


@dataclass
class MigrationFiles:
    upgrade_file: str
    downgrade_file: str


# disabled since this is related to parameter_validations library methods
# pylint: disable=no-value-for-parameter
def update_release(
    github_token: non_blank(non_empty(str)),
    project_params: ProjectParams,
    earliest_pr_date: datetime,
    exec_path: non_blank(non_empty(str)),
    is_test: bool = False,
    cherry_pick_enabled: bool = False,
) -> UpdateReleaseReturnValue:
    path_params = PathParams(
        multi_extension_out_path=f"{exec_path}/{MULTI_EXTENSION_OUT}",
        multi_extension_sql_path=f"{exec_path}/{MULTI_EXTENSION_SQL}",
        citus_control_file_path=f"{exec_path}/{CITUS_CONTROL}",
        configure_in_path=f"{exec_path}/{CONFIGURE_IN}",
        config_py_path=f"{exec_path}/{CONFIG_PY}",
        distributed_dir_path=f"{exec_path}/{DISTRIBUTED_SQL_DIR_PATH}",
        downgrades_dir_path=f"{exec_path}/{DOWNGRADES_DIR_PATH}",
    )

    version_params = VersionParams(
        project_version_details=get_version_details(project_params.project_version),
        upcoming_minor_version=get_upcoming_minor_version(
            project_params.project_version
        ),
        upcoming_devel_version=f"{get_upcoming_minor_version(project_params.project_version)}devel",
    )

    branch_params = BranchParams(
        release_branch_name=get_release_branch_name(
            is_test, version_params.project_version_details
        ),
        upcoming_version_branch=f"master-update-version-{uuid.uuid4()}",
    )

    repository = get_github_repository(github_token, project_params)

    upcoming_version_branch = ""

    migration_files = MigrationFiles("", "")
    # major release
    if is_major_release(project_params.project_version):
        print(
            f"### {project_params.project_version} is a major release. Executing Major release flow... ###"
        )
        major_release_params = MajorReleaseParams(
            configure_in_path=path_params.configure_in_path,
            devel_version=version_params.upcoming_devel_version,
            is_test=is_test,
            main_branch=project_params.main_branch,
            multi_extension_out_path=path_params.multi_extension_out_path,
            project_name=project_params.project_name,
            project_version=project_params.project_version,
            release_branch_name=branch_params.release_branch_name,
        )
        prepare_release_branch_for_major_release(major_release_params)
        upcoming_version_branch_params = UpcomingVersionBranchParams(
            project_version=project_params.project_version,
            project_name=project_params.project_name,
            upcoming_version_branch=branch_params.upcoming_version_branch,
            upcoming_devel_version=version_params.upcoming_devel_version,
            is_test=is_test,
            main_branch=project_params.main_branch,
            citus_control_file_path=path_params.citus_control_file_path,
            config_py_path=path_params.config_py_path,
            configure_in_path=path_params.configure_in_path,
            distributed_dir_path=path_params.distributed_dir_path,
            downgrades_dir_path=path_params.downgrades_dir_path,
            repository=repository,
            upcoming_minor_version=version_params.upcoming_minor_version,
            multi_extension_out_path=path_params.multi_extension_out_path,
            multi_extension_sql_path=path_params.multi_extension_sql_path,
        )
        upcoming_version_branch = upcoming_version_branch_params.upcoming_version_branch

        migration_files = prepare_upcoming_version_branch(
            upcoming_version_branch_params
        )
        print(
            f"### Done {project_params.project_version} Major release flow executed successfully. ###"
        )
    # patch release
    else:
        patch_release_params = PatchReleaseParams(
            cherry_pick_enabled=cherry_pick_enabled,
            configure_in_path=path_params.configure_in_path,
            earliest_pr_date_value=earliest_pr_date,
            is_test=is_test,
            main_branch=project_params.main_branch,
            multi_extension_out_path=path_params.multi_extension_out_path,
            project_name=project_params.project_name,
            project_version=project_params.project_version,
            schema_version=project_params.schema_version,
            citus_control_file_path=path_params.citus_control_file_path,
            release_branch_name=branch_params.release_branch_name,
            repository=repository,
        )
        prepare_release_branch_for_patch_release(patch_release_params)
    return UpdateReleaseReturnValue(
        release_branch_name=branch_params.release_branch_name,
        upcoming_version_branch=upcoming_version_branch,
        upgrade_path_sql_file=f"{DISTRIBUTED_SQL_DIR_PATH}/{migration_files.upgrade_file}",
        downgrade_path_sql_file=f"{DOWNGRADES_DIR_PATH}/{migration_files.downgrade_file}",
    )


def get_github_repository(github_token, project_params):
    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{project_params.project_name}")
    return repository


def get_release_branch_name(is_test, project_version_details):
    release_branch_name = (
        f'release-{project_version_details["major"]}.{project_version_details["minor"]}'
    )
    release_branch_name = (
        f"{release_branch_name}-test" if is_test else release_branch_name
    )
    return release_branch_name


def prepare_release_branch_for_patch_release(patchReleaseParams: PatchReleaseParams):
    print(
        f"### {patchReleaseParams.project_version} is a patch release. Executing Patch release flow... ###"
    )
    # checkout release branch (release-X.Y) In test case release branch for test may not be exist.
    # In this case create one
    if patchReleaseParams.is_test:
        non_test_release_branch = patchReleaseParams.release_branch_name.rstrip("-test")
        release_branch_exist = remote_branch_exists(
            non_test_release_branch, os.getcwd()
        )
        test_release_branch_exist = local_branch_exists(
            patchReleaseParams.release_branch_name, os.getcwd()
        )

        if release_branch_exist:
            run(f"git checkout {non_test_release_branch}")
            run(f"git checkout -b {patchReleaseParams.release_branch_name}")
        elif test_release_branch_exist:
            run(f"git checkout  {patchReleaseParams.release_branch_name}")
        else:
            run(f"git checkout -b  {patchReleaseParams.release_branch_name}")
    else:
        checkout_branch(
            patchReleaseParams.release_branch_name, patchReleaseParams.is_test
        )
    # change version info in configure.in file
    update_version_in_configure_in(
        patchReleaseParams.project_name,
        patchReleaseParams.configure_in_path,
        patchReleaseParams.project_version,
    )
    # execute "auto-conf "
    execute_autoconf_f()
    # change version info in multi_extension.out
    update_version_in_multi_extension_out_for_patch(
        patchReleaseParams.multi_extension_out_path, patchReleaseParams.project_version
    )
    # if schema version is not empty update citus.control schema version
    if patchReleaseParams.schema_version:
        update_schema_version_in_citus_control(
            citus_control_file_path=patchReleaseParams.citus_control_file_path,
            schema_version=patchReleaseParams.schema_version,
        )
    if patchReleaseParams.cherry_pick_enabled:
        # cherry-pick the pr's with backport labels
        cherrypick_prs_with_backport_labels(
            patchReleaseParams.earliest_pr_date_value,
            patchReleaseParams.main_branch,
            patchReleaseParams.release_branch_name,
            patchReleaseParams.repository,
        )
    # commit all changes
    commit_changes_for_version_bump(
        patchReleaseParams.project_name, patchReleaseParams.project_version
    )
    # create and push release-$minor_version-push-$curTime branch
    release_pr_branch = f"{patchReleaseParams.release_branch_name}_{uuid.uuid4()}"
    create_and_checkout_branch(release_pr_branch)
    if not patchReleaseParams.is_test:
        push_branch(release_pr_branch)

    print("### Done Patch release flow executed successfully. ###")


def prepare_upcoming_version_branch(upcoming_params: UpcomingVersionBranchParams):
    print(
        f"### {upcoming_params.upcoming_version_branch} flow is being executed... ###"
    )
    # checkout master
    checkout_branch(upcoming_params.main_branch, upcoming_params.is_test)
    # create master-update-version-$curtime branch
    create_and_checkout_branch(upcoming_params.upcoming_version_branch)
    # update version info with upcoming version on configure.in
    update_version_in_configure_in(
        upcoming_params.project_name,
        upcoming_params.configure_in_path,
        upcoming_params.upcoming_devel_version,
    )
    # update version info with upcoming version on config.py
    update_version_with_upcoming_version_in_config_py(
        upcoming_params.config_py_path, upcoming_params.upcoming_minor_version
    )
    # execute autoconf -f
    execute_autoconf_f()
    # update version info with upcoming version on multi_extension.out
    update_version_in_multi_extension_out(
        upcoming_params.multi_extension_out_path, upcoming_params.upcoming_devel_version
    )
    # update detail lines with minor version
    update_detail_strings_in_multi_extension_out(
        upcoming_params.multi_extension_out_path, upcoming_params.upcoming_minor_version
    )
    # get current schema version from citus.control
    current_schema_version = get_current_schema_from_citus_control(
        upcoming_params.citus_control_file_path
    )
    # add downgrade script in multi_extension.sql file
    add_downgrade_script_in_multi_extension_file(
        current_schema_version,
        upcoming_params.multi_extension_sql_path,
        upcoming_params.upcoming_minor_version,
        MULTI_EXT_SQL_TEMPLATE_FILE,
    )
    # add downgrade script in multi_extension.out file
    add_downgrade_script_in_multi_extension_file(
        current_schema_version,
        upcoming_params.multi_extension_out_path,
        upcoming_params.upcoming_minor_version,
        MULTI_EXT_OUT_TEMPLATE_FILE,
    )
    # create a new sql file for upgrade path:
    upgrade_file = create_new_sql_for_upgrade_path(
        current_schema_version,
        upcoming_params.distributed_dir_path,
        upcoming_params.upcoming_minor_version,
    )
    # create a new sql file for downgrade path:
    downgrade_file = create_new_sql_for_downgrade_path(
        current_schema_version,
        upcoming_params.downgrades_dir_path,
        upcoming_params.upcoming_minor_version,
    )

    # change version in citus.control file
    default_upcoming_schema_version = f"{upcoming_params.upcoming_minor_version}-1"
    update_schema_version_in_citus_control(
        upcoming_params.citus_control_file_path, default_upcoming_schema_version
    )
    # commit and push changes on master-update-version-$curtime branch
    commit_changes_for_version_bump(
        upcoming_params.project_name, upcoming_params.upcoming_devel_version
    )
    if not upcoming_params.is_test:
        push_branch(upcoming_params.upcoming_version_branch)

        # create pull request
        create_pull_request_for_upcoming_version_branch(
            upcoming_params.repository,
            upcoming_params.main_branch,
            upcoming_params.upcoming_version_branch,
            upcoming_params.upcoming_devel_version,
        )
    print(f"### Done {upcoming_params.upcoming_version_branch} flow executed. ###")
    return MigrationFiles(upgrade_file=upgrade_file, downgrade_file=downgrade_file)


def prepare_release_branch_for_major_release(majorReleaseParams: MajorReleaseParams):
    print(
        f"###  {majorReleaseParams.release_branch_name} release branch flow is being executed... ###"
    )
    # checkout master
    checkout_branch(majorReleaseParams.main_branch, majorReleaseParams.is_test)
    # create release branch in release-X.Y format
    create_and_checkout_branch(majorReleaseParams.release_branch_name)
    # change version info in configure.in file
    update_version_in_configure_in(
        majorReleaseParams.project_name,
        majorReleaseParams.configure_in_path,
        majorReleaseParams.project_version,
    )
    # execute "autoconf -f"
    execute_autoconf_f()
    # change version info in multi_extension.out
    update_version_in_multi_extension_out(
        majorReleaseParams.multi_extension_out_path, majorReleaseParams.project_version
    )
    # commit all changes
    commit_changes_for_version_bump(
        majorReleaseParams.project_name, majorReleaseParams.project_version
    )
    # push release branch (No PR creation!!!)
    if not majorReleaseParams.is_test:
        push_branch(majorReleaseParams.release_branch_name)
    print(
        f"### Done {majorReleaseParams.release_branch_name} release branch flow executed .###"
    )


def cherrypick_prs_with_backport_labels(
    earliest_pr_date, main_branch, release_branch_name, repository
):
    print(
        f"### Getting all PR with backport label after {datetime.strftime(earliest_pr_date, '%Y.%m.%d %H:%M')}... ### "
    )
    prs_with_earliest_date = get_prs_for_patch_release(
        repository, earliest_pr_date, main_branch
    )
    # get commits for selected prs with backport label
    prs_with_backport = filter_prs_by_label(prs_with_earliest_date, "backport")
    print(
        f"### Done {len(prs_with_backport)} PRs with backport label found. PR list is as below. ###"
    )
    for pr in prs_with_backport:
        print(f"\tNo:{pr.number} Title:{pr.title}")
    # cherrypick all commits with backport label
    print(f"### Cherry-picking PRs to {release_branch_name}... ###")
    cherry_pick_prs(prs_with_backport)
    print(
        f"### Done Cherry pick completed for all PRs on branch {release_branch_name}. ###"
    )


def create_pull_request_for_upcoming_version_branch(
    repository, main_branch, upcoming_version_branch, upcoming_version
):
    print(f"### Creating pull request for {upcoming_version_branch}... ###")
    pr_result = create_pr_with_repo(
        repo=repository,
        pr_branch=upcoming_version_branch,
        pr_title=f"Bump Citus to {upcoming_version}",
        base_branch=main_branch,
    )
    print(
        f"### Done Pull request created. PR no:{pr_result.number} PR URL: {pr_result.url}. ###  "
    )


def push_branch(upcoming_version_branch):
    print(f"Pushing changes for {upcoming_version_branch} into remote origin... ###")
    run(f"git push --set-upstream origin {upcoming_version_branch}")
    print(f"### Done Changes pushed for {upcoming_version_branch}. ###")


def commit_changes_for_version_bump(project_name, project_version):
    current_branch = get_current_branch(os.getcwd())
    print(f"### Committing changes for branch {current_branch}... ###")
    run("git add .")
    run(f' git commit  -m "Bump {project_name} version to {project_version} "')
    print(f"### Done Changes committed for {current_branch}. ###")


def update_schema_version_in_citus_control(citus_control_file_path, schema_version):
    print(
        f"### Updating {citus_control_file_path} file with the  version {schema_version}... ###"
    )
    if not replace_line_in_file(
        citus_control_file_path,
        CITUS_CONTROL_SEARCH_PATTERN,
        f"default_version = '{schema_version}'",
    ):
        raise ValueError(f"{citus_control_file_path} does not have match for version")
    print(
        f"### Done {citus_control_file_path} file is updated with the schema version {schema_version}. ###"
    )


def add_downgrade_script_in_multi_extension_file(
    current_schema_version,
    multi_extension_out_path,
    upcoming_minor_version,
    template_file: str,
):
    print(
        f"### Adding downgrade scripts from version  {current_schema_version} to  "
        f"{upcoming_minor_version} on {multi_extension_out_path}... ### "
    )
    env = get_template_environment(TEMPLATES_PATH)
    template = env.get_template(
        template_file
    )  # multi_extension_out_prepare_release.tmpl multi_extension_sql_prepare_release.tmpl
    string_to_prepend = f"{template.render(current_schema_version=current_schema_version, upcoming_minor_version=f'{upcoming_minor_version}-1')}\n"

    if not prepend_line_in_file(
        multi_extension_out_path,
        "DROP TABLE prev_objects, extension_diff;",
        string_to_prepend,
    ):
        raise ValueError(
            f"Downgrade scripts could not be added in {multi_extension_out_path} since "
            f"'DROP TABLE prev_objects, extension_diff;' script could not be found  "
        )
    print(
        f"### Done Test downgrade scripts successfully  added in {multi_extension_out_path}. ###"
    )


def get_current_schema_from_citus_control(citus_control_file_path: str) -> str:
    print(f"### Reading current schema version from {citus_control_file_path}... ###")
    current_schema_version = ""
    with open(
        citus_control_file_path,
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as cc_reader:
        cc_file_content = cc_reader.read()
        _, cc_line = find_nth_matching_line_and_line_number(
            cc_file_content, CITUS_CONTROL_SEARCH_PATTERN, 1
        )
        schema_not_found = False
        if len(cc_line) > 0:
            line_parts = cc_line.split("=")
            if len(line_parts) == 2:
                current_schema_version = line_parts[1]
            else:
                schema_not_found = True
        else:
            schema_not_found = True

    if schema_not_found:
        raise ValueError("Version info could not be found in citus.control file")

    current_schema_version = current_schema_version.strip(" '")
    print(f"### Done Schema version is {current_schema_version}. ###")
    return current_schema_version


def update_version_with_upcoming_version_in_config_py(
    config_py_path, upcoming_minor_version
):
    print(
        f"### Updating {config_py_path} file with the upcoming version {upcoming_minor_version}... ###"
    )
    if not replace_line_in_file(
        config_py_path,
        CONFIG_PY_MASTER_VERSION_SEARCH_PATTERN,
        f"MASTER_VERSION = '{upcoming_minor_version}'",
    ):
        raise ValueError(f"{config_py_path} does not have match for version")
    print(
        f"### Done {config_py_path} file updated with the upcoming version {upcoming_minor_version}. ###"
    )


def update_version_in_multi_extension_out(multi_extension_out_path, project_version):
    print(
        f"### Updating {multi_extension_out_path} file with the project version {project_version}... ###"
    )

    if not replace_line_in_file(
        multi_extension_out_path, MULTI_EXT_DEVEL_SEARCH_PATTERN, f" {project_version}"
    ):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {MULTI_EXT_DEVEL_SEARCH_PATTERN}"
        )
    print(
        f"### Done {multi_extension_out_path} file is updated with project version {project_version}. ###"
    )


def update_detail_strings_in_multi_extension_out(
    multi_extension_out_path, minor_version
):
    print(
        f"### Updating {multi_extension_out_path} detail lines file with the project version {minor_version}... ###"
    )

    if not replace_line_in_file(
        multi_extension_out_path,
        MULTI_EXT_DETAIL1_PATTERN,
        f"{MULTI_EXT_DETAIL_PREFIX}{minor_version}{MULTI_EXT_DETAIL1_SUFFIX}",
    ):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {MULTI_EXT_DETAIL1_PATTERN}"
        )

    if not replace_line_in_file(
        multi_extension_out_path,
        MULTI_EXT_DETAIL2_PATTERN,
        f"{MULTI_EXT_DETAIL_PREFIX}{minor_version}{MULTI_EXT_DETAIL2_SUFFIX}",
    ):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {MULTI_EXT_DETAIL2_PATTERN}"
        )

    print(
        f"### Done {multi_extension_out_path} detail lines updated with project version {minor_version}. ###"
    )


def update_version_in_multi_extension_out_for_patch(
    multi_extension_out_path, project_version
):
    print(
        f"### Updating {multi_extension_out_path} file with the project version {project_version}... ###"
    )

    if not replace_line_in_file(
        multi_extension_out_path,
        get_patch_version_regex(project_version),
        f" {project_version}",
    ):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {get_patch_version_regex(project_version)}"
        )
    print(
        f"### Done {multi_extension_out_path} file is updated with project version {project_version}. ###"
    )


def execute_autoconf_f():
    print("### Executing autoconf -f command... ###")
    run("autoconf -f")
    print("### Done autoconf -f executed. ###")


def update_version_in_configure_in(project_name, configure_in_path, project_version):
    print(f"### Updating version on file {configure_in_path}... ###")
    if not replace_line_in_file(
        configure_in_path,
        CONFIGURE_IN_SEARCH_PATTERN,
        f"AC_INIT([{repo_details[project_name]['configure-in-str']}], [{project_version}])",
    ):
        raise ValueError(f"{configure_in_path} does not have match for version")
    print(
        f"### Done {configure_in_path} file is updated with project version {project_version}. ###"
    )


def create_and_checkout_branch(release_branch_name):
    print(
        f"### Creating release branch with name {release_branch_name} from {get_current_branch(os.getcwd())}... ###"
    )
    run(f"git checkout -b {release_branch_name}")
    print(f"### Done {release_branch_name} created. ###")


def checkout_branch(branch_name, is_test):
    print(f"### Checking out {branch_name}... ###")
    run(f"git checkout {branch_name}")
    if not is_test:
        run("git pull")

    print(f"### Done {branch_name} checked out and pulled. ###")


def upgrade_sql_file_name(current_schema_version, upcoming_minor_version):
    return f"citus--{current_schema_version}--{upcoming_minor_version}-1.sql"


def create_new_sql_for_upgrade_path(
    current_schema_version, distributed_dir_path, upcoming_minor_version
):
    newly_created_sql_file = upgrade_sql_file_name(
        current_schema_version, upcoming_minor_version
    )
    print(f"### Creating upgrade file {newly_created_sql_file}... ###")
    with open(
        f"{distributed_dir_path}/{newly_created_sql_file}",
        "w",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as f_writer:
        content = f"-- citus--{current_schema_version}--{upcoming_minor_version}-1"
        content = content + "\n\n"
        content = content + f"-- bump version to {upcoming_minor_version}-1" + "\n\n"
        f_writer.write(content)
    print(f"### Done {newly_created_sql_file} created. ###")
    return newly_created_sql_file


def create_new_sql_for_downgrade_path(
    current_schema_version, distributed_dir_path, upcoming_minor_version
):
    newly_created_sql_file = (
        f"citus--{upcoming_minor_version}-1--{current_schema_version}.sql"
    )
    print(f"### Creating downgrade file {newly_created_sql_file}... ###")
    with open(
        f"{distributed_dir_path}/{newly_created_sql_file}",
        "w",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as f_writer:
        content = f"-- citus--{upcoming_minor_version}-1--{current_schema_version}"
        content = content + "\n"
        content = (
            content + f"-- this is an empty downgrade path since "
            f"{upgrade_sql_file_name(current_schema_version, upcoming_minor_version)} "
            f"is empty for now" + "\n"
        )
        f_writer.write(content)
    print(f"### Done {newly_created_sql_file} created. ###")
    return newly_created_sql_file


CHECKOUT_DIR = "citus_temp"


def validate_parameters(major_release_flag: bool):
    if major_release_flag and arguments.cherry_pick_enabled:
        raise ValueError("Cherry pick could be enabled only for patch release")

    if major_release_flag and arguments.earliest_pr_date:
        raise ValueError("earliest_pr_date could not be used for major releases")

    if major_release_flag and arguments.schema_version:
        raise ValueError("schema_version could not be set for major releases")

    if (
        not major_release_flag
        and arguments.cherry_pick_enabled
        and not arguments.earliest_pr_date
    ):
        raise ValueError(
            "earliest_pr_date parameter could  not be empty when cherry pick is enabled and release is major."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gh_token", required=True)
    parser.add_argument(
        "--prj_name", choices=["citus", "citus-enterprise"], required=True
    )
    parser.add_argument("--prj_ver", required=True)
    parser.add_argument("--main_branch")
    parser.add_argument("--earliest_pr_date")
    parser.add_argument("--cherry_pick_enabled", action="store_true")
    parser.add_argument("--is_test", action="store_true")
    parser.add_argument("--schema_version", nargs="?")
    arguments = parser.parse_args()
    execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
    major_release = is_major_release(arguments.prj_ver)
    validate_parameters(major_release)

    try:
        initialize_env(execution_path, arguments.prj_name, CHECKOUT_DIR)

        is_cherry_pick_enabled = arguments.cherry_pick_enabled
        main_branch = (
            arguments.main_branch
            if arguments.main_branch
            else repo_details[arguments.prj_name]["branch"]
        )
        print(f"Using main branch {main_branch} for the repo {arguments.prj_name}.")
        os.chdir(execution_path)
        print(f"Executing in path {execution_path}")
        earliest_pr_date_value = (
            None
            if major_release or not is_cherry_pick_enabled
            else datetime.strptime(arguments.earliest_pr_date, "%Y.%m.%d")
        )
        proj_params = ProjectParams(
            project_name=arguments.prj_name,
            project_version=arguments.prj_ver,
            main_branch=main_branch,
            schema_version=arguments.schema_version,
        )
        update_release(
            github_token=arguments.gh_token,
            project_params=proj_params,
            earliest_pr_date=earliest_pr_date_value,
            is_test=arguments.is_test,
            cherry_pick_enabled=arguments.cherry_pick_enabled,
            exec_path=execution_path,
        )
    finally:
        if not arguments.is_test:
            remove_cloned_code(execution_path)
