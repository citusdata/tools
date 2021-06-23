import argparse
import uuid
from .common_tool_methods import (process_template_file, write_to_file, run)
from github import Github

REPO_OWNER = "citusdata"
PROJECT_NAME = "packaging"


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
    parser.add_argument('--exec_path', required=True)
    parser.add_argument('--tools_path')
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--is_test', action="store_true")
    args = parser.parse_args()

    execution_path = args.exec_path
    tool_path = args.tools_path
    github_token = args.gh_token
    main_branch = "pgxn-citus"

    print(f"Exec Path: {execution_path}")

    if not github_token:
        raise ValueError("Github Token should be provided")
    if not execution_path:
        raise ValueError("Execution Path should be provided")
    if not tool_path:
        tool_path = f"{execution_path}/tools"
        print(f"Tools path is not provided. Default value is set: {tool_path}")

    run(f"git checkout {main_branch}")
    pr_branch = f"pgxn-citus-push-{args.prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    template_path = f"{tool_path}/packaging_automation/templates/pgxn"
    update_pgxn_files(args.prj_ver, template_path, execution_path)

    run(f'git commit -a -m "Bump to version {args.prj_ver}"')
    if not args.is_test:
        run(f'git push --set-upstream origin {pr_branch}')

    if not args.is_test:
        g = Github(github_token)
        repository = g.get_repo(f"{REPO_OWNER}/{PROJECT_NAME}")
        pr_result = repository.create_pull(title=f"Bump Citus to {args.prj_ver}", base=main_branch,
                                           head=pr_branch, body="")
