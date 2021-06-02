import os
import uuid
from dataclasses import dataclass
from datetime import datetime
import argparse

import pathlib2
from github import Github, Repository
from parameters_validation import (non_blank, non_empty)

from .common_tool_methods import (get_version_details, get_upcoming_patch_version, is_major_release,
                                  get_prs_for_patch_release,
                                  filter_prs_by_label, cherry_pick_prs, run, replace_line_in_file, get_current_branch,
                                  find_nth_matching_line_and_line_number, get_minor_version, get_patch_version_regex,
                                  append_line_in_file, prepend_line_in_file, get_template_environment,
                                  does_branch_exist)
from .common_validations import (CITUS_MINOR_VERSION_PATTERN, CITUS_PATCH_VERSION_PATTERN, is_version)

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

MULTI_EXT_DETAIL_PREFIX = rf"DETAIL:  Loaded library requires "
MULTI_EXT_DETAIL1_SUFFIX = rf", but 8.0-1 was specified."
MULTI_EXT_DETAIL2_SUFFIX = rf", but the installed extension version is 8.1-1."
MULTI_EXT_DETAIL1_PATTERN = rf"^{MULTI_EXT_DETAIL_PREFIX}\d+\.\d+{MULTI_EXT_DETAIL1_SUFFIX}$"

MULTI_EXT_DETAIL2_PATTERN = (
    rf"^{MULTI_EXT_DETAIL_PREFIX}\d+\.\d+{MULTI_EXT_DETAIL2_SUFFIX}$")

CONFIG_PY_MASTER_VERSION_SEARCH_PATTERN = r"^MASTER_VERSION = '\d+\.\d+'"

CONFIGURE_IN_SEARCH_PATTERN = "AC_INIT*"
REPO_OWNER = "citusdata"

BASE_PATH = pathlib2.Path(__file__).parent.absolute()
TEMPLATES_PATH = f"{BASE_PATH}/templates"

MULTI_EXT_OUT_TEMPLATE_FILE = "multi_extension_out_prepare_release.tmpl"
MULTI_EXT_SQL_TEMPLATE_FILE = "multi_extension_sql_prepare_release.tmpl"


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
    devel_version: str
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
    upcoming_version: str
    upcoming_version_branch: str


@dataclass
class PatchReleaseParams:
    cherry_pick_enabled: bool
    configure_in_path: str
    earliest_pr_date: datetime
    is_test: bool
    main_branch: str
    citus_control_file_path: str
    multi_extension_out_path: str
    project_name: str
    project_version: str
    release_branch_name: str
    schema_version: str
    repository: Repository


BASE_GIT_PATH = pathlib2.Path(__file__).parents[1]


def update_release(github_token: non_blank(non_empty(str)), project_name: non_blank(non_empty(str)),
                   project_version: is_version(str), main_branch: non_blank(non_empty(str)),
                   earliest_pr_date: datetime, exec_path: non_blank(non_empty(str)), schema_version: str = "",
                   is_test: bool = False, cherry_pick_enabled: bool = False) -> UpdateReleaseReturnValue:
    multi_extension_sql_path = f"{exec_path}/{MULTI_EXTENSION_SQL}"
    citus_control_file_path = f"{exec_path}/{CITUS_CONTROL}"
    multi_extension_out_path = f"{exec_path}/{MULTI_EXTENSION_OUT}"
    configure_in_path = f"{exec_path}/{CONFIGURE_IN}"
    config_py_path = f"{exec_path}/{CONFIG_PY}"
    distributed_dir_path = f"{exec_path}/{DISTRIBUTED_SQL_DIR_PATH}"
    downgrades_dir_path = f"{exec_path}/{DOWNGRADES_DIR_PATH}"

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
    upgrade_file = ""
    downgrade_file = ""

    # major release
    if is_major_release(project_version):
        print(f"### {project_version} is a major release. Executing Major release flow... ###")
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
                                                    downgrades_dir_path=downgrades_dir_path,
                                                    repository=repository,
                                                    upcoming_minor_version=upcoming_minor_version,
                                                    multi_extension_out_path=multi_extension_out_path,
                                                    multi_extension_sql_path=multi_extension_sql_path)

        upgrade_file, downgrade_file = prepare_upcoming_version_branch(branch_params)
        print(f"### Done {project_version} Major release flow executed successfully. ###")
    # patch release
    else:
        patch_release_params = PatchReleaseParams(cherry_pick_enabled=cherry_pick_enabled,
                                                  configure_in_path=configure_in_path,
                                                  earliest_pr_date=earliest_pr_date, is_test=is_test,
                                                  main_branch=main_branch,
                                                  multi_extension_out_path=multi_extension_out_path,
                                                  project_name=project_name, project_version=project_version,
                                                  schema_version=schema_version,
                                                  citus_control_file_path=citus_control_file_path,
                                                  release_branch_name=release_branch_name, repository=repository)
        prepare_release_branch_for_patch_release(patch_release_params)
    return UpdateReleaseReturnValue(release_branch_name, upcoming_version_branch,
                                    f"{DISTRIBUTED_SQL_DIR_PATH}/{upgrade_file}",
                                    f"{DOWNGRADES_DIR_PATH}/{downgrade_file}")


def prepare_release_branch_for_patch_release(patchReleaseParams: PatchReleaseParams):
    print(f"### {patchReleaseParams.project_version} is a patch release. Executing Patch release flow... ###")
    # checkout release branch (release-X.Y) In test case release branch for test may not be exist.
    # In this case create one
    if patchReleaseParams.is_test:
        non_test_release_branch = patchReleaseParams.release_branch_name.rstrip("-test")
        run(f"git checkout {non_test_release_branch}")
        run(f"git checkout -b {patchReleaseParams.release_branch_name}")
    else:
        checkout_branch(patchReleaseParams.release_branch_name, patchReleaseParams.is_test)
    # change version info in configure.in file
    update_version_in_configure_in(patchReleaseParams.configure_in_path, patchReleaseParams.project_version)
    # execute "auto-conf "
    execute_autoconf_f()
    # change version info in multi_extension.out
    update_version_in_multi_extension_out_for_patch(patchReleaseParams.multi_extension_out_path,
                                                    patchReleaseParams.project_version)
    # if schema version is not empty update citus.control schema version
    if patchReleaseParams.schema_version:
        update_schema_version_in_citus_control(citus_control_file_path=patchReleaseParams.citus_control_file_path,
                                               schema_version=patchReleaseParams.schema_version)
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

    print(f"### Done Patch release flow executed successfully. ###")


def prepare_upcoming_version_branch(upcoming_params: UpcomingVersionBranchParams):
    print(f"### {upcoming_params.upcoming_version_branch} flow is being executed... ###")
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
    # update detail lines with minor version
    update_detail_strings_in_multi_extension_out(upcoming_params.multi_extension_out_path,
                                                 upcoming_params.upcoming_minor_version)
    # get current schema version from citus.control
    current_schema_version = get_current_schema_from_citus_control(upcoming_params.citus_control_file_path)
    # add downgrade script in multi_extension.sql file
    add_downgrade_script_in_multi_extension_file(current_schema_version,
                                                 upcoming_params.multi_extension_sql_path,
                                                 upcoming_params.upcoming_minor_version, MULTI_EXT_SQL_TEMPLATE_FILE)
    # add downgrade script in multi_extension.out file
    add_downgrade_script_in_multi_extension_file(current_schema_version,
                                                 upcoming_params.multi_extension_out_path,
                                                 upcoming_params.upcoming_minor_version, MULTI_EXT_OUT_TEMPLATE_FILE)
    # create a new sql file for upgrade path:
    upgrade_file = create_new_sql_for_upgrade_path(current_schema_version,
                                                   upcoming_params.distributed_dir_path,
                                                   upcoming_params.upcoming_minor_version)
    # create a new sql file for downgrade path:
    downgrade_file = create_new_sql_for_downgrade_path(current_schema_version,
                                                       upcoming_params.downgrades_dir_path,
                                                       upcoming_params.upcoming_minor_version)

    # change version in citus.control file
    default_upcoming_schema_version = f"{upcoming_params.upcoming_minor_version}-1"
    update_schema_version_in_citus_control(upcoming_params.citus_control_file_path,
                                           default_upcoming_schema_version)
    # commit and push changes on master-update-version-$curtime branch
    commit_changes_for_version_bump(upcoming_params.project_name, upcoming_params.project_version)
    if not upcoming_params.is_test:
        push_branch(upcoming_params.upcoming_version_branch)

        # create pull request
        create_pull_request_for_upcoming_version_branch(upcoming_params.repository, upcoming_params.main_branch,
                                                        upcoming_params.upcoming_version_branch,
                                                        upcoming_params.upcoming_version)
    print(f"### Done {upcoming_params.upcoming_version_branch} flow executed. ###")
    return upgrade_file, downgrade_file


def prepare_release_branch_for_major_release(majorReleaseParams: MajorReleaseParams):
    print(f"###  {majorReleaseParams.release_branch_name} release branch flow is being executed... ###")
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
    print(f"### Done {majorReleaseParams.release_branch_name} release branch flow executed .###")


def cherrypick_prs_with_backport_labels(earliest_pr_date, main_branch, release_branch_name, repository):
    print(
        f"### Getting all PR with backport label after {datetime.strftime(earliest_pr_date, '%Y.%m.%d %H:%M')}... ### ")
    prs_with_earliest_date = get_prs_for_patch_release(repository, earliest_pr_date, main_branch)
    # get commits for selected prs with backport label
    prs_with_backport = filter_prs_by_label(prs_with_earliest_date, "backport")
    print(f"### Done {len(prs_with_backport)} PRs with backport label found. PR list is as below. ###")
    for pr in prs_with_backport:
        print(f"\tNo:{pr.number} Title:{pr.title}")
    # cherrypick all commits with backport label
    print(f"### Cherry-picking PRs to {release_branch_name}... ###")
    cherry_pick_prs(prs_with_backport)
    print(f"### Done Cherry pick completed for all PRs on branch {release_branch_name}. ###")


def create_pull_request_for_upcoming_version_branch(repository, main_branch, upcoming_version_branch, upcoming_version):
    print(f"### Creating pull request for {upcoming_version_branch}... ###")
    pr_result = repository.create_pull(title=f"Bump Citus to {upcoming_version}", base=main_branch,
                                       head=upcoming_version_branch, body="")
    print(f"### Done Pull request created. PR no:{pr_result.number} PR URL: {pr_result.url}. ###  ")


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
    print(f"### Updating {citus_control_file_path} file with the  version {schema_version}... ###")
    if not replace_line_in_file(citus_control_file_path, CITUS_CONTROL_SEARCH_PATTERN,
                                f"default_version = '{schema_version}'"):
        raise ValueError(f"{citus_control_file_path} does not have match for version")
    print(f"### Done {citus_control_file_path} file is updated with the schema version {schema_version}. ###")


def add_downgrade_script_in_multi_extension_file(current_schema_version,
                                                 multi_extension_out_path,
                                                 upcoming_minor_version, template_file: str):
    print(f"### Adding downgrade scripts from version  {current_schema_version} to  "
          f"{upcoming_minor_version} on {multi_extension_out_path}... ### ")
    env = get_template_environment(TEMPLATES_PATH)
    template = env.get_template(
        template_file)  # multi_extension_out_prepare_release.tmpl multi_extension_sql_prepare_release.tmpl
    string_to_prepend = (
        f"{template.render(current_schema_version=current_schema_version, upcoming_minor_version=f'{upcoming_minor_version}-1')}\n")

    if not prepend_line_in_file(multi_extension_out_path,
                                f"DROP TABLE prev_objects, extension_diff;",
                                string_to_prepend):
        raise ValueError(f"Downgrade scripts could not be added in {multi_extension_out_path} since "
                         f"'DROP TABLE prev_objects, extension_diff;' script could not be found  ")
    print(f"### Done Test downgrade scripts successfully  added in {multi_extension_out_path}. ###")


def get_current_schema_from_citus_control(citus_control_file_path: str) -> str:
    print(f"### Reading current schema version from {citus_control_file_path}... ###")
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
    print(f"### Done Schema version is {current_schema_version}. ###")
    return current_schema_version


def update_version_with_upcoming_version_in_config_py(config_py_path, upcoming_minor_version):
    print(f"### Updating {config_py_path} file with the upcoming version {upcoming_minor_version}... ###")
    if not replace_line_in_file(config_py_path, CONFIG_PY_MASTER_VERSION_SEARCH_PATTERN,
                                f"MASTER_VERSION = '{upcoming_minor_version}'"):
        raise ValueError(f"{config_py_path} does not have match for version")
    print(f"### Done {config_py_path} file updated with the upcoming version {upcoming_minor_version}. ###")


def update_version_in_multi_extension_out(multi_extension_out_path, project_version):
    print(f"### Updating {multi_extension_out_path} file with the project version {project_version}... ###")

    if not replace_line_in_file(multi_extension_out_path, MULTI_EXT_DEVEL_SEARCH_PATTERN,
                                f" {project_version}"):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {CONFIGURE_IN_SEARCH_PATTERN}")
    print(f"### Done {multi_extension_out_path} file is updated with project version {project_version}. ###")


def update_detail_strings_in_multi_extension_out(multi_extension_out_path, minor_version):
    print(f"### Updating {multi_extension_out_path} detail lines file with the project version {minor_version}... ###")

    if not replace_line_in_file(multi_extension_out_path, MULTI_EXT_DETAIL1_PATTERN,
                                f"{MULTI_EXT_DETAIL_PREFIX}{minor_version}{MULTI_EXT_DETAIL1_SUFFIX}"):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {MULTI_EXT_DETAIL1_PATTERN}")

    if not replace_line_in_file(multi_extension_out_path, MULTI_EXT_DETAIL2_PATTERN,
                                f"{MULTI_EXT_DETAIL_PREFIX}{minor_version}{MULTI_EXT_DETAIL2_SUFFIX}"):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {MULTI_EXT_DETAIL2_PATTERN}")

    print(f"### Done {multi_extension_out_path} detail lines updated with project version {minor_version}. ###")


def update_version_in_multi_extension_out_for_patch(multi_extension_out_path, project_version):
    print(f"### Updating {multi_extension_out_path} file with the project version {project_version}... ###")

    if not replace_line_in_file(multi_extension_out_path,
                                get_patch_version_regex(project_version),
                                f" {project_version}"):
        raise ValueError(
            f"{multi_extension_out_path} does not contain the version with pattern {CONFIGURE_IN_SEARCH_PATTERN}")
    print(f"### Done {multi_extension_out_path} file is updated with project version {project_version}. ###")


def execute_autoconf_f():
    print(f"### Executing autoconf -f command... ###")
    run("autoconf -f")
    print(f"### Done autoconf -f executed. ###")


def update_version_in_configure_in(configure_in_path, project_version):
    print(f"### Updating version on file {configure_in_path}... ###")
    if not replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN,
                                f"AC_INIT([Citus], [{project_version}])"):
        raise ValueError(f"{configure_in_path} does not have match for version")
    print(f"### Done {configure_in_path} file is updated with project version {project_version}. ###")


def create_and_checkout_branch(release_branch_name):
    print(f"### Creating release branch with name {release_branch_name} from {get_current_branch(os.getcwd())}... ###")
    run(f'git checkout -b {release_branch_name}')
    print(f"### Done {release_branch_name} created. ###")


def checkout_branch(branch_name, is_test):
    print(f"### Checking out {branch_name}... ###")
    run(f"git checkout {branch_name}")
    if not is_test:
        run(f"git pull")

    print(f"### Done {branch_name} checked out and pulled. ###")


def upgrade_sql_file_name(current_schema_version, upcoming_minor_version):
    return f"citus--{current_schema_version}--{upcoming_minor_version}-1.sql"


def create_new_sql_for_upgrade_path(current_schema_version, distributed_dir_path,
                                    upcoming_minor_version):
    newly_created_sql_file = upgrade_sql_file_name(current_schema_version, upcoming_minor_version)
    print(f"### Creating upgrade file {newly_created_sql_file}... ###")
    with open(f"{distributed_dir_path}/{newly_created_sql_file}", "w") as f_writer:
        content = f"/* citus--{current_schema_version}--{upcoming_minor_version}-1 */"
        content = content + "\n\n"
        content = content + f"-- bump version to {upcoming_minor_version}-1" + "\n\n"
        f_writer.write(content)
    print(f"### Done {newly_created_sql_file} created. ###")
    return newly_created_sql_file


def create_new_sql_for_downgrade_path(current_schema_version, distributed_dir_path,
                                      upcoming_minor_version):
    newly_created_sql_file = f"citus--{upcoming_minor_version}--{current_schema_version}-1.sql"
    print(f"### Creating downgrade file {newly_created_sql_file}... ###")
    with open(f"{distributed_dir_path}/{newly_created_sql_file}", "w") as f_writer:
        content = f"/* citus--{upcoming_minor_version}--{current_schema_version}-1 */"
        content = content + "\n"
        content = (
                content + f"-- this is an empty downgrade path since "
                          f"{upgrade_sql_file_name(current_schema_version, distributed_dir_path)} "
                          f"is empty for now" + "\n\n")
        f_writer.write(content)
    print(f"### Done {newly_created_sql_file} created. ###")
    return newly_created_sql_file


CHECKOUT_DIR = "citus_temp"


def remove_cloned_code(exec_path: str):
    if os.path.exists(f"{exec_path}"):
        print("Deleting cloned code ...")
        os.chdir("..")
        run(f"sudo rm -rf {os.path.basename(exec_path)}")
        print("Done. Code deleted successfully.")


def initialize_env(exec_path: str):
    remove_cloned_code(exec_path)
    if not os.path.exists(CHECKOUT_DIR):
        run(f"git clone https://github.com/citusdata/citus.git {CHECKOUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token')
    parser.add_argument('--prj_name')
    parser.add_argument('--prj_ver')
    parser.add_argument('--main_branch')
    parser.add_argument('--earliest_pr_date')
    parser.add_argument('--exec_path')
    parser.add_argument('--cherry_pick_enabled', nargs='?', default="False")
    parser.add_argument('--is_test', nargs='?', default="False")
    parser.add_argument('--schema_version', nargs='?')
    arguments = parser.parse_args()
    is_test = False
    execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
    try:
        initialize_env(execution_path)
        major_release = is_major_release(arguments.prj_ver)
        is_cherry_pick_enabled = arguments.cherry_pick_enabled.lower() == "true"
        if not arguments.prj_ver and major_release and arguments.cherry_pick_enabled.lower() == "true":
            raise ValueError("Cherry-Pick could be enabled only for patch release")
        elif not major_release and arguments.cherry_pick_enabled.lower() == "true" \
                and not arguments.earliest_pr_date:
            raise ValueError(
                "Earliest PR date parameter should not be empty when cherry pick is enabled and release is major.")
        earliest_pr_date = None if major_release or not is_cherry_pick_enabled else datetime.strptime(
            arguments.earliest_pr_date,
            '%Y.%m.%d %H:%M:%S %z')

        os.chdir(execution_path)
        print(f"Executing in path {execution_path}")
        is_test = arguments.is_test.lower() == "true"

        update_release(github_token=arguments.gh_token, project_name=arguments.prj_name,
                       project_version=arguments.prj_ver,
                       main_branch=arguments.main_branch,
                       earliest_pr_date=earliest_pr_date,
                       is_test=is_test,
                       cherry_pick_enabled=is_cherry_pick_enabled, exec_path=execution_path,
                       schema_version=arguments.schema_version)
    finally:
        if not is_test:
            remove_cloned_code(execution_path)
