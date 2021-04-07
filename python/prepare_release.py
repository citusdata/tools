import os

from github import Github
import uuid

from .common_tool_methods import *

MULTI_EXTENSION_SQL = "src/test/regress/sql/multi_extension.sql"
CITUS_CONTROL = "src/backend/distributed/citus.control"
MULTI_EXTENSION_OUT = "src/test/regress/expected/multi_extension.out"
CONFIG_PY = "src/test/regress/upgrade/config.py"
DISTRIBUTED_DIR_PATH = "src/backend/distributed"
CONFIGURE_IN = "configure.in"
CITUS_CONTROL_SEARCH_PATTERN = r"^default_version*"

MULT_EXT_SEARCH_PATTERN = r"^\d{1,2}\.\d{1,2}devel$"
CONFIGURE_IN_SEARCH_PATTERN = "AC_INIT*"
REPO_OWNER = "citusdata"


def update_release(github_token: str, project_name: str, project_version: is_version(str), main_branch: str,
                   earliest_pr_date: datetime, exec_path: str):
    multi_extension_sql_path = f"{exec_path}/{MULTI_EXTENSION_SQL}"
    citus_control_file_path = f"{exec_path}/{CITUS_CONTROL}"
    multi_extension_out_path = f"{exec_path}/{MULTI_EXTENSION_OUT}"
    configure_in_path = f"{exec_path}/{CONFIGURE_IN}"
    config_py_path = f"{exec_path}/{CONFIG_PY}"
    distributed_dir_path = f"{exec_path}/{DISTRIBUTED_DIR_PATH}"

    project_version_details = get_version_details(project_version)
    default_upcoming_version = f'{project_version_details["major"]}.{project_version_details["minor"]}.' \
                               f'{str(int(project_version_details["patch"]) + 1)}'
    upcoming_version = default_upcoming_version if os.getenv("UPCOMING_VERSION") is None else os.getenv(
        "UPCOMING_VERSION")
    upcoming_version_details = get_version_details(upcoming_version)
    upcoming_minor_version = f'{upcoming_version_details["major"]}.{upcoming_version_details["minor"]}'
    release_branch_name = f'release-test-{project_version_details["major"]}.{project_version_details["minor"]}'
    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{project_name}")

    # if major release
    if is_major_release(project_version):
        print(f"{project_version} is a major release. Executing Major release flow ")
        # create release-X-Y branch
        print(f"Preparing {release_branch_name}...")
        # checkout master
        print(f"Checking out {main_branch}...")
        run(f"git checkout {main_branch}")
        run(f"git pull")
        print(f"OK {main_branch} checked out and pulled")
        # create release branch in release-X.Y format
        print(f"Creating release branch with name {release_branch_name}...")
        run(f'git checkout -b {release_branch_name}')
        print(f"OK {release_branch_name} created")
        # change version info in configure.in file
        print(f"Updating version on file {configure_in_path}...")
        replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN, f"AC_INIT([Citus], [{project_version}])")
        print(f"OK {configure_in_path} file is updated with project version {project_version}.")
        # update_configure_in(project_version)

        # execute "autoconf -f"
        print(f"Executing autoconf -f command...")
        run("autoconf -f")
        print(f"OK autoconf -f executed.")
        # change version info in multi_extension.out
        print(f"Updating version on file {multi_extension_out_path}...")
        replace_line_in_file(multi_extension_out_path, MULT_EXT_SEARCH_PATTERN,
                             f"{project_version}")
        print(f"OK {multi_extension_out_path} file is updated with project version {project_version}.")
        # commit all changes
        print(f"Committing changes for branch {release_branch_name}...")
        run(f' git commit -am "Bump  {project_name} version to  {project_version} "')
        print(f"OK Changes committed for {release_branch_name}")
        # push release branch (No PR creation!!!)
        print(f"Pushing changes for {release_branch_name} into remote origin...")
        run(f"git push --set-upstream origin {release_branch_name}")
        print(f"OK Changes pushed for {release_branch_name}")
        print(f"OK {release_branch_name} prepared.")
        # Increase version number and change upcoming version
        upcoming_version_branch = f"master-update-version-{uuid.uuid4()}"
        print(f"Preparing upcoming version branch for the new master with name {upcoming_version_branch}...")
        # checkout master
        print(f"Checking out {main_branch}...")
        run(f"git checkout {main_branch}")
        print(f"OK {main_branch} checked out.")
        # create master-update-version-$curtime branch
        print(f"Checking out {upcoming_version_branch}...")
        run(f"git checkout -b {upcoming_version_branch}")
        print(f"{upcoming_version_branch} checked out.")
        # update version info with upcoming version on configure.in
        print(f"Updating {configure_in_path} file with the upcoming version {upcoming_version}...")
        replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN, f"AC_INIT([Citus], [{upcoming_version}])")
        print(f"U{configure_in_path} file updated with the upcoming version {upcoming_version}...")
        # update version info with upcoming version on config.py
        print(f"Updating {config_py_path} file with the upcoming version {upcoming_minor_version}...")
        replace_line_in_file(config_py_path, "^MASTER_VERSION =*",
                             f'MASTER_VERSION = {upcoming_minor_version}')
        print(f"U{config_py_path} file updated with the upcoming version {upcoming_minor_version}...")
        # execute autoconf -f
        print(f"Executing autoconf -f command...")
        run("autoconf -f")
        print(f"OK autoconf -f executed.")
        # update version info with upcoming version on multiextension.out
        # TODO May add a special version descriptor to address  lines directly to be replaced
        print(f"Updating {multi_extension_out_path} file with the upcoming version {upcoming_version}...")
        replace_line_in_file(multi_extension_out_path, MULT_EXT_SEARCH_PATTERN,
                             f"{upcoming_version}")
        print(f"U{multi_extension_out_path} file updated with the upcoming version {upcoming_version}...")
        # get current schema version from citus.control
        print(f"Reading current schema version from  {citus_control_file_path}...")
        current_schema_version = ""
        with open(citus_control_file_path, "r") as cc_reader:
            cc_file_content = cc_reader.read()
            cc_lines = cc_file_content.splitlines()
            for cc_line in cc_lines:
                if re.match(CITUS_CONTROL_SEARCH_PATTERN, cc_line):
                    current_schema_version = cc_line

        if len(current_schema_version) == 0:
            raise ValueError("Version info could not be found in citus.control file")

        print(f"OK Current schema version is {current_schema_version}")

        # find current schema version info and update it with upcoming version  in multi_extension.sql file
        print(
            f"Updating schema version {current_schema_version} on {multi_extension_sql_path} "
            f"file with the upcoming version {upcoming_version}...")
        replace_line_in_file(multi_extension_sql_path,
                             f"ALTER EXTENSION citus UPDATE TO {current_schema_version}",
                             f"ALTER EXTENSION citus UPDATE TO {upcoming_minor_version}")
        print(f"OK Current schema version updated on {multi_extension_sql_path} to {upcoming_minor_version}")
        # find current schema version info and update it with upcoming version  in multi_extension.out file
        print(
            f"Updating schema version {current_schema_version} on {multi_extension_out_path} "
            f"file with the upcoming version {upcoming_version}...")
        replace_line_in_file(multi_extension_out_path,
                             f"ALTER EXTENSION citus UPDATE TO {current_schema_version}",
                             f"ALTER EXTENSION citus UPDATE TO {upcoming_minor_version}")
        print(f"OK Current schema version updated on {multi_extension_out_path} to {upcoming_minor_version}")
        # create new sql file with the name ">./src/backend/distributed/citus--$current_schema_version--
        # $upcoming_minor_version-1.sql"
        newly_created_sql_file = f"citus--{current_schema_version}--{upcoming_minor_version}-1.sql"
        print(f"Creating file {newly_created_sql_file}...")
        with open(f"{distributed_dir_path}/{newly_created_sql_file}", "w") as f_writer:
            content = f"/* citus--{current_schema_version}--{upcoming_minor_version}-1 */"
            content = content + "\n\n"
            content = content + f"-- bump version to {upcoming_minor_version}-1" + "\n\n"
            f_writer.write(content)
        print(f"{newly_created_sql_file} created.")
        # change version in citus.control file
        print(f"Updating {citus_control_file_path} file with the upcoming version {upcoming_minor_version}...")
        replace_line_in_file(citus_control_file_path, CITUS_CONTROL_SEARCH_PATTERN,
                             f"default_version={upcoming_minor_version}-1")
        print(f"U{citus_control_file_path} file updated with the upcoming version {upcoming_minor_version}...")
        # commit and push changes on master-update-version-$curtime branch
        print(f"Committing changes for branch {upcoming_version_branch}...")
        run(f'git commit -am "{project_name} version to {project_version}"')
        print(f"OK Changes committed for {upcoming_version_branch}")
        print(f"Pushing changes for {upcoming_version_branch} into remote origin...")
        run(f"git push --set-upstream origin {upcoming_version_branch}")
        print(f"OK Changes pushed for {upcoming_version_branch}")
        # create pull request
        print(f"Creating pull request for {upcoming_version_branch}")
        pr_result = repository.create_pull(title=f"Bump Citus to {upcoming_version}", base=main_branch,
                                           head=upcoming_version_branch, body="")
        print(f"OK Pull request created. PR Number:{pr_result.number} PR URL: {pr_result.url}")
    else:
        print(f"{project_version} is a patch release. Executing Patch release flow ")
        # checkout release branch in release-X.Y format
        print(f"Checking out {release_branch_name}...")
        run(f'git checkout {release_branch_name}')
        print(f"{release_branch_name} checked out")
        # list all pr's with backport labels
        print(f"Getting all PR with backport label after {datetime.strftime(earliest_pr_date, '%Y.%m.%d %H:%M')}")
        all_related_prs = get_prs(repository, earliest_pr_date, main_branch)
        # get commits for selected prs with backport label
        prs_with_backport = get_pr_issues_by_label(all_related_prs, "backport")
        print(f"OK {len(prs_with_backport)} PRs with backport label found. PR list is as below")
        for pr in prs_with_backport:
            print(f"No:{pr.number} Title:{pr.title}\n")

        # cherrypick all commits with backport label

        print(f"Cherry-picking PRs on {release_branch_name}...")
        cherry_pick_prs(prs_with_backport)
        print(f"OK Cherry pick completed for all PRs on branch {release_branch_name}")
        # change version info in configure.in file

        replace_line_in_file(configure_in_path, CONFIGURE_IN_SEARCH_PATTERN, f"AC_INIT([Citus], [{project_version}])")
        # execute "auto-conf " (Not with f flag!!!)
        run("autoconf")
        # change version info in multi_extension.out
        print(f"Updating {multi_extension_out_path} file with the project version {project_version}...")
        replace_line_in_file(multi_extension_out_path, MULT_EXT_SEARCH_PATTERN,
                             f"{project_version}")
        print(f"OK {multi_extension_out_path} file is updated with project version {project_version}.")
        # commit all-changes
        print(f"Committing changes for branch {release_branch_name}...")
        run(f'git commit -am "{project_name} version to {project_version}"')
        print(f"OK Changes committed for {release_branch_name}")
        # create and push release-$minor_version-push-$curTime branch
        print(f"Pushing changes for {release_branch_name} into remote origin...")
        run(f"git push --set-upstream origin {release_branch_name}")
        print(f"OK Changes pushed for {release_branch_name}")
