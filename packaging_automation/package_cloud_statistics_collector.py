import json
import time

import requests
from sqlalchemy import Column, INTEGER

from .dbconfig import (Base)

PACKAGE_CLOUD_API_TOKEN = "cf058e6c1453b02742cae518499e80dd13a3e9a0893509fd"
ORGANIZATION_NAME = "citusdata"
PAGE_RECORD_COUNT = 100

class PackageCloudDownloadStats(Base):
    __tablename__ = "github_clone_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)


def fetch_and_save_package_cloud_stats(package_cloud_api_token: str, repo_name: str, ref_mod_value: int,
                                       mod_index: int) -> bool:
    more_packages_exists = True
    page_count = mod_index
    while more_packages_exists:
        start = time.time()
        result = requests.get(
            f"https://{package_cloud_api_token}:@packagecloud.io/api/v1/repos/{ORGANIZATION_NAME}/{repo_name}/packages.json?per_page={PAGE_RECORD_COUNT}&page={page_count}")

        package_info_list = json.loads(result.content)
        for package_info in package_info_list:
            print(f"{package_info['name']}-{package_info['downloads_series_url']}-{package_info['type']}-"
                  f"{package_info['distro_version']}-{package_info['filename']}")

        print(page_count)
        if len(package_info_list) > 0:
            page_count = page_count + ref_mod_value
        else:
            more_packages_exists = False
        end = time.time()

        print(end - start)

    # result = requests.get(
    #     f"https://cf058e6c1453b02742cae518499e80dd13a3e9a0893509fd:@packagecloud.io/api/v1/repos/{ORGANIZATION_NAME}/{repo_name}/package/deb/debian/buster/pg-auto-failover-cli-1.4/amd64/1.4.1-1/stats/downloads/series/daily.json")

    print(counter)
    return more_packages_exists


fetch_and_save_package_cloud_stats(PACKAGE_CLOUD_API_TOKEN, "community", 5, 1)
