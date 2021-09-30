import os
import re
import shlex
import subprocess
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple

import base64
import git
import gnupg
import pathlib2
import requests
from git import GitCommandError, Repo
from github import Commit, Github, PullRequest, Repository
from jinja2 import Environment, FileSystemLoader
from parameters_validation import validate_parameters

from .common_validations import (is_tag, is_version)
from .dbconfig import RequestLog, RequestType

BASE_GIT_PATH = pathlib2.Path(__file__).parents[1]
PATCH_VERSION_MATCH_FROM_MINOR_SUFFIX = r"\.\d{1,3}"

# http://python-notes.curiousefficiency.org/en/latest/python3/text_file_processing.html
# https://bleepcoder.com/pylint/698183789/pep-597-require-encoding-kwarg-in-open-call-and-other-calls
# Parameterized to fix pylint unspecified-encoding error
DEFAULT_ENCODING_FOR_FILE_HANDLING = "utf8"
DEFAULT_UNICODE_ERROR_HANDLER = "surrogateescape"

# When using GitPython library Repo objects should be closed to be able to delete cloned sources
# referenced by Repo objects.References are stored in below array to be able to close
# all resources after the code execution.
referenced_repos: List[Repo] = []


def get_new_repo(working_dir: str) -> Repo:
    repo = Repo(working_dir)
    referenced_repos.append(repo)
    return repo


def release_all_repos():
    for repo in referenced_repos:
        repo.close()


class PackageType(Enum):
    deb = 1
    rpm = 2


class GpgKeyType(Enum):
    private = 1
    public = 2


BASE_PATH = pathlib2.Path(__file__).parents[1]


def get_spec_file_name(project_name: str) -> str:
    return f"{project_name}.spec"


def get_minor_project_version(project_version: str) -> str:
    project_version_details = get_version_details(project_version)
    return f'{project_version_details["major"]}.{project_version_details["minor"]}'


def append_fancy_suffix_to_version(version: str, fancy_release_number: int) -> str:
    fancy_suffix = f"-{fancy_release_number}"
    return f"{version}{fancy_suffix}"


def append_project_name_to_version(project_name: str, version: str) -> str:
    return f"{version}.{project_name}"


def get_project_version_from_tag_name(tag_name: is_tag(str)) -> str:
    return tag_name[1:]


def get_template_environment(template_dir: str) -> Environment:
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    return env


def find_nth_occurrence_position(subject_string: str, search_string: str, n) -> int:
    start = subject_string.find(search_string)

    while start >= 0 and n > 1:
        start = subject_string.find(search_string, start + 1)
        n -= 1
    return start


def find_nth_matching_line_and_line_number(subject_string: str, regex_pattern: str, n: int) -> Tuple[int, str]:
    """Takes a subject string, regex param and the search index as parameter and returns line number of found match.
    If not found returns -1"""
    lines = subject_string.splitlines()
    counter = 0
    for line_number, line in enumerate(lines):
        if re.match(regex_pattern, line):
            counter = counter + 1
        if counter == n:
            return line_number, lines[line_number]
    return -1, ""


def remove_text_with_parenthesis(param: str) -> str:
    """Removes texts within parenthesis i.e. outside parenthesis(inside parenthesis)-> outside parenthesis """
    return re.sub(r"[(\[].*?[)\]]", "", param)


def run(command, *args, **kwargs):
    result = subprocess.run(shlex.split(command), *args, check=True, **kwargs)
    return result


def run_with_output(command, *args, **kwargs):
    # this method's main objective is to return output. Therefore it is caller's responsibility to handle
    # success status
    # pylint: disable=subprocess-run-check
    result = subprocess.run(shlex.split(command), *args, capture_output=True, **kwargs)
    return result


def cherry_pick_prs(prs: List[PullRequest.PullRequest]):
    for pr in prs:
        commits = pr.get_commits()
        for single_commit in commits:
            if not is_merge_commit(single_commit):
                cp_result = run(f"git cherry-pick -x {single_commit.commit.sha}")
                print(
                    f"Cherry pick result for PR no {pr.number} and commit sha {single_commit.commit.sha}: {cp_result}")


def get_minor_version(version: str) -> str:
    project_version_details = get_version_details(version)
    return f'{project_version_details["major"]}.{project_version_details["minor"]}'


@validate_parameters
def get_patch_version_regex(version: is_version(str)):
    return fr"^{re.escape(get_minor_version(version))}{PATCH_VERSION_MATCH_FROM_MINOR_SUFFIX}$"


def is_merge_commit(commit: Commit):
    return len(commit.parents) <= 1


@validate_parameters
def get_version_details(version: is_version(str)) -> Dict[str, str]:
    version_parts = version.split(".")
    return {"major": version_parts[0], "minor": version_parts[1], "patch": version_parts[2]}


@validate_parameters
def get_upcoming_patch_version(version: is_version(str)) -> str:
    project_version_details = get_version_details(version)
    return f'{get_upcoming_minor_version(version)}.{int(project_version_details["patch"]) + 1}'


@validate_parameters
def get_upcoming_minor_version(version: is_version(str)) -> str:
    project_version_details = get_version_details(version)
    return f'{project_version_details["major"]}.{int(project_version_details["minor"]) + 1}'


def get_last_commit_message(path: str) -> str:
    repo = get_new_repo(path)
    commit = repo.head.commit
    return commit.message


@validate_parameters
def is_major_release(version: is_version(str)) -> bool:
    version_info = get_version_details(version)
    return version_info["patch"] == "0"


def str_array_to_str(str_array: List[str]) -> str:
    return f"{os.linesep.join(str_array)}{os.linesep}"


def get_prs_for_patch_release(repo: Repository.Repository, earliest_date: datetime, base_branch: str,
                              last_date: datetime = None):
    pull_requests = repo.get_pulls(state="closed", base=base_branch, sort="created", direction="desc")

    # filter pull requests according to given time interval
    filtered_pull_requests = []
    for pull_request in pull_requests:
        # FIXME: We hit to API rate limit when using `.merged`, so we use `.merged_at` here
        if not pull_request.merged_at:
            continue
        if pull_request.merged_at < earliest_date:
            continue
        if last_date and pull_request.merged_at > last_date:
            continue

        filtered_pull_requests.append(pull_request)

    # finally, sort the pr's by their merge date
    sorted_pull_requests = sorted(filtered_pull_requests, key=lambda p: p.merged_at)
    return sorted_pull_requests


def filter_prs_by_label(prs: List[PullRequest.PullRequest], label_name: str):
    filtered_prs = []
    for pr in prs:
        if any(label.name == label_name for label in pr.labels):
            filtered_prs.append(pr)
    return filtered_prs


def file_includes_line(base_path: str, relative_file_path: str, line_content: str) -> bool:
    with open(f"{base_path}/{relative_file_path}", "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        content = reader.read()
        lines = content.splitlines()
        for line in lines:
            if line == line_content:
                return True
    return False


def count_line_in_file(base_path: str, relative_file_path: str, search_line: str) -> int:
    with open(f"{base_path}/{relative_file_path}", "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        content = reader.read()
        lines = content.splitlines()
    return len(list(filter(lambda line: line == search_line, lines)))


def replace_line_in_file(file: str, match_regex: str, replace_str: str) -> bool:
    with open(file, "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING, errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        file_content = reader.read()
        lines = file_content.splitlines()
        has_match = False
        for line_number, line in enumerate(lines):
            if re.match(match_regex, line.strip()):
                has_match = True
                lines[line_number] = replace_str
        edited_content = str_array_to_str(lines)
    with open(file, "w", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING, errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        writer.write(edited_content)

    return has_match


def append_line_in_file(file: str, match_regex: str, append_str: str) -> bool:
    with open(file, "r+", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING, errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        file_content = reader.read()
        lines = file_content.splitlines()
        has_match = False
        copy_lines = lines.copy()
        appended_line_index = 0
        for line_number, line in enumerate(lines):
            if re.match(match_regex, line.strip()):
                has_match = True

                if line_number + 1 < len(lines):
                    copy_lines[appended_line_index + 1] = append_str
                    # Since line is added after matched string, shift index start with line_number+1
                    # increment of appended_line_index is 2 since copy_lines appended_line_index+1 includes
                    # append_str
                    lines_to_be_shifted = lines[line_number + 1:]
                    copy_lines = copy_lines[0:appended_line_index + 2] + lines_to_be_shifted
                else:
                    copy_lines.append(append_str)
            appended_line_index = appended_line_index + 1
        edited_content = str_array_to_str(copy_lines)
    with open(file, "w", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING, errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        writer.write(edited_content)

    return has_match


def prepend_line_in_file(file: str, match_regex: str, append_str: str) -> bool:
    with open(file, "r+", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING, errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        file_content = reader.read()
        lines = file_content.splitlines()
        has_match = False
        copy_lines = lines.copy()
        prepended_line_index = 0
        for line_number, line in enumerate(lines):
            if re.match(match_regex, line.strip()):
                has_match = True
                copy_lines[prepended_line_index] = append_str
                # Since line is added before  matched string shift index start with line_number
                # increment of prepend_line_index is 1 line after prepended_line_index should be shifted
                lines_to_be_shifted = lines[line_number:]
                copy_lines = copy_lines[0:prepended_line_index + 1] + lines_to_be_shifted
            prepended_line_index = prepended_line_index + 1
        edited_content = str_array_to_str(copy_lines)
    with open(file, "w", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING, errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        writer.write(edited_content)

    return has_match


def is_tag_on_branch(tag_name: str, branch_name: str):
    g = git.Git(os.getcwd())
    try:
        branches_str = g.execute(["git", "branch", "--contains", f"tags/{tag_name}"])
        branches = remove_prefix(branches_str, "*").split("\n")
        print("Branches str:" + branches_str)
        if len(branches) > 0:
            for branch in branches:
                if branch.strip() == branch_name:
                    return True
        return False
    except GitCommandError as e:
        print("Error:" + str(e))
        return False


def get_current_branch(working_dir: str) -> str:
    repo = get_new_repo(working_dir)

    return repo.active_branch.name


def remote_branch_exists(branch_name: str, working_dir: str) -> bool:
    repo = get_new_repo(working_dir)
    for rp in repo.references:
        if rp.name.endswith(f"/{branch_name}"):
            return True
    return False


def local_branch_exists(branch_name: str, working_dir: str) -> bool:
    repo = get_new_repo(working_dir)
    for rp in repo.branches:
        if rp.name == branch_name:
            return True
    return False


def branch_exists(branch_name: str, working_dir: str) -> bool:
    return local_branch_exists(branch_name, working_dir) or remote_branch_exists(branch_name, working_dir)


def remove_cloned_code(exec_path: str):
    release_all_repos()
    if os.path.exists(f"{exec_path}"):
        print(f"Deleting cloned code {exec_path} ...")
        # https://stackoverflow.com/questions/51819472/git-cant-delete-local-branch-operation-not-permitted
        # https://askubuntu.com/questions/1049142/cannot-delete-git-directory
        # since git directory is readonly first we need to give write permission to delete git directory
        if os.path.exists(f"{exec_path}/.git"):
            run(f"chmod -R 777 {exec_path}/.git")
        try:
            run(f"rm -rf {exec_path}")
            print("Done. Code deleted successfully.")
        except subprocess.CalledProcessError:
            print(f"Some files could not be deleted in directory {exec_path}. "
                  f"Please delete them manually or they will be deleted before next execution")


def process_template_file(project_version: str, templates_path: str, template_file_path: str,
                          postgres_version: str = ""):
    ''' This function gets the template files, changes tha parameters inside the file and returns the output.
        Template files are stored under packaging_automation/templates and these files include parametric items in the
        format of {{parameter_name}}. This function is used while creating docker files and pgxn files which include
        "project_name" as parameter. Example usage is in "test_common_tool_methods/test_process_template_file".
        Jinja2 is used as th the template engine and render function gets the file change parameters in the file
         with the given input parameters and returns the output.'''
    minor_version = get_minor_project_version(project_version)
    env = get_template_environment(templates_path)
    template = env.get_template(template_file_path)
    rendered_output = template.render(project_version=project_version, postgres_version=postgres_version,
                                      project_minor_version=minor_version)
    return f"{rendered_output}\n"


def write_to_file(content: str, dest_file_name: str):
    with open(dest_file_name, "w+", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        writer.write(content)


def get_gpg_fingerprints_by_name(name: str) -> List[str]:
    '''Returns GPG fingerprint by its unique key name. We use this function to determine the fingerprint that
       we should use when signing packages'''
    result = subprocess.run(shlex.split("gpg --list-keys"), check=True, stdout=subprocess.PIPE)
    lines = result.stdout.decode("ascii").splitlines()
    finger_prints = []
    previous_line = ""
    for line in lines:
        if line.startswith("uid") and name in line:
            finger_prints.append(previous_line.strip())
            continue
        previous_line = line
    return finger_prints


def delete_gpg_key_by_name(name: str, key_type: GpgKeyType):
    keys = get_gpg_fingerprints_by_name(name)

    # There could be more than one key with the same name. For statement is used to delete all the public keys
    # until no key remains (i.e. key_id is empty).
    # Public and private keys are stored with the same fingerprint. In some cases one of them may not be exist.
    # Therefore non-existence case is possible
    for key_id in keys:
        if key_type == GpgKeyType.public:
            delete_command = f"gpg --batch --yes --delete-key {key_id}"
        elif key_type == GpgKeyType.private:
            delete_command = f"gpg --batch --yes --delete-secret-key {key_id}"
        else:
            raise ValueError("Unsupported Gpg key type")
        output = run_with_output(delete_command)
        if output.returncode == 0:
            print(f"{key_type.name.capitalize()} key with the id {key_id} deleted")
        elif output.returncode == 2:
            # Key does not exist in keyring
            continue
        else:
            print(f"Error {output.stderr.decode('ascii')}")
            break


def delete_public_gpg_key_by_name(name: str):
    delete_gpg_key_by_name(name, GpgKeyType.public)


def delete_private_gpg_key_by_name(name: str):
    delete_gpg_key_by_name(name, GpgKeyType.private)


def delete_all_gpg_keys_by_name(name: str):
    delete_private_gpg_key_by_name(name)
    delete_public_gpg_key_by_name(name)


def get_private_key_by_fingerprint_without_passphrase(fingerprint: str) -> str:
    gpg = gnupg.GPG()

    private_key = gpg.export_keys(fingerprint, secret=True, expect_passphrase=False)
    if not private_key:
        raise ValueError(
            "Error while getting key. Most probably packaging key is stored with passphrase. "
            "Please check the passphrase and try again")
    return private_key


def get_private_key_by_fingerprint_with_passphrase(fingerprint: str, passphrase: str) -> str:
    gpg = gnupg.GPG()

    private_key = gpg.export_keys(fingerprint, secret=True, passphrase=passphrase)
    if not private_key:
        raise ValueError(
            "Error while getting key. Most probably packaging key is stored with passphrase. "
            "Please check the passphrase and try again")
    return private_key


def transform_key_into_base64_str(key: str) -> str:
    # while signing packages base64 encoded string is required. So first we encode key with ascii and create a
    # byte array than encode it with base64 and decode it with ascii to get the required output
    return base64.b64encode(key.encode("ascii")).decode("ascii")


def define_rpm_public_key_to_machine(fingerprint: str):
    with open("rpm_public.key", "w", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        subprocess.run(shlex.split(f"gpg --export -a {fingerprint}"), stdout=writer, check=True)
    run("rpm --import rpm_public.key")
    os.remove("rpm_public.key")


def delete_rpm_key_by_name(summary: str):
    rpm_keys = get_rpm_keys()
    for key in rpm_keys:
        if rpm_key_matches_summary(key, summary):
            run(f"rpm -e {key}")
            print(f"RPM key with id {key} was deleted")


def get_rpm_keys():
    result = run_with_output("rpm -q gpg-pubkey")
    if result.stderr:
        raise ValueError(f"Error:{result.stderr.decode('ascii')}")
    output = result.stdout.decode("ascii")
    key_lines = output.splitlines()
    return key_lines


def rpm_key_matches_summary(key: str, summary: str):
    result = run_with_output("rpm -q " + key + " --qf  '%{SUMMARY}'")
    if result.stderr:
        raise ValueError(f"Error:{result.stderr.decode('ascii')}")
    output = result.stdout.decode("ascii")
    return summary in output


def is_rpm_file_signed(file_path: str) -> bool:
    result = run_with_output(f"rpm -K {file_path}")
    return result.returncode == 0


def verify_rpm_signature_in_dir(rpm_dir_path: str):
    files = []
    for (dirpath, _, filenames) in os.walk(rpm_dir_path):
        files += [os.path.join(dirpath, file) for file in filenames]
    rpm_files = filter(lambda file_name: file_name.endswith("rpm"), files)
    for file in rpm_files:
        if not is_rpm_file_signed(f"{file}"):
            raise ValueError(f"File {file} is not signed or there is a signature check problem")


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        result_str = text[len(prefix):]
    else:
        result_str = text
    return result_str


def remove_suffix(initial_str: str, suffix: str) -> str:
    if initial_str.endswith(suffix):
        result_str = initial_str[:-len(suffix)]
    else:
        result_str = initial_str
    return result_str


def initialize_env(exec_path: str, project_name: str, checkout_dir: str):
    remove_cloned_code(f"{exec_path}/{checkout_dir}")
    if not os.path.exists(checkout_dir):
        run(f"git clone https://github.com/citusdata/{project_name}.git {checkout_dir}")


def create_pr(gh_token: str, pr_branch: str, pr_title: str, repo_owner: str, project_name: str, base_branch: str):
    g = Github(gh_token)
    repository = g.get_repo(f"{repo_owner}/{project_name}")
    create_pr_with_repo(repo=repository, pr_branch=pr_branch, pr_title=pr_title, base_branch=base_branch)


def create_pr_with_repo(repo: Repository, pr_branch: str, pr_title: str, base_branch: str):
    return repo.create_pull(title=pr_title, base=base_branch, head=pr_branch, body="")


def stat_get_request(request_address: str, request_type: RequestType, session):
    request_log = RequestLog(request_time=datetime.now(), request_type=request_type)
    session.add(request_log)
    session.commit()
    try:
        result = requests.get(request_address)
        request_log.status_code = result.status_code
        request_log.response = result.content.decode("ascii")
    except requests.exceptions.RequestException as e:
        result = e.response
        request_log.status_code = -1
        request_log.response = e.response.content.decode("ascii") if e.response.content.decode("ascii") else str(e)
    finally:
        session.commit()
    return result
