import argparse
import os
import uuid

import pathlib2

from .common_tool_methods import (
    get_template_environment,
    process_template_file,
    write_to_file,
    run,
    initialize_env,
    create_pr,
    remove_cloned_code,
)

REPO_OWNER = "citusdata"
PROJECT_NAME = "packaging"
CHECKOUT_DIR = "pgxn_temp"
BASE_PATH = pathlib2.Path(__file__).parent.absolute()
# PostgreSQL 10 and later use <major>.<minor> versions, which PGXN expresses as <major>.0.0.
LOWEST_VALID_POSTGRES_MAJOR = 10


def postgres_min_version(pg_min_major: int) -> str:
    """The PGXN runtime requirement for the lowest PostgreSQL major a Citus release line supports."""
    if (
        isinstance(pg_min_major, bool)
        or not isinstance(pg_min_major, int)
        or pg_min_major < LOWEST_VALID_POSTGRES_MAJOR
    ):
        raise ValueError(
            f"Invalid minimum PostgreSQL major {pg_min_major}; "
            f"expected integer {LOWEST_VALID_POSTGRES_MAJOR} or later."
        )
    return f"{pg_min_major}.0.0"


def update_meta_json(
    project_version: str, template_path: str, exec_path: str, pg_min_major: int
):
    template = get_template_environment(template_path).get_template("META.tmpl.json")
    content = template.render(
        project_version=project_version,
        postgres_min_version=postgres_min_version(pg_min_major),
    )
    write_to_file(f"{content}\n", f"{exec_path}/META.json")


def update_pkgvars(project_version: str, template_path: str, exec_path: str):
    content = process_template_file(project_version, template_path, "pkgvars.tmpl")
    dest_file_name = f"{exec_path}/pkgvars"
    write_to_file(content, dest_file_name)


def update_pgxn_files(
    project_version: str, template_path: str, exec_path: str, pg_min_major: int
):
    update_meta_json(project_version, template_path, exec_path, pg_min_major)
    update_pkgvars(project_version, template_path, exec_path)


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--prj_ver", required=True)
    parser.add_argument(
        "--pg_min_major",
        type=int,
        required=True,
        help="Lowest PostgreSQL major of the Citus release line, written to META.json as <major>.0.0",
    )
    parser.add_argument("--gh_token", required=True)
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument("--exec_path")
    parser.add_argument("--is_test", action="store_true")
    args = parser.parse_args(argv)
    try:
        postgres_min_version(args.pg_min_major)
    except ValueError as error:
        parser.error(str(error))
    return args


if __name__ == "__main__":
    args = parse_arguments()

    github_token = args.gh_token
    main_branch = "pgxn-citus"

    if args.pipeline:
        if not args.exec_path:
            raise ValueError("exec_path should be defined")
        execution_path = args.exec_path
        os.chdir(execution_path)
    else:
        execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
        initialize_env(execution_path, PROJECT_NAME, execution_path)
        os.chdir(execution_path)
        run(f"git checkout {main_branch}")

    pr_branch = f"pgxn-citus-push-{args.prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    template_path = f"{BASE_PATH}/templates/pgxn"
    update_pgxn_files(args.prj_ver, template_path, execution_path, args.pg_min_major)
    commit_message = f"Bump pgxn to version {args.prj_ver}"
    run(f'git commit -a -m "{commit_message}"')
    if not args.is_test:
        run(f"git push --set-upstream origin {pr_branch}")
        create_pr(
            github_token,
            pr_branch,
            commit_message,
            REPO_OWNER,
            PROJECT_NAME,
            main_branch,
        )
    if not args.is_test and not args.pipeline:
        remove_cloned_code(execution_path)
