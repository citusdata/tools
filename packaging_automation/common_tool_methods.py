import os
import base64
import os
import re
import subprocess
from datetime import datetime
from enum import Enum
from typing import Dict, List
from typing import Tuple

import gnupg
import pathlib2
from git import Repo
from github import Repository, PullRequest, Commit
from jinja2 import Environment, FileSystemLoader

from .common_validations import (is_tag, is_version)
from git import Repo
import pathlib2
from typing import Tuple

BASE_GIT_PATH = pathlib2.Path(__file__).parents[1]
PATCH_VERSION_MATCH_FROM_MINOR_SUFFIX = "\.\d{1,3}"

# When using GitPython library Repo objects should be closed to be able to delete cloned sources
# referenced by Repo objects.References are stored in below array to be able to close
# all resources after the code execution.
referenced_repos:List[Repo] = []


def get_new_repo(working_dir: str) -> Repo:
    repo = Repo(working_dir)
    referenced_repos.append(repo)
    return repo


def release_all_repos():
    for repo in referenced_repos:
        repo.close()


class PackageType(Enum):
    deb = 1,
    rpm = 2


BASE_PATH = pathlib2.Path(__file__).parents[1]


def get_spec_file_name(project_name: str) -> str:
    return f"{project_name}.spec"


def get_minor_project_version(project_version: str) -> str:
    project_version_details = get_version_details(project_version)
    return f'{project_version_details["major"]}.{project_version_details["minor"]}'


def get_version_number(version: str, fancy: bool, fancy_release_count: int) -> str:
    fancy_suffix = f"-{fancy_release_count}" if fancy else ""
    return f"{version}{fancy_suffix}"


def get_version_number_with_project_name(project_name: str, version: str, fancy: bool, fancy_release_count: int) -> str:
    fancy_suffix = f"-{fancy_release_count}" if fancy else ""
    return f"{version}.{project_name}{fancy_suffix}"


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
    result = subprocess.run(command, *args, check=True, shell=True, **kwargs)
    return result


def run_with_output(command, *args, **kwargs):
    result = subprocess.run(command, *args, check=True, shell=True, stdout=subprocess.PIPE, **kwargs)
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


def get_patch_version_regex(version: is_version(str)):
    return fr"^{re.escape(get_minor_version(version))}{PATCH_VERSION_MATCH_FROM_MINOR_SUFFIX}$"


def is_merge_commit(commit: Commit):
    return len(commit.parents) <= 1


def get_version_details(version: is_version(str)) -> Dict[str, str]:
    version_parts = version.split(".")
    return {"major": version_parts[0], "minor": version_parts[1], "patch": version_parts[2]}


def get_upcoming_patch_version(version: is_version(str)) -> str:
    project_version_details = get_version_details(version)
    return f'{get_upcoming_minor_version(version)}.{int(project_version_details["patch"]) + 1}'


def get_upcoming_minor_version(version: is_version(str)) -> str:
    project_version_details = get_version_details(version)
    return f'{project_version_details["major"]}.{int(project_version_details["minor"]) + 1}'


def get_last_commit_message(path: str) -> str:
    repo = get_new_repo(path)
    commit = repo.head.commit
    return commit.message


def is_major_release(version: is_version(str)) -> bool:
    version_info = get_version_details(version)
    return version_info["patch"] == "0"


def str_array_to_str(str_array: List[str]) -> str:
    return f"{os.linesep.join(str_array)}{os.linesep}"


def get_prs_for_patch_release(repo: Repository.Repository, earliest_date: datetime, base_branch: str,
                              last_date: datetime = None):
    pull_requests = repo.get_pulls(state="closed", base=base_branch, sort="created", direction="desc")

    # filter pull requests according to given time interval
    filtered_pull_requests = list()
    for pull_request in pull_requests:
        if not pull_request.is_merged():
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
    with open(f"{base_path}/{relative_file_path}", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        for line in lines:
            if line == line_content:
                return True
    return False


def count_line_in_file(base_path: str, relative_file_path: str, search_line: str) -> int:
    with open(f"{base_path}/{relative_file_path}", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
    return len(list(filter(lambda line: line == search_line, lines)))


def replace_line_in_file(file: str, match_regex: str, replace_str: str) -> bool:
    with open(file, "r") as reader:
        file_content = reader.read()
        lines = file_content.splitlines()
        has_match = False
        for line_number, line in enumerate(lines):
            if re.match(match_regex, line.strip()):
                has_match = True
                lines[line_number] = replace_str
        edited_content = str_array_to_str(lines)
    with open(file, "w") as writer:
        writer.write(edited_content)

    return has_match


def append_line_in_file(file: str, match_regex: str, append_str: str) -> bool:
    with open(file, "r+") as reader:
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
    with open(file, "w") as writer:
        writer.write(edited_content)

    return has_match


def prepend_line_in_file(file: str, match_regex: str, append_str: str) -> bool:
    with open(file, "r+") as reader:
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
    with open(file, "w") as writer:
        writer.write(edited_content)

    return has_match


def get_current_branch(working_dir: str) -> str:
    repo = get_new_repo(working_dir)
    return repo.active_branch


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


def does_branch_exist(branch_name: str, working_dir: str) -> bool:
    return local_branch_exists(branch_name, working_dir) or remote_branch_exists(branch_name, working_dir)


def get_template_environment(template_dir: str) -> Environment:
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    return env


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
        except:
            print(f"Some files could not be deleted in directory {exec_path}. "
                  f"Please delete them manually or they will be deleted before next execution")


def process_docker_template_file(project_version: str, templates_path: str, template_file_path: str):
    minor_version = get_minor_project_version(project_version)
    env = get_template_environment(templates_path)
    template = env.get_template(template_file_path)
    return f"{template.render(project_version=project_version, project_minor_version=minor_version)}\n"


def write_to_file(content: str, dest_file_name: str):
    with open(dest_file_name, "w") as writer:
        writer.write(content)


def get_gpg_fingerprint_from_name(name: str):
    result = subprocess.run(f"gpg --list-keys ", check=True, shell=True, stdout=subprocess.PIPE)
    lines = result.stdout.decode("ascii").splitlines()
    counter = 0
    line_found = False
    for line in lines:
        if line.startswith("uid") and name in line:
            line_found = True
            break
        counter = counter + 1
    if not line_found:
        raise ValueError(f"Key with the name {name} could not be found ")
    else:
        return lines[counter - 1].strip()


def delete_gpg_key_by_name(name: str):
    try:
        while True:
            key_id = get_gpg_fingerprint_from_name(name)
            run(f"gpg --batch --yes --delete-secret-key {key_id}")
            run(f"gpg --batch --yes --delete-key {key_id}")
    except ValueError:
        print(f"Key for the name {name} does not exist")


def get_secret_key_by_fingerprint(fingerprint: str) -> str:
    try:
        cmd = f'gpg --batch --export-secret-keys -a "{fingerprint}" | base64'
        ps = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=2)
        secret_key = ps.stdout.decode("ascii")
        return secret_key
    except subprocess.TimeoutExpired:
        raise ValueError(
            f"Error while getting key. Most probably packaging key is stored with password. "
            f"Please remove the password when storing key with fingerprint {fingerprint}")


def get_secret_key_by_fingerprint_with_password(fingerprint: str, passphrase: str) -> str:
    try:
        gpg = gnupg.GPG()
        private_key = gpg.export_keys(fingerprint, True, passphrase=passphrase)

        return base64.b64encode(private_key.encode("ascii")).decode("ascii")
    except subprocess.TimeoutExpired:
        raise ValueError(
            f"Error while getting key. Most probably packaging key is stored with password. "
            f"Please remove the password when storing key with fingerprint {fingerprint}")


def get_public_gpg_key(fingerprint: str) -> str:
    gpg = gnupg.GPG()
    ascii_armored_public_keys = gpg.export_keys(fingerprint)
    return base64.b64encode(ascii_armored_public_keys.encode("ascii")).decode("ascii")


def define_rpm_public_key_to_machine(fingerprint: str):
    run(f"gpg --export -a {fingerprint} >rpm_public.key")
    run("rpm --import rpm_public.key")
    os.remove("rpm_public.key")


def delete_rpm_key_by_name(key_name: str):
    result = subprocess.run(["rpm", "-q gpg-pubkey", "--qf %{NAME}-%{VERSION}-%{RELEASE}\t%{SUMMARY}\n"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode("ascii")
    if output == "package gpg-pubkey is not installed":
        print("There is not rpm public key to delete")
    else:
        key_lines = output.splitlines()
        key_lines_filtered = filter(lambda line: key_name in line, key_lines)
        for key_line in key_lines_filtered:
            keys = key_line.split()
            if len(keys) > 0:
                run(f"rpm -e {keys[0]}")
                print(f"{keys[0]} deleted")


def is_rpm_file_signed(file_path: str) -> bool:
    result = run_with_output(f"rpm -K {file_path}")
    if result.returncode == 0:
        return True
    else:
        return False


def verify_rpm_signature_in_dir(rpm_dir_path: str):
    files = list()
    for (dirpath, dirnames, filenames) in os.walk(rpm_dir_path):
        files += [os.path.join(dirpath, file) for file in filenames]
    rpm_files = filter(lambda file_name: file_name.endswith("rpm"), files)
    for file in rpm_files:
        if not is_rpm_file_signed(f"{file}"):
            raise ValueError(f"File {file} is not signed or there is a signature check problem")


def get_current_branch(exec_path: str):
    repo = Repo(exec_path)
    return repo.active_branch


def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]
