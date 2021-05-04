import uuid
from enum import Enum
from typing import Tuple

from github import Github

from .common_tool_methods import *
from .common_validations import *

MULTI_EXTENSION_SQL = "src/test/regress/sql/multi_extension.sql"
CITUS_CONTROL = "src/backend/distributed/citus.control"
MULTI_EXTENSION_OUT = "src/test/regress/expected/multi_extension.out"
CONFIG_PY = "src/test/regress/upgrade/config.py"
DISTRIBUTED_DIR_PATH = "src/backend/distributed"
CONFIGURE_IN = "configure.in"
CONFIGURE = "configure"
CITUS_CONTROL_SEARCH_PATTERN = r"^default_version*"

MULTI_EXT_MAJOR_SEARCH_PATTERN = r"^\s*\d{1,2}\.\d{1,2}devel$"
MULTI_EXT_MINOR_PATCH_SEARCH_PATTERN = r"^\s*" + CITUS_VERSION_PATTERN

CONFIGURE_IN_SEARCH_PATTERN = "AC_INIT*"
REPO_OWNER = "citusdata"


class ResourceStatus(Enum):
    INITIAL = 1
    RELEASE_BRANCH_LOCAL = 2
    RELEASE_BRANCH_REMOTE = 3
    UPCOMING_VERSION_LOCAL = 4
    UPCOMING_VERSION_REMOTE = 5
    PULL_REQUEST_CREATED = 6


def get_minor_version(version: str) -> str:
    project_version_details = get_version_details(version)
    return f'{project_version_details["major"]}.{project_version_details["minor"]}'


def update_release(github_token: str, project_name: str, project_version: is_version(str), main_branch: str,
                   earliest_pr_date: datetime, exec_path: str, is_test: bool = False,
                   cherry_pick_enabled: bool = False) -> Tuple[str, str, str, ResourceStatus]:
    multi_extension_sql_path = f"{exec_path}/{MULTI_EXTENSION_SQL}"
    citus_control_file_path = f"{exec_path}/{CITUS_CONTROL}"
    multi_extension_out_path = f"{exec_path}/{MULTI_EXTENSION_OUT}"
    configure_in_path = f"{exec_path}/{CONFIGURE_IN}"
    config_py_path = f"{exec_path}/{CONFIG_PY}"
    distributed_dir_path = f"{exec_path}/{DISTRIBUTED_DIR_PATH}"

    resource_status = ResourceStatus.INITIAL

    project_version_details = get_version_details(project_version)
    default_upcoming_version = get_default_upcoming_version(project_version)
    upcoming_version = os.getenv("UPCOMING_VERSION", default=default_upcoming_version)
    upcoming_minor_version = get_minor_version(upcoming_version)
    devel_version = f"{upcoming_minor_version}devel"

    release_branch_name = f'release-{project_version_details["major"]}.{project_version_details["minor"]}'
    release_branch_name = f"{release_branch_name}-test" if is_test else release_branch_name
    upcoming_version_branch = f"master-update-version-{uuid.uuid4()}"

    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{project_name}")
    newly_created_sql_file = ""

    # if major release
    if is_major_release(project_version):
        print(f"### {project_version} is a major release. Executing Major release flow### ")
        # create release-X-Y branch
        print(f"### Preparing {release_branch_name}...### ")
        # checkout master
        checkout_branch(main_branch, is_test)
        # create release branch in release-X.Y format
        create_branch(release_branch_name)
        resource_status = ResourceStatus.RELEASE_BRANCH_LOCAL
        # change version info in configure.in file
        update_version_in_configure_in(configure_in_path, devel_version)

        # execute "autoconf -f"
        execute_autoconf_f()
        # change version info in multi_extension.out
        update_version_in_multi_extension_out(multi_extension_out_path, devel_version)
        # commit all changes
        commit_all_changes_on_branch(project_name, project_version, release_branch_name)
        # push release branch (No PR creation!!!)
        if not is_test:
            push_branch(release_branch_name)
            resource_status = ResourceStatus.RELEASE_BRANCH_REMOTE
        print(f"### OK {release_branch_name} prepared.### ")
        # Increase version number and change upcoming version

        print(f"### Preparing upcoming version branch for the new master with name {upcoming_version_branch}...### ")
        # checkout master
        checkout_branch(main_branch, is_test)
        # create master-update-version-$curtime branch
        create_branch(upcoming_version_branch)
        resource_status = ResourceStatus.UPCOMING_VERSION_LOCAL
        # update version info with upcoming version on configure.in
        update_version_in_configure_in(configure_in_path, devel_version)
        # update version info with upcoming version on config.py
        update_version_with_upcoming_version_inconfig_py(config_py_path, upcoming_minor_version)
        # execute autoconf -f
        execute_autoconf_f()
        # update version info with upcoming version on multiextension.out
        # TODO May add a special version descriptor to address  lines directly to be replaced
        update_version_in_multi_extension_out(multi_extension_out_path, devel_version)
        # get current schema version from citus.control
        current_schema_version = get_current_schema_from_citus_control(citus_control_file_path)

        # find current schema version info and update it with upcoming version  in multi_extension.sql file
        update_schema_version_with_upcoming_version_in_multi_extension_file(current_schema_version,
                                                                            multi_extension_sql_path,
                                                                            upcoming_minor_version, upcoming_version)
        # find current schema version info and update it with upcoming version  in multi_extension.out file
        update_schema_version_with_upcoming_version_in_multi_extension_file(current_schema_version,
                                                                            multi_extension_out_path,
                                                                            upcoming_minor_version, upcoming_version)
        # create new sql file with the name ">./src/backend/distributed/citus--$current_schema_version--
        # $upcoming_minor_version-1.sql"
        newly_created_sql_file = create_new_upcoming_version_sql_file(current_schema_version, distributed_dir_path,
                                                                      upcoming_minor_version)
        # change version in citus.control file
        update_version_with_upcoming_version_in_citus_control(citus_control_file_path, upcoming_minor_version)
        # commit and push changes on master-update-version-$curtime branch
        commit_all_changes_on_branch(project_name, project_version, upcoming_version_branch)
        if not is_test:
            push_branch(upcoming_version_branch)
            resource_status = ResourceStatus.UPCOMING_VERSION_REMOTE
        # create pull request
        if not is_test:
            create_pull_request_for_upcoming_version_branch(main_branch, repository, upcoming_version,
                                                            upcoming_version_branch)
            resource_status = ResourceStatus.PULL_REQUEST_CREATED
    else:
        print(f"### {project_version} is a patch release. Executing Patch release flow ### ")
        # checkout release branch in release-X.Y format
        checkout_branch(release_branch_name, is_test)

        # change version info in configure.in file
        update_version_in_configure_in(configure_in_path, project_version)
        # execute "auto-conf " (Not with f flag!!!)
        execute_autoconf_f()
        # change version info in multi_extension.out
        update_version_in_multi_extension_out(multi_extension_out_path, project_version)

        if cherry_pick_enabled:
            # list all pr's with backport labels
            list_and_cherrypick_prs_with_backport_labels(earliest_pr_date, main_branch, release_branch_name, repository)

        # commit all-changes
        commit_all_changes_on_branch(project_name, project_version, release_branch_name)
        # create and push release-$minor_version-push-$curTime branch
        release_pr_branch = f"{release_branch_name}_{uuid.uuid4()}"
        create_branch(release_pr_branch)
        if not is_test:
            push_branch(release_pr_branch)
    return release_branch_name, upcoming_version_branch, f"{DISTRIBUTED_DIR_PATH}/{newly_created_sql_file}", \
           resource_status


def list_and_cherrypick_prs_with_backport_labels(earliest_pr_date, main_branch, release_branch_name, repository):
    print(
        f"### Getting all PR with backport label after {datetime.strftime(earliest_pr_date, '%Y.%m.%d %H:%M')}### ")
    all_related_prs = get_prs(repository, earliest_pr_date, main_branch)
    # get commits for selected prs with backport label
    prs_with_backport = get_prs_by_label(all_related_prs, "backport")
    print(f"### OK {len(prs_with_backport)} PRs with backport label found. PR list is as below### ")
    for pr in prs_with_backport:
        print(f"No:{pr.number} Title:{pr.title}\n")
    # cherrypick all commits with backport label
    print(f"Cherry-picking PRs on {release_branch_name}...")
    cherry_pick_prs(prs_with_backport)
    print(f"OK Cherry pick completed for all PRs on branch {release_branch_name}")


def create_pull_request_for_upcoming_version_branch(main_branch, repository, upcoming_version,
                                                    upcoming_version_branch):
    print(f"### Creating pull request for {upcoming_version_branch}### ")
    pr_result = repository.create_pull(title=f"Bump Citus to {upcoming_version}", base=main_branch,
                                       head=upcoming_version_branch, body="")
    print(f"### OK Pull request created. PR Number:{pr_result.number} PR URL: {pr_result.url}### ")


def push_branch(upcoming_version_branch):
    print(f"Pushing changes for {upcoming_version_branch} into remote origin...### ")
    run(f"git push --set-upstream origin {upcoming_version_branch}")
    print(f"### OK Changes pushed for {upcoming_version_branch}### ")


def commit_all_changes_on_branch(project_name, project_version, release_branch):
    print(f"### Committing changes for branch {release_branch}...### ")
    run(f' git commit -a -m "Bump  {project_name} version to  {project_version} "')
    print(f"### OK Changes committed for {release_branch}### ")


def update_version_with_upcoming_version_in_citus_control(citus_control_file_path, upcoming_minor_version):
    print(f"### Updating {citus_control_file_path} file with the upcoming version {upcoming_minor_version}...### ")
    if not replace_line_in_file(citus_control_file_path, CITUS_CONTROL_SEARCH_PATTERN,
                                f"default_version = '{upcoming_minor_version}-1'"):
        raise ValueError(f"{citus_control_file_path} does not have match for version")
    print(f"### OK{citus_control_file_path} file updated with the upcoming version {upcoming_minor_version}...### ")


def update_schema_version_with_upcoming_version_in_multi_extension_file(current_schema_version,
                                                                        multi_extension_sql_path,
                                                                        upcoming_minor_version, upcoming_version):
    print(
        f"### Updating schema version {current_schema_version} on {multi_extension_sql_path} "
        f"file with the upcoming version {upcoming_version}...### ")
    # TODO Append instead of replace may require
    if not replace_line_in_file(multi_extension_sql_path,
                                f"ALTER EXTENSION citus UPDATE TO '{current_schema_version}'",
                                f"ALTER EXTENSION citus UPDATE TO '{upcoming_minor_version}-1';"):
        raise ValueError(f"{multi_extension_sql_path} does not have match for version")
    print(f"### OK Current schema version updated on {multi_extension_sql_path} to {upcoming_minor_version}### ")


def get_current_schema_from_citus_control(citus_control_file_path):
    print(f"### Reading current schema version from  {citus_control_file_path}...### ")
    current_schema_version = get_current_schema_version(citus_control_file_path)
    if len(current_schema_version) == 0:
        raise ValueError("Version info could not be found in citus.control file")
    print(f"### OK Current schema version is {current_schema_version}### ")
    return current_schema_version


def update_version_with_upcoming_version_inconfig_py(config_py_path, upcoming_minor_version):
    print(f"### Updating {config_py_path} file with the upcoming version {upcoming_minor_version}...### ")
    if not replace_line_in_file(config_py_path, "^MASTER_VERSION =*",
                                f"MASTER_VERSION = '{upcoming_minor_version}'"):
        raise ValueError(f"{config_py_path} does not have match for version")
    print(f"### {config_py_path} file updated with the upcoming version {upcoming_minor_version}...### ")


def update_version_in_multi_extension_out(multi_extension_out_path, project_version):
    print(f"### Updating {multi_extension_out_path} file with the project version {project_version}...### ")
    if not replace_line_in_file(multi_extension_out_path, MULTI_EXT_MAJOR_SEARCH_PATTERN,
                                f" {project_version}"):
        raise ValueError(f"{multi_extension_out_path} does not have match for version")
    print(f"### OK {multi_extension_out_path} file is updated with project version {project_version}.### ")


def execute_autoconf_f():
    print(f"### Executing autoconf -f command...### ")
    run("autoconf -f")
    print(f"### OK autoconf -f executed.### ")


def update_version_in_configure_in(configure_in_path, project_version):
    print(f"### Updating version on file {configure_in_path}...### ")
    if not replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN,
                                f"AC_INIT([Citus], [{project_version}])"):
        raise ValueError(f"{configure_in_path} does not have match for version")
    print(f"### OK {configure_in_path} file is updated with project version {project_version}.### ")


def create_branch(release_branch_name):
    print(f"### Creating release branch with name {release_branch_name}...### ")
    run(f'git checkout -b {release_branch_name}')
    print(f"### OK {release_branch_name} created### ")


def checkout_branch(branch_name, is_test):
    print(f"### Checking out {branch_name}...### ")
    run(f"git checkout {branch_name}")
    if not is_test:
        run(f"git pull")
    print(f"### OK {branch_name} checked out and pulled### ")


def create_new_upcoming_version_sql_file(current_schema_version, distributed_dir_path,
                                         upcoming_minor_version):
    newly_created_sql_file = f"citus--{current_schema_version}--{upcoming_minor_version}-1.sql"
    print(f"### Creating file {newly_created_sql_file}...### ")
    with open(f"{distributed_dir_path}/{newly_created_sql_file}", "w") as f_writer:
        content = f"/* citus--{current_schema_version}--{upcoming_minor_version}-1 */"
        content = content + "\n\n"
        content = content + f"-- bump version to {upcoming_minor_version}-1" + "\n\n"
        f_writer.write(content)
    run(f"git add {distributed_dir_path}/{newly_created_sql_file}")
    print(f"### OK {newly_created_sql_file} created.")
    return newly_created_sql_file


def get_current_schema_version(citus_control_file_path):
    current_schema_version = ""
    with open(citus_control_file_path, "r") as cc_reader:
        cc_file_content = cc_reader.read()
        cc_lines = cc_file_content.splitlines()
        for cc_line in cc_lines:
            if re.match(CITUS_CONTROL_SEARCH_PATTERN, cc_line):
                line_parts = cc_line.split("=")
                if len(line_parts) > 0:
                    current_schema_version = line_parts[1]
    current_schema_version = current_schema_version.strip(" '")
    return current_schema_version
