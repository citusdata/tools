import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

import pathlib2
from github import Github, Repository

from .common_tool_methods import (get_version_details, get_upcoming_patch_version, is_major_release,
                                  get_prs_for_patch_release,
                                  filter_prs_by_label, cherry_pick_prs, run, replace_line_in_file, get_current_branch,
                                  find_nth_matching_line_and_line_number, get_minor_version, get_patch_version_regex,append_line_in_file)
from .common_validations import CITUS_MINOR_VERSION_PATTERN, CITUS_PATCH_VERSION_PATTERN, is_version

MULTI_EXTENSION_SQL = "src/test/regress/sql/multi_extension.sql"
CITUS_CONTROL = "src/backend/distributed/citus.control"
MULTI_EXTENSION_OUT = "src/test/regress/expected/multi_extension.out"
CONFIG_PY = "src/test/regress/upgrade/config.py"
DISTRIBUTED_DIR_PATH = "src/backend/distributed"
CONFIGURE_IN = "configure.in"
CONFIGURE = "configure"
CITUS_CONTROL_SEARCH_PATTERN = r"^default_version*"

MULTI_EXT_DEVEL_SEARCH_PATTERN = rf"^\s*{CITUS_MINOR_VERSION_PATTERN}devel$"
MULTI_EXT_PATCH_SEARCH_PATTERN = rf"^\s*{CITUS_PATCH_VERSION_PATTERN}$"
CONFIG_PY_MASTER_VERSION_SEARCH_PATTERN = r"^MASTER_VERSION = '\d+\.\d+'"

CONFIGURE_IN_SEARCH_PATTERN = "AC_INIT*"
REPO_OWNER = "citusdata"


@dataclass
class UpdateReleaseReturnValue:
    release_branch_name: str
    upcoming_version_branch: str
    upgrade_path_sql_file: str


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
    devel_version: str
    distributed_dir_path: str
    is_test: bool
    main_branch: str
    multi_extension_out_path: str
    multi_extension_sql_path: str
    project_name: str
    project_version: str
    repository: Repository
    upcoming_minor_version: str
    upcoming_version: str
    upcoming_version_branch: str


@dataclass
class PatchReleaseParams:
    cherry_pick_enabled: bool
    configure_in_path: str
    earliest_pr_date: datetime
    is_test: bool
    main_branch: str
    multi_extension_out_path: str
    project_name: str
    project_version: str
    release_branch_name: str
    repository: Repository


BASE_GIT_PATH = pathlib2.Path(__file__).parents[1]


def update_release(github_token: str, project_name: str, project_version: is_version(str), main_branch: str,
                   earliest_pr_date: datetime, exec_path: str, is_test: bool = False,
                   cherry_pick_enabled: bool = False) -> UpdateReleaseReturnValue:
    multi_extension_sql_path = f"{exec_path}/{MULTI_EXTENSION_SQL}"
    citus_control_file_path = f"{exec_path}/{CITUS_CONTROL}"
    multi_extension_out_path = f"{exec_path}/{MULTI_EXTENSION_OUT}"
    configure_in_path = f"{exec_path}/{CONFIGURE_IN}"
    config_py_path = f"{exec_path}/{CONFIG_PY}"
    distributed_dir_path = f"{exec_path}/{DISTRIBUTED_DIR_PATH}"

    project_version_details = get_version_details(project_version)
    default_upcoming_version = get_upcoming_patch_version(project_version)
    upcoming_version = os.getenv("UPCOMING_VERSION", default=default_upcoming_version)
    upcoming_minor_version = get_minor_version(upcoming_version)
    devel_version = f"{upcoming_minor_version}devel"

    release_branch_name = f'release-{project_version_details["major"]}.{project_version_details["minor"]}'
    release_branch_name = f"{release_branch_name}-test" if is_test else release_branch_name
    upcoming_version_branch = f"master-update-version-{uuid.uuid4()}"

    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{project_name}")
    newly_created_sql_file = ""

    # major release
    if is_major_release(project_version):
        print(f"### {project_version} is a major release. Executing Major release flow###")
        major_release_params = MajorReleaseParams(configure_in_path=configure_in_path, devel_version=devel_version,
                                                  is_test=is_test, main_branch=main_branch,
                                                  multi_extension_out_path=multi_extension_out_path,
                                                  project_name=project_name, project_version=project_version,
                                                  release_branch_name=release_branch_name)
        prepare_release_branch_for_major_release(major_release_params)
        branch_params = UpcomingVersionBranchParams(project_version=project_version,
                                                    project_name=project_name,
                                                    upcoming_version=upcoming_version,
                                                    upcoming_version_branch=upcoming_version_branch,
                                                    devel_version=devel_version, is_test=is_test,
                                                    main_branch=main_branch,
                                                    citus_control_file_path=citus_control_file_path,
                                                    config_py_path=config_py_path,
                                                    configure_in_path=configure_in_path,
                                                    distributed_dir_path=distributed_dir_path,
                                                    repository=repository,
                                                    upcoming_minor_version=upcoming_minor_version,
                                                    multi_extension_out_path=multi_extension_out_path,
                                                    multi_extension_sql_path=multi_extension_sql_path)

        newly_created_sql_file = prepare_upcoming_version_branch(branch_params)
        print(f"OK {project_version} Major release flow executed successfully")
    # patch release
    else:
        patch_release_params = PatchReleaseParams(cherry_pick_enabled=cherry_pick_enabled,
                                                  configure_in_path=configure_in_path,
                                                  earliest_pr_date=earliest_pr_date, is_test=is_test,
                                                  main_branch=main_branch,
                                                  multi_extension_out_path=multi_extension_out_path,
                                                  project_name=project_name, project_version=project_version,
                                                  release_branch_name=release_branch_name, repository=repository)
        prepare_release_branch_for_patch_release(patch_release_params)
    return UpdateReleaseReturnValue(release_branch_name, upcoming_version_branch,
                                    f"{DISTRIBUTED_DIR_PATH}/{newly_created_sql_file}")


def prepare_release_branch_for_patch_release(patchReleaseParams: PatchReleaseParams):
    print(f"### {patchReleaseParams.project_version} is a patch release. Executing Patch release flow ###")
    # checkout release branch (release-X.Y)
    checkout_branch(patchReleaseParams.release_branch_name, patchReleaseParams.is_test)
    # change version info in configure.in file
    update_version_in_configure_in(patchReleaseParams.configure_in_path, patchReleaseParams.project_version)
    # execute "auto-conf "
    execute_autoconf_f()
    # change version info in multi_extension.out
    update_version_in_multi_extension_out_for_patch(patchReleaseParams.multi_extension_out_path,
                                                    patchReleaseParams.project_version)
    if patchReleaseParams.cherry_pick_enabled:
        # cherry-pick the pr's with backport labels
        cherrypick_prs_with_backport_labels(patchReleaseParams.earliest_pr_date, patchReleaseParams.main_branch,
                                            patchReleaseParams.release_branch_name, patchReleaseParams.repository)
    # commit all changes
    commit_changes_for_version_bump(patchReleaseParams.project_name, patchReleaseParams.project_version)
    # create and push release-$minor_version-push-$curTime branch
    release_pr_branch = f"{patchReleaseParams.release_branch_name}_{uuid.uuid4()}"
    create_and_checkout_branch(release_pr_branch)
    if not patchReleaseParams.is_test:
        push_branch(release_pr_branch)


def prepare_upcoming_version_branch(upcoming_params: UpcomingVersionBranchParams):
    print(f"### Preparing {upcoming_params.upcoming_version_branch} branch that bumps master version.###")
    # checkout master
    checkout_branch(upcoming_params.main_branch, upcoming_params.is_test)
    # create master-update-version-$curtime branch
    create_and_checkout_branch(upcoming_params.upcoming_version_branch)
    # update version info with upcoming version on configure.in
    update_version_in_configure_in(upcoming_params.configure_in_path, upcoming_params.devel_version)
    # update version info with upcoming version on config.py
    update_version_with_upcoming_version_in_config_py(upcoming_params.config_py_path,
                                                      upcoming_params.upcoming_minor_version)
    # execute autoconf -f
    execute_autoconf_f()
    # update version info with upcoming version on multiextension.out
    update_version_in_multi_extension_out(upcoming_params.multi_extension_out_path, upcoming_params.devel_version)
    # get current schema version from citus.control
    current_schema_version = get_current_schema_from_citus_control(upcoming_params.citus_control_file_path)
    # find current schema version info and update it with upcoming version in multi_extension.sql file
    update_schema_version_with_upcoming_version_in_multi_extension_file(current_schema_version,
                                                                        upcoming_params.multi_extension_sql_path,
                                                                        upcoming_params.upcoming_minor_version,
                                                                        upcoming_params.upcoming_version)
    # find current schema version info and update it with upcoming version in multi_extension.out file
    update_schema_version_with_upcoming_version_in_multi_extension_file(current_schema_version,
                                                                        upcoming_params.multi_extension_out_path,
                                                                        upcoming_params.upcoming_minor_version,
                                                                        upcoming_params.upcoming_version)
    # create a new sql file for upgrade path:
    newly_created_sql_file = create_new_sql_for_upgrade_path(current_schema_version,
                                                             upcoming_params.distributed_dir_path,
                                                             upcoming_params.upcoming_minor_version)
    # change version in citus.control file
    update_version_with_upcoming_version_in_citus_control(upcoming_params.citus_control_file_path,
                                                          upcoming_params.upcoming_minor_version)
    # commit and push changes on master-update-version-$curtime branch
    commit_changes_for_version_bump(upcoming_params.project_name, upcoming_params.project_version)
    if not upcoming_params.is_test:
        push_branch(upcoming_params.upcoming_version_branch)

        # create pull request
        create_pull_request_for_upcoming_version_branch(upcoming_params.repository, upcoming_params.main_branch,
                                                        upcoming_params.upcoming_version_branch,
                                                        upcoming_params.upcoming_version)
    print(f"### OK {upcoming_params.upcoming_version_branch} prepared.###")
    return newly_created_sql_file


def prepare_release_branch_for_major_release(majorReleaseParams: MajorReleaseParams):
    print(f"### Preparing {majorReleaseParams.release_branch_name}...###")
    # checkout master
    checkout_branch(majorReleaseParams.main_branch, majorReleaseParams.is_test)
    # create release branch in release-X.Y format
    create_and_checkout_branch(majorReleaseParams.release_branch_name)
    # change version info in configure.in file
    update_version_in_configure_in(majorReleaseParams.configure_in_path, majorReleaseParams.project_version)
    # execute "autoconf -f"
    execute_autoconf_f()
    # change version info in multi_extension.out
    update_version_in_multi_extension_out(majorReleaseParams.multi_extension_out_path,
                                          majorReleaseParams.project_version)
    # commit all changes
    commit_changes_for_version_bump(majorReleaseParams.project_name, majorReleaseParams.project_version)
    # push release branch (No PR creation!!!)
    if not majorReleaseParams.is_test:
        push_branch(majorReleaseParams.release_branch_name)
    print(f"### OK {majorReleaseParams.release_branch_name} prepared.###")


def cherrypick_prs_with_backport_labels(earliest_pr_date, main_branch, release_branch_name, repository):
    print(
        f"### Getting all PR with backport label after {datetime.strftime(earliest_pr_date, '%Y.%m.%d %H:%M')}### ")
    prs_with_earliest_date = get_prs_for_patch_release(repository, earliest_pr_date, main_branch)
    # get commits for selected prs with backport label
    prs_with_backport = filter_prs_by_label(prs_with_earliest_date, "backport")
    print(f"### OK {len(prs_with_backport)} PRs with backport label found. PR list is as below###")
    for pr in prs_with_backport:
        print(f"\tNo:{pr.number} Title:{pr.title}")
    # cherrypick all commits with backport label
    print(f"Cherry-picking PRs to {release_branch_name}...")
    cherry_pick_prs(prs_with_backport)
    print(f"OK Cherry pick completed for all PRs on branch {release_branch_name}")


def create_pull_request_for_upcoming_version_branch(repository, main_branch, upcoming_version_branch, upcoming_version):
    print(f"### Creating pull request for {upcoming_version_branch}###")
    pr_result = repository.create_pull(title=f"Bump Citus to {upcoming_version}", base=main_branch,
                                       head=upcoming_version_branch, body="")
    print(f"### OK Pull request created. PR Number:{pr_result.number} PR URL: {pr_result.url}###")


def push_branch(upcoming_version_branch):
    print(f"Pushing changes for {upcoming_version_branch} into remote origin...###")
    run(f"git push --set-upstream origin {upcoming_version_branch}")
    print(f"### OK Changes pushed for {upcoming_version_branch}###")


def commit_changes_for_version_bump(project_name, project_version):
    current_branch = get_current_branch()
    print(f"### Committing changes for branch {current_branch}...###")

    run(f' git commit -a -m "Bump {project_name} version to {project_version} "')
    print(f"### OK Changes committed for {current_branch}###")


def update_version_with_upcoming_version_in_citus_control(citus_control_file_path, upcoming_minor_version):
    print(f"### Updating {citus_control_file_path} file with the upcoming version {upcoming_minor_version}...###")
    if not replace_line_in_file(citus_control_file_path, CITUS_CONTROL_SEARCH_PATTERN,
                                f"default_version = '{upcoming_minor_version}-1'"):
        raise ValueError(f"{citus_control_file_path} does not have match for version")
    print(f"### OK {citus_control_file_path} file is updated with the upcoming version {upcoming_minor_version}...###")


def update_schema_version_with_upcoming_version_in_multi_extension_file(current_schema_version,
                                                                        multi_extension_sql_path,
                                                                        upcoming_minor_version, upcoming_version):
    print(
        f"### Updating schema version {current_schema_version} on {multi_extension_sql_path} "
        f"file with the upcoming version {upcoming_version}...### ")
    # TODO Append instead of replace may require
    if not append_line_in_file(multi_extension_sql_path,
                                f"ALTER EXTENSION citus UPDATE TO '{current_schema_version}'",
                                f"ALTER EXTENSION citus UPDATE TO '{upcoming_minor_version}-1';"):
        raise ValueError(f"{multi_extension_sql_path} does not have match for version")
    print(f"### OK Current schema version updated on {multi_extension_sql_path} to {upcoming_minor_version}###")


def get_current_schema_from_citus_control(citus_control_file_path: str) -> str:
    print(f"### Reading current schema version from {citus_control_file_path}...###")
    current_schema_version = ""
    with open(citus_control_file_path, "r") as cc_reader:
        cc_file_content = cc_reader.read()
        cc_line_number, cc_line = find_nth_matching_line_and_line_number(cc_file_content, CITUS_CONTROL_SEARCH_PATTERN,
                                                                         1)
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
    print(f"OK Schema version is {current_schema_version}")
    return current_schema_version


def update_version_with_upcoming_version_in_config_py(config_py_path, upcoming_minor_version):
    print(f"### Updating {config_py_path} file with the upcoming version {upcoming_minor_version}...###")
    if not replace_line_in_file(config_py_path, CONFIG_PY_MASTER_VERSION_SEARCH_PATTERN,
                                f"MASTER_VERSION = '{upcoming_minor_version}'"):
        raise ValueError(f"{config_py_path} does not have match for version")
    print(f"### {config_py_path} file updated with the upcoming version {upcoming_minor_version}...###")


def update_version_in_multi_extension_out(multi_extension_out_path, project_version):
    print(f"### Updating {multi_extension_out_path} file with the project version {project_version}...###")

    if not replace_line_in_file(multi_extension_out_path, MULTI_EXT_DEVEL_SEARCH_PATTERN,
                                f" {project_version}"):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {CONFIGURE_IN_SEARCH_PATTERN}")
    print(f"### OK {multi_extension_out_path} file is updated with project version {project_version}.###")


def update_version_in_multi_extension_out_for_patch(multi_extension_out_path, project_version):
    print(f"### Updating {multi_extension_out_path} file with the project version {project_version}...###")

    if not replace_line_in_file(multi_extension_out_path,
                                get_patch_version_regex(project_version),
                                f" {project_version}"):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {CONFIGURE_IN_SEARCH_PATTERN}")
    print(f"### OK {multi_extension_out_path} file is updated with project version {project_version}.###")


def execute_autoconf_f():
    print(f"### Executing autoconf -f command...###")
    run("autoconf -f")
    print(f"### OK autoconf -f executed.###")


def update_version_in_configure_in(configure_in_path, project_version):
    print(f"### Updating version on file {configure_in_path}...###")
    if not replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN,
                                f"AC_INIT([Citus], [{project_version}])"):
        raise ValueError(f"{configure_in_path} does not have match for version")
    print(f"### OK {configure_in_path} file is updated with project version {project_version}.###")


def create_and_checkout_branch(release_branch_name):
    print(f"### Creating release branch with name {release_branch_name} from {get_current_branch()}...###")
    run(f'git checkout -b {release_branch_name}')
    print(f"### OK {release_branch_name} created###")


def checkout_branch(branch_name, is_test):
    print(f"### Checking out {branch_name}...###")
    run(f"git checkout {branch_name}")
    if not is_test:
        run(f"git pull")
    print(f"### OK {branch_name} checked out and pulled###")


def create_new_sql_for_upgrade_path(current_schema_version, distributed_dir_path,
                                    upcoming_minor_version):
    newly_created_sql_file = f"citus--{current_schema_version}--{upcoming_minor_version}-1.sql"
    print(f"### Creating file {newly_created_sql_file}...###")
    with open(f"{distributed_dir_path}/{newly_created_sql_file}", "w") as f_writer:
        content = f"/* citus--{current_schema_version}--{upcoming_minor_version}-1 */"
        content = content + "\n\n"
        content = content + f"-- bump version to {upcoming_minor_version}-1" + "\n\n"
        f_writer.write(content)
    print(f"### OK {newly_created_sql_file} created.")
    return newly_created_sql_file
