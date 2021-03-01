import os
import sys
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


@dataclass
class MultipleReturnValue:
    def __init__(self, ret_vals: List[ReturnValue]):
        self.return_values = ret_vals

    multiple_return_value: List[ReturnValue]

    def success_status(self) -> bool:
        return [r for r in self.return_values if not r.success_status].count == 0


def upload_to_packagecloud(distro_name, package_name, packagecloud_token, repo_name) -> ReturnValue:
    distro_id = supported_distros[distro_name]
    files = {
        'package[distro_version_id]': (None, str(distro_id)),
        'package[package_file]': (
            package_name, open(package_name, 'rb')),
    }
    package_query_url = 'https://' + packagecloud_token + ':@packagecloud.io/api/v1/repos/citus-bot/' + repo_name + '/packages.json'
    print("Url:" + package_query_url)
    print("Package Name:"+package_name)
    response = requests.post(package_query_url, files=files)
    return ReturnValue(response.ok, response.content)


def upload_files_in_directory_to_packagecloud(directoryName: str, distro_name: str, package_cloud_token: str,
                                              repo_name: str) -> MultipleReturnValue:
    print("Distro Name: " + distro_name)
    print("Supported Distros:")
    for key, value in supported_distros.items():
        print(key + "=>" + str(value))
    ret_status: List[ReturnValue] = []
    for filename in os.listdir(directoryName):
        ret_val = upload_to_packagecloud(distro_name, os.path.join(directoryName, filename), package_cloud_token,
                                         repo_name)
        ret_status.append(ret_val)

    return MultipleReturnValue(ret_status)


# r = upload_to_packagecloud("el/8",
#                            "pg-auto-failover14_12-1.4.2-2.el7.x86_64.rpm",
#                            "cf058e6c1453b02742cae518499e80dd13a3e9a0893509fd")

if len(sys.argv) < 3:
    raise Exception("Distro Name package_cloud_api_token and repository name parameters should be provided")

target_platform = sys.argv[1]
package_cloud_api_token = sys.argv[2]
repository_name = sys.argv[3]
multiple_return_value = upload_files_in_directory_to_packagecloud(os.path.join(os.getcwd(), "pkgs/releases"),
                                                                  target_platform,
                                                                  package_cloud_api_token, repository_name)
print(multiple_return_value.success_status())
[print(i) for i in multiple_return_value.return_values]

# print(r.message)
# print(r.success_status)
