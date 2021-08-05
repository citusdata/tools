import argparse
import json
import time
from datetime import datetime, date
from enum import Enum
from http import HTTPStatus
from typing import List, Any

import requests
from sqlalchemy import Column, INTEGER, DATE, TIMESTAMP, String
import sqlalchemy

from .common_tool_methods import (remove_suffix, stat_get_request)
from .dbconfig import (Base, db_session, DbParams, RequestType)

PC_PACKAGE_COUNT_SUFFIX = " packages"
PC_DOWNLOAD_DATE_FORMAT = '%Y%m%dZ'


class PackageCloudRepos(Enum):
    community = "community"
    enterprise = "enterprise"
    azure = "azure"
    community_nightlies = "community-nightlies"
    enterprise_nightlies = "enterprise-nightlies"
    test = "test"


class PackageCloudOrganizations(Enum):
    citusdata = "citusdata"
    citus_bot = "citus-bot"


class PackageCloudDownloadStats(Base):
    __tablename__ = "package_cloud_download_stats"
    id = Column(INTEGER, primary_key=True, autoincrement=True)
    fetch_date = Column(TIMESTAMP, nullable=False)
    repo = Column(sqlalchemy.Enum(PackageCloudRepos), nullable=False)
    package_name = Column(String, nullable=False)
    package_full_name = Column(String, nullable=False)
    package_version = Column(String, nullable=False)
    package_release = Column(String)
    package_type = Column(String, nullable=False)
    download_date = Column(DATE, nullable=False)
    download_count = Column(INTEGER, nullable=False)


def package_count(organization: PackageCloudOrganizations, repo_name: PackageCloudRepos,
                  package_cloud_api_token: str) -> int:
    result = requests.get(
        f"https://{package_cloud_api_token}:@packagecloud.io/api/v1/repos.json?include_collaborations=true")

    repo_list = json.loads(result.content)
    for repo in repo_list:
        if repo["fqname"] == f"{organization.name}/{repo_name.name}":
            return int(remove_suffix(repo['package_count_human'], PC_PACKAGE_COUNT_SUFFIX))
    raise ValueError(f"Repo name with the name {repo_name.name} could not be found on package cloud")


def fetch_and_save_package_cloud_stats(db_params: DbParams, package_cloud_api_token: str,
                                       organization: PackageCloudOrganizations, repo_name: PackageCloudRepos,
                                       parallel_count: int, parallel_exec_index: int, page_record_count: int,
                                       is_test: bool = False, save_records_with_download_count_zero: bool = False):
    '''It is called directly from pipeline. Packages are queried page by page from packagecloud. Packages are queried
     with the given index and queried packages are saved into database using
     fetch_and_save_package_stats_for_package_list method'''
    repo_package_count = package_count(organization=organization, repo_name=repo_name,
                                       package_cloud_api_token=package_cloud_api_token)
    session = db_session(db_params=db_params, is_test=is_test)
    page_index = parallel_exec_index + 1
    start = time.time()
    while is_page_in_range(page_index, repo_package_count, page_record_count):

        result = stat_get_request(
            package_list_with_pagination_request_address(package_cloud_api_token, page_index, organization, repo_name,
                                                         page_record_count),
            RequestType.package_cloud_list_package, session)
        package_info_list = json.loads(result.content)

        if len(package_info_list) > 0:
            page_index = page_index + parallel_count
        else:
            break
        fetch_and_save_package_stats_for_package_list(package_info_list, package_cloud_api_token, session,
                                                      save_records_with_download_count_zero, repo_name)

        session.commit()
    end = time.time()

    print("Elapsed Time in seconds: " + str(end - start))


def fetch_and_save_package_stats_for_package_list(package_info_list: List[Any], package_cloud_api_token: str, session,
                                                  save_records_with_download_count_zero: bool,
                                                  repo_name: PackageCloudRepos):
    '''Gets and saves the package statistics of the given packages'''
    for package_info in package_info_list:

        request_result = stat_get_request(
            package_historic_statistics_request_address(package_cloud_api_token, package_info['downloads_series_url']),
            RequestType.package_cloud_detail_query, session)
        if request_result.status_code != HTTPStatus.OK:
            continue
        download_stats = json.loads(request_result.content)
        for stat_date in download_stats['value']:
            download_date = datetime.strptime(stat_date, PC_DOWNLOAD_DATE_FORMAT).date()
            download_count = int(download_stats['value'][stat_date])
            if download_date != date.today() and not stat_records_exists(download_date,
                                                                         package_info['filename'],
                                                                         session) and (
                    is_download_count_eligible_for_save(download_count, save_records_with_download_count_zero)):
                pc_stats = PackageCloudDownloadStats(fetch_date=datetime.now(), repo=repo_name,
                                                     package_full_name=package_info['filename'],
                                                     package_name=package_info['name'],
                                                     package_version=package_info['version'],
                                                     package_release=package_info['release'],
                                                     package_type=package_info['type'],
                                                     download_date=download_date,
                                                     download_count=download_count)
                session.add(pc_stats)


def package_historic_statistics_request_address(package_cloud_api_token: str, detail_query_uri: str):
    return f"https://{package_cloud_api_token}:@packagecloud.io/{detail_query_uri}"


def package_list_with_pagination_request_address(package_cloud_api_token, page_index,
                                                 organization: PackageCloudOrganizations,
                                                 repo_name: PackageCloudRepos, page_record_count: int) -> str:
    return (f"https://{package_cloud_api_token}:@packagecloud.io/api/v1/repos/{organization.name}/{repo_name.name}"
            f"/packages.json?per_page={page_record_count}&page={page_index}")


def is_download_count_eligible_for_save(download_count: int, save_records_with_download_count_zero: bool) -> bool:
    return download_count > 0 or (download_count == 0 and save_records_with_download_count_zero)


def is_page_in_range(page_index: int, total_package_count: int, page_record_count: int):
    return ((page_index * page_record_count < total_package_count) or
            (page_index * page_record_count >= total_package_count > (page_index - 1) * page_record_count))


def stat_records_exists(download_date: date, package_full_name: str, session) -> bool:
    db_record = session.query(PackageCloudDownloadStats).filter_by(download_date=download_date,
                                                                   package_full_name=package_full_name).first()
    return db_record is not None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--organization', choices=[r.value for r in PackageCloudOrganizations])
    parser.add_argument('--repo_name', choices=[r.value for r in PackageCloudRepos])
    parser.add_argument('--db_user_name', required=True)
    parser.add_argument('--db_password', required=True)
    parser.add_argument('--db_host_and_port', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--package_cloud_api_token', required=True)
    parser.add_argument('--parallel_count', type=int, choices=range(1, 30), required=True, default=1)
    parser.add_argument('--parallel_exec_index', type=int, choices=range(0, 30), required=True, default=0)
    parser.add_argument('--page_record_count', type=int, choices=range(5, 101), required=True, default=0)
    parser.add_argument('--is_test', action="store_true")

    arguments = parser.parse_args()

    db_parameters = DbParams(user_name=arguments.db_user_name, password=arguments.db_password,
                             host_and_port=arguments.db_host_and_port, db_name=arguments.db_name)

    fetch_and_save_package_cloud_stats(db_parameters, arguments.package_cloud_api_token,
                                       PackageCloudOrganizations[arguments.organization],
                                       PackageCloudRepos(arguments.repo_name),
                                       arguments.parallel_count,
                                       arguments.parallel_exec_index, arguments.is_test)
