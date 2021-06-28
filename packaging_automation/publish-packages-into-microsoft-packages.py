from subprocess import PIPE
import subprocess
import os
import json
import re
import time
import sys
from pprint import pprint

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


def suffix_deb_package(repo, package_path):
    if repo["url"] in ("citus-ubuntu", "citus-debian"):
        if repo["distribution"] not in package_file:
            if not package_path.endswith("amd64.deb"):
                raise "Package should have ended with amd64.deb: %s" % package_path
            old_package_path = package_path
            package_prefix = package_path[: -len("amd64.deb")]
            package_path = "%s+%s_amd64.deb" % (
                package_prefix,
                repo["distribution"],
            )
            os.rename(old_package_path, package_path)


def publish_single_package():
    global result
    result = run(
        "repoclient package add --repoID %s %s" % (repo["id"], package_path),
        stdout=PIPE,
    )
    submission_responses[package_path] = json.loads(result.stdout)
    print(
        "Waiting for 30 seconds to avoid concurrency problems on publishing server"
    )
    time.sleep(30)


def run(command, *args, **kwargs):
    print(command)
    result = subprocess.run(command, *args, check=True, shell=True, **kwargs)
    return result


def get_citus_repos():
    result = run("repoclient repo list", stdout=PIPE)

    all_repos = json.loads(result.stdout)

    repos = {}
    for repo in all_repos:
        if not repo["url"].startswith("citus-"):
            continue
        name = repo["url"][len("citus-"):]
        if name in ("ubuntu", "debian"):
            # Suffix distribution
            name = name + "-" + repo["distribution"]
        else:
            # Put dash before repo number
            name = re.sub(r"(\d+)", r"-\1", name)
        repos[name] = repo

    return repos


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


def publish_packages():
    global package_file, repo, package_path
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
            publish_single_package()


citus_repos = get_citus_repos()

# pprint(citus_repos)
target_platform = sys.argv[1]
submission_responses = {}
print("Citus Repos")
print("Current Dir" + os.getcwd())
pprint(citus_repos)

publish_packages()

pprint(submission_responses)

# Check 15 times if there are any packages that we couldn't publish
unfinished_submissions = {}
finished_submissions = {}
for i in range(15):

    for package_path, response in submission_responses.items():
        package_id = response["Location"].split("/")[-1]

        try:
            run("repoclient package check %s" % package_id)
            finished_submissions[package_path] = response
        except Exception:
            print(package_path, "was not published yet")
            unfinished_submissions[package_path] = response

    if not unfinished_submissions:
        break
    submission_responses = unfinished_submissions
    time.sleep(i)

if finished_submissions:
    print("The following packages were published successfuly")
    pprint(finished_submissions)

if unfinished_submissions:
    print("The following packages were not published successfuly")
    pprint(unfinished_submissions)
    raise Exception("Some packages were not finished publishing")
