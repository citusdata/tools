import argparse
import glob
import os
import urllib
from dataclasses import dataclass
from typing import List

import pathlib2
import requests
from requests.auth import HTTPBasicAuth

supported_distros = {
    "el/7": 140,
    "el/8": 205,
    "ol/7": 146,
    "debian/buster": 150,
    "debian/stretch": 149,
    "ubuntu/focal": 210,
    "ubuntu/bionic": 190,
    "ubuntu/xenial": 165
}

supported_repos = ["sample",
                   "citusdata/enterprise",
                   "citusdata/community",
                   "citusdata/community-nightlies",
                   "citusdata/enterprise-nightlies",
                   "citusdata/azure"]


@dataclass
class ReturnValue:
    success_status: bool
    message: str
    file_name: str
    distro: str
    repo: str


@dataclass
class MultipleReturnValue:
    def __init__(self, ret_vals: List[ReturnValue]):
        self.return_values = ret_vals

    multiple_return_value: List[ReturnValue]

    def success_status(self) -> bool:
        return len([r for r in self.return_values if not r.success_status]) == 0


BASE_PATH = pathlib2.Path(__file__).parents[1]


def upload_to_package_cloud(distro_name, package_name, package_cloud_token, repo_name) -> ReturnValue:
    distro_id = supported_distros[distro_name]

    files = {
        'package[distro_version_id]': (None, str(distro_id)),
        'package[package_file]': (
            package_name, open(package_name, 'rb')),  # pylint: disable=consider-using-with
    }

    package_query_url = (
        f'https://{package_cloud_token}:@packagecloud.io/api/v1/repos/{repo_name}/packages.json')
    print(f"Uploading package {os.path.basename(package_name)}")
    response = requests.post(package_query_url, files=files)
    print(f"Response from package cloud: {response.content}")
    return ReturnValue(response.ok, response.content.decode("ascii"), package_name, distro_name, repo_name)


def upload_files_in_directory_to_package_cloud(directoryName: str, distro_name: str, package_cloud_token: str,
                                               repo_name: str, current_branch: str,
                                               main_branch: str) -> MultipleReturnValue:
    if not main_branch:
        raise ValueError("main_branch should be defined")
    if main_branch != current_branch:
        print(f"Package publishing skipped since current branch is not equal to {main_branch}")
        return MultipleReturnValue(ret_vals=[])

    ret_status: List[ReturnValue] = []

    files = glob.glob(f"{directoryName}/**/*.*", recursive=True)

    for file in files:
        if file.endswith((".rpm", ".deb")):
            ret_val = upload_to_package_cloud(distro_name, file,
                                              package_cloud_token,
                                              repo_name)
            ret_status.append(ret_val)

    return MultipleReturnValue(ret_status)


def delete_package_from_package_cloud(package_cloud_token: str, repo_owner: str, repo_name: str, distro_name: str,
                                      distro_version: str, package_name: str) -> ReturnValue:
    delete_url = (f'https://{package_cloud_token}:@packagecloud.io/api/v1/repos/{repo_owner}/{repo_name}/'
                  f'{distro_name}/{distro_version}/{package_name}')

    response = requests.delete(delete_url)
    return ReturnValue(response.ok, response.content, package_name, distro_name, repo_name)


def package_exists(package_cloud_token: str, repo_owner: str, repo_name: str, package_name: str,
                   platform: str) -> bool:
    query_url = (f"https://packagecloud.io/api/v1/repos/{repo_owner}/{repo_name}/search?"
                 f"q={package_name}&filter=all&dist={urllib.parse.quote(platform, safe='')}")
    response = requests.get(query_url, auth=HTTPBasicAuth(package_cloud_token, ''))
    return response.ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=supported_distros.keys())
    parser.add_argument('--package_cloud_api_token', required=True)
    parser.add_argument('--repository_name', required=True, choices=supported_repos)
    parser.add_argument('--output_file_path', required=True)
    parser.add_argument('--current_branch', required=True)
    parser.add_argument('--main_branch', required=True)

    args = parser.parse_args()

    multiple_return_value = upload_files_in_directory_to_package_cloud(args.output_file_path,
                                                                       args.platform,
                                                                       args.package_cloud_api_token,
                                                                       args.repository_name, args.current_branch,
                                                                       args.main_branch)
    print(multiple_return_value.success_status())
    print(multiple_return_value.return_values)
    for rv in multiple_return_value.return_values:
        if not rv.success_status:
            print(
                f'Error occured while uploading file on package cloud. Error: {rv.message} Distro: {rv.distro} '
                f'File Name: {os.path.basename(rv.file_name)} Repo Name: {rv.repo}')
        else:
            print(f'File successfully uploaded. Distro: {rv.distro} File Name: {os.path.basename(rv.file_name)} '
                  f'Repo Name: {rv.repo}')
    if not multiple_return_value.success_status():
        raise ValueError("There were some errors while uploading some packages")
