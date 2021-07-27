import argparse
import os
import uuid

from .common_tool_methods import (process_template_file, write_to_file, run, initialize_env, create_pr)

REPO_OWNER = "citusdata"
PROJECT_NAME = "packaging"
CHECKOUT_DIR = "pgxn_temp"


def update_meta_json(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path,
                                    "META.tmpl.json")
    dest_file_name = f"{exec_path}/META.json"
    write_to_file(content, dest_file_name)


def update_pkgvars(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path,
                                    "pkgvars.tmpl")
    dest_file_name = f"{exec_path}/pkgvars"
    write_to_file(content, dest_file_name)


def update_pgxn_files(project_version: str, template_path: str, exec_path: str):
    update_meta_json(project_version, template_path, exec_path)
    update_pkgvars(project_version, template_path, exec_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver', required=True)
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--is_test', action="store_true")
    args = parser.parse_args()

    execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
    github_token = args.gh_token
    main_branch = "pgxn-citus"

    tools_path = os.getcwd()
    initialize_env(execution_path, PROJECT_NAME, CHECKOUT_DIR)
    os.chdir(execution_path)

    run(f"git checkout {main_branch}")
    pr_branch = f"pgxn-citus-push-{args.prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    template_path = f"{tools_path}/packaging_automation/templates/pgxn"
    update_pgxn_files(args.prj_ver, template_path, execution_path)
    commit_message = f"Bump pgxn to version {args.prj_ver}"
    run(f'git commit -a -m "{commit_message}"')
    if not args.is_test:
        run(f'git push --set-upstream origin {pr_branch}')

    if not args.is_test:
        create_pr(github_token, pr_branch, commit_message, REPO_OWNER, PROJECT_NAME, main_branch)
