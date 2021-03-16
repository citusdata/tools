import os
import sys
import ntpath;
from dataclasses import dataclass
from typing import List

import requests

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


def upload_to_packagecloud(distro_name, package_name, packagecloud_token, repo_name) -> ReturnValue:
    distro_id = supported_distros[distro_name]
    files = {
        'package[distro_version_id]': (None, str(distro_id)),
        'package[package_file]': (
            package_name, open(package_name, 'rb')),
    }

    package_query_url = 'https://' + packagecloud_token + ':@packagecloud.io/api/v1/repos/citus-bot/' + repo_name + '/packages.json'
    print(f"Uploading package {ntpath.basename(package_name)} using path {package_query_url}")
    response = requests.post(package_query_url, files=files)
    print(f"Response from package cloud: {response.content}")
    return ReturnValue(response.ok, response.content, package_name, distro_name, repo_name)


def upload_files_in_directory_to_packagecloud(directoryName: str, distro_name: str, package_cloud_token: str,
                                              repo_name: str) -> MultipleReturnValue:
    # print("Distro Name: " + distro_name)
    # print("Supported Distros:")
    for key, value in supported_distros.items():
        print(key + "=>" + str(value))
    ret_status: List[ReturnValue] = []

    # TODO may be parameterized to push all files. Now only two level
    print("Test version")
    for firstLevelFileItem in os.listdir(directoryName):
        item_name = os.path.join(directoryName, firstLevelFileItem)
        if os.path.isdir(item_name):
            for filename in os.listdir(item_name):
                if filename.lower().endswith((".rpm", ".deb")):
                    ret_val = upload_to_packagecloud(distro_name, os.path.join(item_name, filename),
                                                     package_cloud_token,
                                                     repo_name)
                    ret_status.append(ret_val)
        else:
            if filename.lower().endswith((".rpm", ".deb")):
                filename = firstLevelFileItem
                ret_val = upload_to_packagecloud(distro_name, os.path.join(directoryName, filename), package_cloud_token,
                                                 repo_name)
                ret_status.append(ret_val)

    return MultipleReturnValue(ret_status)


if len(sys.argv) < 3:
    raise Exception("Distro Name package_cloud_api_token and repository name parameters should be provided")

target_platform = sys.argv[1]
package_cloud_api_token = sys.argv[2]
repository_name = sys.argv[3]
multiple_return_value = upload_files_in_directory_to_packagecloud(os.path.join(os.getcwd(), "pkgs/releases"),
                                                                  target_platform,
                                                                  package_cloud_api_token, repository_name)
print(multiple_return_value.success_status())
print(multiple_return_value.return_values)
for rv in multiple_return_value.return_values:
    if not rv.success_status:
        print(
            f'Error occured while uploading file on package cloud. Error: {rv.message} Distro: {rv.distro} File Name: {ntpath.basename(rv.file_name)} Repo Name: {rv.repo}')
    else:
        print(
            f'File successfully uploaded. Distro: {rv.distro} File Name: {ntpath.basename(rv.file_name)} Repo Name: {rv.repo}')
if multiple_return_value.success_status():
    sys.exit(0)
else:
    sys.exit(1)
# for rv in multiple_return_value.return_values:
#     if(rv.)
# print(r.message)
# print(r.success_status)
