import argparse
import uuid
from . import common_tool_methods
from github import Github



REPO_OWNER = "citusdata"
PROJECT_NAME = "packaging"


def update_meta_json(project_version: str, template_path: str, exec_path: str):
    content = common_tool_methods.process_docker_template_file(project_version, template_path,
                                                               "META.tmpl.json")
    dest_file_name = f"{exec_path}/META.json"
    common_tool_methods.write_to_file(content, dest_file_name)


def update_pkgvars(project_version: str, template_path: str, exec_path: str):
    content = common_tool_methods.process_docker_template_file(project_version, template_path,
                                                               "pkgvars.tmpl")
    dest_file_name = f"{exec_path}/pkgvars"
    common_tool_methods.write_to_file(content, dest_file_name)


def update_pgxn_files(project_version: str, template_path: str, exec_path: str):
    update_meta_json(project_version, template_path, exec_path)
    update_pkgvars(project_version, template_path, exec_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver')
    parser.add_argument('--exec_path')
    parser.add_argument('--tools_path')
    parser.add_argument('--gh_token')
    args = parser.parse_args()

    execution_path = args.exec_path
    tool_path = args.tools_path
    github_token = args.gh_token
    main_branch = "pgxn-citus"

    print(f"Exec Path: {execution_path}")

    if github_token is None or github_token == "":
        raise ValueError("Github Token should be provided")
    if execution_path is None or execution_path == "":
        raise ValueError("Execution Path should be provided")
    if tool_path is None or tool_path == "":
        tool_path = f"{execution_path}/tools"
        print(f"Tools path is not provided. Default value is set: {tool_path}")

    common_tool_methods.run(f"git checkout {main_branch}")
    pr_branch = f"pgxn-citus-push-{args.prj_ver}-{uuid.uuid4()}"
    common_tool_methods.run(f"git checkout -b {pr_branch}")
    template_path = f"{tool_path}/packaging_automation/templates/pgxn"
    update_pgxn_files(args.prj_ver, template_path, execution_path)

    common_tool_methods.run(f'git commit -a -m "Bump to version {args.prj_ver}"')
    common_tool_methods.run(f'git push --set-upstream origin {pr_branch}')

    g = Github(github_token)
    repository = g.get_repo(f"{REPO_OWNER}/{PROJECT_NAME}")

    pr_result = repository.create_pull(title=f"Bump Citus to {args.prj_ver}", base=main_branch,
                                       head=pr_branch, body="")
