from dataclasses import dataclass

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


def upload_to_packagecloud(distro_name, package_name, packagecloud_token) -> ReturnValue:

    distro_id = supported_distros[distro_name]
    files = {
        'package[distro_version_id]': (None, distro_id),
        'package[package_file]': (
            package_name, open(package_name, 'rb')),
    }

    response = requests.post(
        'https://' + packagecloud_token + ':@packagecloud.io/api/v1/repos/citus-bot/sample/packages.json',
        files=files)
    return ReturnValue(response.ok, response.content)


r = upload_to_packagecloud("el/8",
                           "pg-auto-failover14_12-1.4.2-2.el7.x86_64.rpm",
                           "cf058e6c1453b02742cae518499e80dd13a3e9a0893509fd")
print(r.message)
print(r.success_status)
