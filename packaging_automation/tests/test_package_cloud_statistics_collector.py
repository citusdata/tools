import os
from sqlalchemy import text, create_engine
from ..dbconfig import (Base, db_session, DbParams, db_connection_string)
from ..package_cloud_statistics_collector import (fetch_and_save_package_cloud_stats, PackageCloudRepos,
                                                  PackageCloudOrganizations, package_count, PackageCloudDownloadStats)

DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST_AND_PORT = os.getenv("DB_HOST_AND_PORT")
DB_NAME = os.getenv("DB_NAME")
PACKAGE_CLOUD_API_TOKEN = os.getenv("PACKAGE_CLOUD_API_TOKEN")
REPO = PackageCloudRepos.azure
ORGANIZATION = PackageCloudOrganizations.citusdata
db_parameters = DbParams(user_name=DB_USER_NAME, password=DB_PASSWORD, host_and_port=DB_HOST_AND_PORT, db_name=DB_NAME)
# 7 Records are fetched for each package from package cloud. To check the record count, we need to multiply package
# count with 7
PACKAGE_SAVED_HISTORIC_RECORD_COUNT = 7


def test_fetch_and_save_package_cloud_stats():
    db = create_engine(db_connection_string(db_params=db_parameters, is_test=True))
    db.execute(text(f'DROP TABLE IF EXISTS {PackageCloudDownloadStats.__tablename__}'))
    pack_count = package_count(ORGANIZATION, REPO, PACKAGE_CLOUD_API_TOKEN)
    session = db_session(db_params=db_parameters, is_test=True)
    page_record_count = 3
    parallel_count = 3
    for index in range(0, parallel_count):
        fetch_and_save_package_cloud_stats(package_cloud_api_token=PACKAGE_CLOUD_API_TOKEN, organization=ORGANIZATION,
                                           repo_name=REPO, db_params=db_parameters, parallel_count=parallel_count,
                                           parallel_exec_index=index, page_record_count=page_record_count,
                                           is_test=True, save_records_with_download_count_zero=True)

    records = session.query(PackageCloudDownloadStats).all()
    assert len(records) == pack_count * PACKAGE_SAVED_HISTORIC_RECORD_COUNT