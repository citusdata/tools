import re
import subprocess
from datetime import datetime
from typing import Dict, List
import os

from github import Repository, PullRequest, Commit
from jinja2 import Environment, FileSystemLoader

from .common_validations import (is_tag, is_version)
from git import Repo
import pathlib2
from typing import Tuple

BASE_GIT_PATH = pathlib2.Path(__file__).parents[1]
PATCH_VERSION_MATCH_FROM_MINOR_SUFFIX = "\.\d{1,3}"


def get_spec_file_name(project_name: str) -> str:
    return f"{project_name}.spec"


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
    """Removes texts within parentheses i.e. outside parenthesis(inside parenthesis)-> outside parenthesis """
    return re.sub(r"[(\[].*?[)\]]", "", param)


def run(command, *args, **kwargs):
    result = subprocess.run(command, *args, check=True, shell=True, **kwargs)
    return result


def cherry_pick_prs(prs: List[PullRequest.PullRequest]):
    for pr in prs:
        commits = pr.get_commits()
        for single_commit in commits:
            if not is_merge_commit(single_commit):
                cp_result = run(f"git cherry-pick {single_commit.commit.sha}")
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
    upcoming_version_details = get_version_details(version)
    return f'{upcoming_version_details["major"]}.{upcoming_version_details["minor"]}'


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


def get_current_branch() -> str:
    repo = Repo(BASE_GIT_PATH)
    return repo.active_branch
