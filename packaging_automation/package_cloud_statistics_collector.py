import json
import time

from datetime import datetime, date
import requests
from sqlalchemy import Column, INTEGER, DATE, TIMESTAMP, String, TEXT

from .dbconfig import (Base, db_session, DbParams)
from .common_tool_methods import (remove_suffix)
from enum import Enum
from typing import List, Any
import os
from http import HTTPStatus

PACKAGE_CLOUD_API_TOKEN = os.getenv("PACKAGE_CLOUD_API_TOKEN")
ORGANIZATION_NAME = "citusdata"
PAGE_RECORD_COUNT = 30
PC_PACKAGE_COUNT_SUFFIX = " packages"
PC_DOWNLOAD_DATE_FORMAT = '%Y%m%dZ'
SAVE_RECORDS_WITH_DOWNLOAD_COUNT_ZERO = False


class RequestType(Enum):
    docker_pull = 1
    github_clone = 2
    package_cloud_list_package = 3
    package_cloud_detail_query = 4
    homebrew_download = 5


class PackageCloudDownloadStats(Base):
    __tablename__ = "package_cloud_download_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_date = Column(TIMESTAMP, nullable=False)
    package_name = Column(String, nullable=False)
    package_full_name = Column(String, nullable=False)
    package_version = Column(String, nullable=False)
    package_release = Column(String, nullable=False)
    package_type = Column(String, nullable=False)
    download_date = Column(DATE, nullable=False)
    download_count = Column(INTEGER, nullable=False)


class RequestLog(Base):
    __tablename__ = "request_log"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    request_time = Column(TIMESTAMP, nullable=False)
    request_type = Column(String, nullable=False)
    status_code = Column(INTEGER)
    response = Column(TEXT)


def package_count(repo_name: str) -> int:
    result = requests.get(
        f"https://{PACKAGE_CLOUD_API_TOKEN}:@packagecloud.io/api/v1/repos.json?include_collaborations=true")

    repo_details = json.loads(result.content)
    for repo in repo_details:
        if repo["name"] == repo_name:
            return int(remove_suffix(repo['package_count_human'], PC_PACKAGE_COUNT_SUFFIX))
    raise ValueError(f"Repo name with the name {repo_name} could not be found on package cloud")


def fetch_and_save_package_cloud_stats(db_params: DbParams, package_cloud_api_token: str, repo_name: str,
                                       ref_mod_value: int,
                                       mod_index: int, total_package_count: int, is_test: bool = False):
    session = db_session(db_params=db_params, is_test=is_test)
    page_index = mod_index + 1
    start = time.time()
    while is_page_in_range(page_index, total_package_count):

        result = stat_get_request(package_request_address(package_cloud_api_token, page_index, repo_name),
                                  RequestType.package_cloud_list_package, session)
        package_info_list = json.loads(result.content)
        print(page_index)
        if len(package_info_list) > 0:
            page_index = page_index + ref_mod_value
        else:
            break
        # print(package_info_list)
        fetch_and_save_package_stats(package_info_list, package_cloud_api_token, session)

        session.commit()
    end = time.time()

    print(end - start)


def fetch_and_save_package_stats(package_info_list: List[Any], package_cloud_api_token: str, session):
    for package_info in package_info_list:
        # print(f"{package_info['created_at']}-{package_info['name']}-{package_info['downloads_series_url']}-{package_info['type']}-"
        #       f"{package_info['distro_version']}-{package_info['filename']}")
        request_result = stat_get_request(
            package_details_request_address(package_cloud_api_token, package_info['downloads_series_url']),
            RequestType.package_cloud_detail_query, session)
        if request_result.status_code == HTTPStatus.OK:
            download_stats = json.loads(request_result.content)
            for stat_date in download_stats['value']:
                download_date = datetime.strptime(stat_date, PC_DOWNLOAD_DATE_FORMAT).date()
                download_count = int(download_stats['value'][stat_date])
                if download_date != datetime.today() and not stat_records_exists(download_date,
                                                                                 package_info['filename'],
                                                                                 session) and (
                        is_download_count_eligible_for_save(download_count)):
                    pc_stats = PackageCloudDownloadStats(fetch_date=datetime.now(),
                                                         package_full_name=package_info['filename'],
                                                         package_name=package_info['name'],
                                                         package_version=package_info['version'],
                                                         package_release=package_info['release'],
                                                         package_type=package_info['type'],
                                                         download_date=download_date,
                                                         download_count=download_count)
                    session.add(pc_stats)


def package_details_request_address(package_cloud_api_token: str, detail_query_uri: str):
    return f"https://{package_cloud_api_token}:@packagecloud.io/{detail_query_uri}"


def package_request_address(package_cloud_api_token, page_index, repo_name) -> str:
    return (f"https://{package_cloud_api_token}:@packagecloud.io/api/v1/repos/{ORGANIZATION_NAME}/{repo_name}"
            f"/packages.json?per_page={PAGE_RECORD_COUNT}&page={page_index}")


def stat_get_request(request_address: str, request_type: RequestType, session):
    request_log = RequestLog(request_time=datetime.now(), request_type=request_type.name)
    session.add(request_log)
    session.commit()
    result = requests.get(request_address)
    request_log.status_code = result.status_code
    request_log.response = result.content.decode("ascii")
    session.commit()
    return result


def is_download_count_eligible_for_save(download_count: int) -> bool:
    return download_count > 0 or (download_count == 0 and SAVE_RECORDS_WITH_DOWNLOAD_COUNT_ZERO)


def is_page_in_range(page_index, total_package_count):
    return page_index * PAGE_RECORD_COUNT < total_package_count or (
            page_index * PAGE_RECORD_COUNT >= total_package_count > page_index - 1 * PAGE_RECORD_COUNT)


def stat_records_exists(download_date: date, package_full_name: str, session) -> bool:
    db_record = session.query(PackageCloudDownloadStats).filter_by(download_date=download_date,
                                                                   package_full_name=package_full_name).first()
    return db_record is not None


DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")

db_parameters = DbParams(user_name=DB_USER_NAME, password=DB_PASSWORD, host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME)
pack_count = package_count("azure")
print(pack_count)
fetch_and_save_package_cloud_stats(db_parameters, PACKAGE_CLOUD_API_TOKEN, "azure", 30, 0, pack_count)
