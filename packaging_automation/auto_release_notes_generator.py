import requests
import json
from enum import Enum
from typing import List
from dataclasses import dataclass
import argparse
import os

REPO_NAME = "citusdata/citus"
repos = ["citusdata/citus", "citusdata/pg_auto_failover"]
user_cache = {}


class GitHubQuerySort(Enum):
    asc = 1
    desc = 2


class GitHubState(Enum):
    open = 1
    closed = 2


@dataclass
class PullRequest:
    number: int
    title: str
    user_name: str
    user_login: str


def get_pulls(
        state: GitHubState = None,
        sort: GitHubQuerySort = GitHubQuerySort.desc,
        milestone: str = None,
        base: str = None,
        head: str = None
) -> List[PullRequest]:
    pull_requests = []
    page_number = 1
    remaining_record_exists = True
    query_string = f"https://api.github.com/search/issues?q=is:pr+repo:{REPO_NAME}"
    params = {}
    if state:
        params["state"] = state.name
    if sort:
        params["sort"] = sort.name
    if milestone:
        params["milestone"] = f'"{milestone}"'
    if base:
        params["base"] = base
    if head:
        params["head"] = head

    for key, value in params.items():
        query_string = f"{query_string}+{key}:{value}"

    while remaining_record_exists:
        raw_result = requests.get(f"{query_string}&page={str(page_number)}")

        result = json.loads(raw_result.content)
        if len(result["items"]) == 0:
            remaining_record_exists = False
        else:
            page_number = page_number + 1
            for pr in result["items"]:
                user_url = pr["user"]["url"]
                user_result = get_user_info(user_url)

                pull_requests.append(
                    PullRequest(number=pr["number"], title=pr["title"], user_login=pr["user"]["login"],
                                user_name=user_result["name"]))
    return pull_requests


def get_user_info(user_url):
    if user_url in user_cache:
        return user_cache[user_url]
    raw_user_result = requests.get(user_url)
    user_result = json.loads(raw_user_result.content)
    user_cache[user_url] = user_result
    return user_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--milestone', required=True)
    parser.add_argument('--repo', choices=repos)

    arguments = parser.parse_args()

    prs = get_pulls(milestone=arguments.milestone)
    current_dir = os.getcwd()
    with open(f"{current_dir}/release.exclude", "r") as reader:
        content = reader.read()
    excluded_pr_numbers = content.splitlines()

    filtered_prs = list(filter(lambda p: (str(p.number) not in excluded_pr_numbers), prs))
    for pr in filtered_prs:
        print(str(pr.number) + "-" + pr.title + "-" + pr.user_name + "-" + pr.user_login)
