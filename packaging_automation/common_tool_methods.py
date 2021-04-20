import subprocess
import re
from datetime import datetime
from typing import Dict, List

from github import Repository, PullRequest
from jinja2 import Environment, FileSystemLoader

from . import common_validations


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


def get_template_environment(template_dir: str) -> Environment:
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    return env


def find_nth_overlapping(subject_string, search_string, n) -> int:
    start = subject_string.find(search_string)

    while start >= 0 and n > 1:
        start = subject_string.find(search_string, start + 1)
        n -= 1
    return start


def find_nth_overlapping_line_by_regex(subject_string, regex_pattern, n) -> int:
    lines = subject_string.splitlines()
    counter = 0
    index = -1
    for i in range(len(lines)):
        if re.match(regex_pattern, lines[i]):
            counter = counter + 1
        if counter == n:
            index = i
            break
    return index


def remove_string_inside_parentheses(param: str) -> str:
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
            cp_result = run(f"git cherry-pick {single_commit.commit.sha}")
            print(f"Cherry pick result for PR No {pr.number} and commit sha {single_commit.commit.sha}: {cp_result}  ")


def get_version_details(version: common_validations.is_version(str)) -> Dict[str, str]:
    version_parts = version.split(".")
    return {"major": version_parts[0], "minor": version_parts[1], "patch": version_parts[2]}


def is_major_release(version: common_validations.is_version(str)) -> bool:
    version_info = get_version_details(version)
    return version_info["patch"] == "0"


def str_array_to_str(str_array: List[str]) -> str:
    result_str = ""
    for i in range(len(str_array)):
        result_str = result_str + str_array[i] + "\n"
    return result_str


def get_prs(repo: Repository.Repository, earliest_date: datetime, base_branch: str, last_date: datetime = None):
    pulls = repo.get_pulls(state="all", base=base_branch, sort="created", direction="desc")
    picked_pulls = []
    for pull in pulls:
        if not pull.is_merged():
            continue
        if last_date is not None and pull.created_at > last_date:
            continue
        if pull.created_at < earliest_date:
            break
        if pull.merged_at is not None and pull.merged_at > earliest_date:
            picked_pulls.append(pull)
    return picked_pulls


def get_pr_issues_by_label(prs: List[PullRequest.PullRequest], label_name: str):
    filtered_prs = []
    for pr in prs:
        filtered_labels = filter(lambda label: label.name == label_name, pr.labels)
        if len(list(filtered_labels)) > 0:
            filtered_prs.append(pr)
    return filtered_prs


def has_file_include_line(base_path: str, relative_file_path: str, line_content: str) -> bool:
    with open(f"{base_path}/{relative_file_path}", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        found = False
        for line in lines:
            if line == line_content:
                found = True
                break
    return found


def line_count_in_file(base_path: str, relative_file_path: str, line_content: str) -> int:
    with open(f"{base_path}/{relative_file_path}", "r") as reader:
        content = reader.read()
        lines = content.splitlines()
        counter = 0
        for line in lines:
            if line == line_content:
                counter = counter + 1

    return counter


def replace_line_in_file(file: str, match_regex: str, replace_str: str) -> bool:
    with open(file, "r") as reader:
        file_content = reader.read()
        lines = file_content.splitlines()
        line_counter = 0
        has_match = False
        for line in lines:
            if re.match(match_regex, line):
                has_match = True
                lines[line_counter] = replace_str
            line_counter = line_counter + 1
        edited_content = str_array_to_str(lines)
    with open(file, "w") as writer:
        writer.write(edited_content)

    return has_match


def process_docker_template_file(project_version: str, templates_path: str, template_file_path: str):
    minor_version = get_minor_project_version(project_version)
    env = get_template_environment(templates_path)
    template = env.get_template(template_file_path)
    return f"{template.render(project_version=project_version, project_minor_version=minor_version)}\n"


def write_to_file(content: str, dest_file_name: str):
    with open(dest_file_name, "w") as writer:
        writer.write(content)


def get_gpg_key_from_email(email: str):
    result = subprocess.run(f"gpg --list-keys ", check=True, shell=True, stdout=subprocess.PIPE)
    lines = result.stdout.decode("ascii").splitlines()
    counter = 0
    line_found = False
    for line in lines:
        if line.startswith("uid") and email in line:
            line_found = True
            break
        counter = counter + 1
    if not line_found:
        raise ValueError(f"Key with the  email address {email} could not be found ")
    else:
        return lines[counter - 1].strip()


def delete_gpg_key_by_email(email: str):
    try:
        while True:
            key_id = get_gpg_key_from_email(email)
            run(f"gpg --batch --yes --delete-secret-key {key_id}")
            run(f"gpg --batch --yes --delete-key {key_id}")
    except ValueError:
        print(f"Key for the email {email} does not exist")


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
