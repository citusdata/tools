import argparse
import json
import os
import re
import subprocess
import time
from pprint import pprint
from subprocess import PIPE

ms_package_repo_map = {
    "el/8": "centos-8",
    "el/7": "centos-7",
    "debian/buster": "debian-buster",
    "debian/jessie": "debian-jessie",
    "debian/stretch": "debian-stretch",
    "ubuntu/bionic": "ubuntu-bionic",
    "ubuntu/xenial": "ubuntu-xenial",
    "ubuntu/focal": "ubuntu-focal"
}

RELEASE_DIR = "pkgs/releases"


def run(command, *args, **kwargs):
    print(command)
    result = subprocess.run(command, *args, check=True, shell=True, **kwargs)
    return result


def publish_single_package(package_path: str, repo):
    result = run(f"repoclient package add --repoID {repo['id']} {package_path}")

    return json.loads(result.stdout)


# Ubuntu focal repo id is not returned from repoclient list so we had to add this repo manually
ubuntu_focal_repo_id = "6009d702435efdb9f7acd170"


def get_citus_repos():
    repo_list = run("repoclient repo list", stdout=PIPE)

    all_repos = json.loads(repo_list.stdout)

    repos = {}
    for repo in all_repos:
        if not repo["url"].startswith("citus-"):
            continue
        name = repo["url"][len("citus-"):]
        if name in ("ubuntu", "debian"):
            # Suffix distribution
            name = name + "-" + repo["distribution"]
        else:
            # Put dash before number
            name = re.sub(r"(\d+)", r"-\1", name)
        repos[name] = repo
    # Adding ubuntu-focal manually because list does not include ubuntu-focal
    repos["ubuntu-focal"] = {"url": "ubuntu-focal", "distribution": "focal", "id": ubuntu_focal_repo_id}
    return repos


# Ensure deb packages contain the distribution, so they do not conflict
def suffix_deb_package(repository, package_file_path):
    if not package_file_path.endswith("amd64.deb"):
        raise "Package should have ended with amd64.deb: %s" % package_file_path
    old_package_path = package_file_path
    package_prefix = package_file_path[: -len("amd64.deb")]
    package_file_path = "%s+%s_amd64.deb" % (
        package_prefix,
        repository["distribution"],
    )
    os.rename(old_package_path, package_file_path)
    return package_file_path


def publish_packages(target_platform, citus_repos):
    responses = {}
    for package_file in os.listdir(RELEASE_DIR):

        print("Target Platform is " + target_platform)
        repo_platform = ms_package_repo_map[target_platform]
        repo = citus_repos[repo_platform]
        package_path = os.path.join(RELEASE_DIR, package_file)

        print("Repo Url:" + repo["url"])

        # Ensure deb packages contain the distribution, so they do not conflict
        if repo["url"] in ("citus-ubuntu", "citus-debian"):
            if repo["distribution"] not in package_file:
                package_path = suffix_deb_package(repo, package_path)

        # Publish packages
        if os.path.isfile(package_path) and (package_file.endswith(".rpm") or package_file.endswith(".deb")):
            publish_result = publish_single_package(package_path, repo)
            responses[package_path] = publish_result
            print(
                "Waiting for 30 seconds to avoid concurrency problems on publishing server"
            )
            time.sleep(30)

    return responses


def check_submissions(all_responses):
    # Check 15 times if there are any packages that we couldn't publish
    unfinished_submissions = all_responses
    finished_submissions = {}
    for i in range(15):

        for pack_path, response in unfinished_submissions.items():
            package_id = response["Location"].split("/")[-1]

            try:
                run("repoclient package check %s" % package_id)
                finished_submissions[pack_path] = response
                del unfinished_submissions[pack_path]
            except Exception:
                print(pack_path, "was not published yet")

        if not unfinished_submissions:
            break
        time.sleep(i)

    if finished_submissions:
        print("The following packages were published successfuly")
        pprint(finished_submissions)

    if unfinished_submissions:
        print("The following packages were not published successfuly")
        pprint(unfinished_submissions)
        raise Exception("Some packages were not finished publishing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=ms_package_repo_map.keys())
    args = parser.parse_args()

    citus_repos = get_citus_repos()

    # pprint(citus_repos)
    target_platform = args.platform
    print("Citus Repos")
    pprint(citus_repos)

    submission_responses = publish_packages(target_platform, citus_repos)
    print("Submission Responses")
    pprint(submission_responses)

    check_submissions(submission_responses)
