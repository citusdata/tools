import os
import uuid
import re
from typing import Tuple

from datetime import datetime

from github import Github

from . import common_tool_methods
from . import common_validations
from enum import Enum

MULTI_EXTENSION_SQL = "src/test/regress/sql/multi_extension.sql"
CITUS_CONTROL = "src/backend/distributed/citus.control"
MULTI_EXTENSION_OUT = "src/test/regress/expected/multi_extension.out"
CONFIG_PY = "src/test/regress/upgrade/config.py"
DISTRIBUTED_DIR_PATH = "src/backend/distributed"
CONFIGURE_IN = "configure.in"
CONFIGURE = "configure"
CITUS_CONTROL_SEARCH_PATTERN = r"^default_version*"

MULT_EXT_MAJOR_SEARCH_PATTERN = r"^\s*\d{1,2}\.\d{1,2}devel$"
MULT_EXT_PATCH_SEARCH_PATTERN = r"^\s*\d{1,2}\.\d{1,2}.\d{1,2}$"

CONFIGURE_IN_SEARCH_PATTERN = "AC_INIT*"
REPO_OWNER = "citusdata"


class ResourceStatus(Enum):
    INITIAL = 1
    RELEASE_BRANCH_LOCAL = 2
    RELEASE_BRANCH_REMOTE = 3
    UPCOMING_VERSION_LOCAL = 4
    UPCOMING_VERSION_REMOTE = 5
    PULL_REQUEST_CREATED = 6


def update_release(github_token: str, project_name: str, project_version: common_validations.is_version(str),
                   main_branch: str, earliest_pr_date: datetime, exec_path: str, is_test: bool = False,
                   cherry_pick_enabled: bool = False) -> Tuple[str, str, str, ResourceStatus]:
    multi_extension_sql_path = f"{exec_path}/{MULTI_EXTENSION_SQL}"
    citus_control_file_path = f"{exec_path}/{CITUS_CONTROL}"
    multi_extension_out_path = f"{exec_path}/{MULTI_EXTENSION_OUT}"
    configure_in_path = f"{exec_path}/{CONFIGURE_IN}"
    config_py_path = f"{exec_path}/{CONFIG_PY}"
    distributed_dir_path = f"{exec_path}/{DISTRIBUTED_DIR_PATH}"

    resource_status = ResourceStatus.INITIAL

    project_version_details = common_tool_methods.get_version_details(project_version)
    default_upcoming_version = f'{project_version_details["major"]}.{project_version_details["minor"]}.' \
                               f'{str(int(project_version_details["patch"]) + 1)}'
    upcoming_version = default_upcoming_version if os.getenv("UPCOMING_VERSION") is None else os.getenv(
        "UPCOMING_VERSION")
    upcoming_version_details = common_tool_methods.get_version_details(upcoming_version)
    upcoming_patch_version = f'{upcoming_version_details["major"]}.{upcoming_version_details["minor"]}'
    devel_version = f"{upcoming_patch_version}devel"
    release_branch_name = f'release-{project_version_details["major"]}.{project_version_details["minor"]}'
    release_branch_name = f"{release_branch_name}-test" if is_test else release_branch_name
    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{project_name}")
    newly_created_sql_file = ""
    upcoming_version_branch = f"master-update-version-{uuid.uuid4()}"
    # if major release
    if common_tool_methods.is_major_release(project_version):
        print(f"### {project_version} is a major release. Executing Major release flow### ")
        # create release-X-Y branch
        print(f"### Preparing {release_branch_name}...### ")
        # checkout master
        print(f"### Checking out {main_branch}...### ")
        common_tool_methods.run(f"git checkout {main_branch}")
        common_tool_methods.run(f"git pull")
        print(f"### OK {main_branch} checked out and pulled### ")
        # create release branch in release-X.Y format
        print(f"### Creating release branch with name {release_branch_name}...### ")
        common_tool_methods.run(f'git checkout -b {release_branch_name}')
        print(f"### OK {release_branch_name} created### ")
        resource_status = ResourceStatus.RELEASE_BRANCH_LOCAL
        # change version info in configure.in file
        print(f"### Updating version on file {configure_in_path}...### ")
        if not common_tool_methods.replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN,
                                                        f"AC_INIT([Citus], [{project_version}])"):
            raise ValueError(f"{configure_in_path} does not have match for version")
        print(f"### OK {configure_in_path} file is updated with project version {project_version}.### ")

        # execute "autoconf -f"
        print(f"### Executing autoconf -f command...### ")
        common_tool_methods.run("autoconf -f")
        print(f"### OK autoconf -f executed.### ")
        # change version info in multi_extension.out
        print(f"### Updating version on file {multi_extension_out_path}...### ")
        if not common_tool_methods.replace_line_in_file(multi_extension_out_path, MULT_EXT_MAJOR_SEARCH_PATTERN,
                                                        f" {project_version}"):
            raise ValueError(f"{multi_extension_out_path} does not have match for version")
        print(f"### OK {multi_extension_out_path} file is updated with project version {project_version}.### ")
        # commit all changes
        print(f"### Committing changes for branch {release_branch_name}...### ")
        common_tool_methods.run(f' git commit -a -m "Bump  {project_name} version to  {project_version} "')
        print(f"### OK Changes committed for {release_branch_name}### ")
        # push release branch (No PR creation!!!)
        if not is_test:
            print(f"### Pushing changes for {release_branch_name} into remote origin...### ")
            common_tool_methods.run(f"git push --set-upstream origin {release_branch_name}")
            resource_status = ResourceStatus.RELEASE_BRANCH_REMOTE
            print(f"### OK Changes pushed for {release_branch_name}### ")
        print(f"### OK {release_branch_name} prepared.### ")

        # Increase version number and change upcoming version

        print(f"### Preparing upcoming version branch for the new master with name {upcoming_version_branch}...### ")
        # checkout master
        print(f"### Checking out {main_branch}...### ")
        common_tool_methods.run(f"git checkout {main_branch}")
        print(f"### OK {main_branch} checked out.### ")
        # create master-update-version-$curtime branch
        print(f"### Checking out {upcoming_version_branch}...### ")
        common_tool_methods.run(f"git checkout -b {upcoming_version_branch}")
        print(f"### {upcoming_version_branch} checked out.### ")
        resource_status = ResourceStatus.UPCOMING_VERSION_LOCAL
        # update version info with upcoming version on configure.in
        print(f"### Updating {configure_in_path} file with the upcoming version {devel_version}...### ")
        if not common_tool_methods.replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN,
                                                        f"AC_INIT([Citus], [{devel_version}])"):
            raise ValueError(f"{configure_in_path} does not have match for version")
        print(f"### {configure_in_path} file updated with the upcoming version {devel_version}...### ")
        # update version info with upcoming version on config.py
        print(f"### Updating {config_py_path} file with the upcoming version {upcoming_patch_version}...### ")
        if not common_tool_methods.replace_line_in_file(config_py_path, "^MASTER_VERSION =*",
                                                        f"MASTER_VERSION = '{upcoming_patch_version}'"):
            raise ValueError(f"{config_py_path} does not have match for version")
        print(f"### {config_py_path} file updated with the upcoming version {upcoming_patch_version}...### ")
        # execute autoconf -f
        print(f"### Executing autoconf -f command...### ")
        common_tool_methods.run("autoconf -f")
        print(f"### OK autoconf -f executed.### ")
        # update version info with upcoming version on multiextension.out
        # TODO May add a special version descriptor to address  lines directly to be replaced
        print(f"### Updating {multi_extension_out_path} file with the upcoming version {devel_version}...### ")
        if not common_tool_methods.replace_line_in_file(multi_extension_out_path, MULT_EXT_MAJOR_SEARCH_PATTERN,
                                                        f" {devel_version}"):
            raise ValueError(f"{multi_extension_out_path} does not have match for version")
        print(f"### OK {multi_extension_out_path} file updated with the upcoming version {devel_version}...### ")
        # get current schema version from citus.control
        print(f"### Reading current schema version from  {citus_control_file_path}...### ")
        current_schema_version = get_current_schema_version(citus_control_file_path)
        if len(current_schema_version) == 0:
            raise ValueError("Version info could not be found in citus.control file")

        print(f"### OK Current schema version is {current_schema_version}### ")

        # find current schema version info and update it with upcoming version  in multi_extension.sql file
        print(
            f"### Updating schema version {current_schema_version} on {multi_extension_sql_path} "
            f"file with the upcoming version {upcoming_version}...### ")
        # TODO Append instead of replace may require
        if not common_tool_methods.replace_line_in_file(multi_extension_sql_path,
                                                        f"ALTER EXTENSION citus UPDATE TO '{current_schema_version}'",
                                                        f"ALTER EXTENSION citus UPDATE TO '{upcoming_patch_version}-1';"):
            raise ValueError(f"{multi_extension_sql_path} does not have match for version")
        print(f"### OK Current schema version updated on {multi_extension_sql_path} to {upcoming_patch_version}### ")
        # find current schema version info and update it with upcoming version  in multi_extension.out file
        print(
            f"### Updating schema version {current_schema_version} on {multi_extension_out_path} "
            f"file with the upcoming version {upcoming_version}...### ")
        if not common_tool_methods.replace_line_in_file(multi_extension_out_path,
                                                        f"ALTER EXTENSION citus UPDATE TO '{current_schema_version}'",
                                                        f"ALTER EXTENSION citus UPDATE TO '{upcoming_patch_version}-1';"):
            raise ValueError(f"{multi_extension_out_path} does not have match for version")
        print(f"### OK Current schema version updated on {multi_extension_out_path} to {upcoming_patch_version}### ")
        # create new sql file with the name ">./src/backend/distributed/citus--$current_schema_version--
        # $upcoming_minor_version-1.sql"
        newly_created_sql_file = f"citus--{current_schema_version}--{upcoming_patch_version}-1.sql"
        print(f"### Creating file {newly_created_sql_file}...### ")
        with open(f"{distributed_dir_path}/{newly_created_sql_file}", "w") as f_writer:
            content = f"/* citus--{current_schema_version}--{upcoming_patch_version}-1 */"
            content = content + "\n\n"
            content = content + f"-- bump version to {upcoming_patch_version}-1" + "\n\n"
            f_writer.write(content)
        common_tool_methods.run(f"git add {distributed_dir_path}/{newly_created_sql_file}")
        print(f"### OK {newly_created_sql_file} created.")
        # change version in citus.control file
        print(f"### Updating {citus_control_file_path} file with the upcoming version {upcoming_patch_version}...### ")
        if not common_tool_methods.replace_line_in_file(citus_control_file_path, CITUS_CONTROL_SEARCH_PATTERN,
                                                        f"default_version = '{upcoming_patch_version}-1'"):
            raise ValueError(f"{citus_control_file_path} does not have match for version")
        print(f"### OK{citus_control_file_path} file updated with the upcoming version {upcoming_patch_version}...### ")
        # commit and push changes on master-update-version-$curtime branch
        print(f"### Committing changes for branch {upcoming_version_branch}...### ")
        common_tool_methods.run(f'git commit -a -m "Bump {project_name} version to {project_version}"')
        print(f"### OK Changes committed for {upcoming_version_branch}")
        if not is_test:
            print(f"Pushing changes for {upcoming_version_branch} into remote origin...### ")
            common_tool_methods.run(f"git push --set-upstream origin {upcoming_version_branch}")
            resource_status = ResourceStatus.UPCOMING_VERSION_REMOTE
            print(f"### OK Changes pushed for {upcoming_version_branch}### ")
        # create pull request
        if not is_test:
            print(f"### Creating pull request for {upcoming_version_branch}### ")
            pr_result = repository.create_pull(title=f"Bump Citus to {upcoming_version}", base=main_branch,
                                               head=upcoming_version_branch, body="")
            print(f"### OK Pull request created. PR Number:{pr_result.number} PR URL: {pr_result.url}### ")
            resource_status = ResourceStatus.PULL_REQUEST_CREATED
    else:
        print(f"### {project_version} is a patch release. Executing Patch release flow ### ")
        # checkout release branch in release-X.Y format
        print(f"### Checking out {release_branch_name}...### ")
        common_tool_methods.run(f'git checkout {release_branch_name}')
        print(f"### OK {release_branch_name} checked out### ")

        # change version info in configure.in file
        print(f"### Updating {configure_in_path} file with the project version {project_version}...### ")
        if not common_tool_methods.replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN,
                                                        f"AC_INIT([Citus], [{project_version}])"):
            raise ValueError(f"{configure_in_path} does not have match for version")
        print(f"### OK {configure_in_path} file is updated with project version {project_version}.### ")
        # execute "auto-conf " (Not with f flag!!!)
        print(f"### Executing autoconf command...### ")
        common_tool_methods.run("autoconf -f")
        print(f"### OK autoconf executed.### ")
        # change version info in multi_extension.out
        print(f"### Updating {multi_extension_out_path} file with the project version {project_version}...### ")
        if not common_tool_methods.replace_line_in_file(multi_extension_out_path, MULT_EXT_PATCH_SEARCH_PATTERN,
                                                        f" {project_version}"):
            raise ValueError(f"{multi_extension_out_path} does not have match for version")
        print(f"### OK {multi_extension_out_path} file is updated with project version {project_version}.### ")

        if cherry_pick_enabled:
            # list all pr's with backport labels
            print(
                f"### Getting all PR with backport label after {datetime.strftime(earliest_pr_date, '%Y.%m.%d %H:%M')}### ")
            all_related_prs = common_tool_methods.get_prs(repository, earliest_pr_date, main_branch)
            # get commits for selected prs with backport label
            prs_with_backport = common_tool_methods.get_pr_issues_by_label(all_related_prs, "backport")
            print(f"### OK {len(prs_with_backport)} PRs with backport label found. PR list is as below### ")
            for pr in prs_with_backport:
                print(f"No:{pr.number} Title:{pr.title}\n")
            # cherrypick all commits with backport label

            print(f"Cherry-picking PRs on {release_branch_name}...")
            common_tool_methods.cherry_pick_prs(prs_with_backport)
            print(f"OK Cherry pick completed for all PRs on branch {release_branch_name}")
            # commit all-changes

        print(f"### Committing changes for branch {release_branch_name}...### ")
        common_tool_methods.run(f'git commit -a -m "{project_name} version to {project_version}"')
        print(f"### OK Changes committed for {release_branch_name}### ")
        # create and push release-$minor_version-push-$curTime branch
        if not is_test:
            print(f"### Pushing changes for {release_branch_name} into remote origin...### ")
            common_tool_methods.run(f"git push --set-upstream origin {release_branch_name}")
            resource_status = ResourceStatus.UPCOMING_VERSION_REMOTE
            print(f"### OK Changes pushed for {release_branch_name}### ")
    return release_branch_name, upcoming_version_branch, f"{DISTRIBUTED_DIR_PATH}/{newly_created_sql_file}", \
           resource_status


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
