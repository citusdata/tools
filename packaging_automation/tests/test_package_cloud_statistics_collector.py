import os
from sqlalchemy import text, create_engine, table
from ..common_tool_methods import stat_get_request
from ..dbconfig import (Base, db_session, DbParams, db_connection_string)
from ..package_cloud_statistics_collector import (fetch_and_save_package_cloud_stats, PackageCloudRepos,
                                                  PackageCloudOrganizations, package_count, PackageCloudDownloadStats,
                                                  package_list_with_pagination_request_address, RequestType,
                                                  is_ignored_package)
import json

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")
PACKAGE_CLOUD_API_TOKEN = os.getenv("PACKAGE_CLOUD_API_TOKEN")
PACKAGE_CLOUD_ADMIN_API_TOKEN = os.getenv("PACKAGE_CLOUD_ADMIN_API_TOKEN")
REPO = PackageCloudRepos.azure
ORGANIZATION = PackageCloudOrganizations.citusdata
db_parameters = DbParams(user_name=DB_USER_NAME, password=DB_PASSWORD, host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME)
# 7 Records are fetched for each package from package cloud. To check the record count, we need to multiply package
# count with 7
PACKAGE_SAVED_HISTORIC_RECORD_COUNT = 7


def test_fetch_and_save_package_cloud_stats():
    db = create_engine(db_connection_string(db_params=db_parameters, is_test=True))
    db.execute(text(f'DROP TABLE IF EXISTS {PackageCloudDownloadStats.__tablename__}'))
    session = db_session(db_params=db_parameters, is_test=True)
    page_record_count = 3
    parallel_count = 3

    filtered_package_count = get_filtered_package_count(session)

    for index in range(0, parallel_count):
        fetch_and_save_package_cloud_stats(package_cloud_api_token=PACKAGE_CLOUD_API_TOKEN,
                                           package_cloud_admin_api_token=PACKAGE_CLOUD_ADMIN_API_TOKEN,
                                           organization=ORGANIZATION,
                                           repo_name=REPO, db_params=db_parameters, parallel_count=parallel_count,
                                           parallel_exec_index=index, page_record_count=page_record_count,
                                           is_test=True, save_records_with_download_count_zero=True)

    records = session.query(PackageCloudDownloadStats).all()

    assert len(records) == filtered_package_count * PACKAGE_SAVED_HISTORIC_RECORD_COUNT


def get_filtered_package_count(session) -> int:
    # Since package count for our test repo is lower than 100, we get the total package details by getting all the
    # packages in one call
    result = stat_get_request(
        package_list_with_pagination_request_address(PACKAGE_CLOUD_API_TOKEN, 1, ORGANIZATION, REPO, 100),
        RequestType.package_cloud_list_package, session)
    package_info_list = json.loads(result.content)
    package_list = list(filter(
        lambda p: not is_ignored_package(p["name"]), package_info_list))
    return len(package_list)
