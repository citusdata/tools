import re
import subprocess
from datetime import datetime
from typing import Dict, List

from github import Repository, PullRequest
from jinja2 import Environment, FileSystemLoader

from .common_validations import *


def get_spec_file_name(project_name: str) -> str:
    return f"{project_name}.spec"


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


def cherry_pick_prs(prs: List[PullRequest.PullRequest]):
    for pr in prs:
        commits = pr.get_commits()
        for single_commit in commits:
            cp_result = run(f"git cherry-pick {single_commit.commit.sha}")
            print(f"Cherry pick result for PR No {pr.number} and commit sha {single_commit.commit.sha}: {cp_result}  ")


def get_version_details(version: is_version(str)) -> Dict[str, str]:
    version_parts = version.split(".")
    return {"major": version_parts[0], "minor": version_parts[1], "patch": version_parts[2]}


def is_major_release(version: is_version(str)) -> bool:
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


def replace_line_in_file(file: str, match_regex: str, replace_str: str):
    with open(file, "r") as reader:
        file_content = reader.read()
        lines = file_content.splitlines()
        line_counter = 0
        for line in lines:
            if re.match(match_regex, line):
                lines[line_counter] = replace_str
            line_counter = line_counter + 1
        edited_content = str_array_to_str(lines)
    with open(file, "w") as writer:
        writer.write(edited_content)
