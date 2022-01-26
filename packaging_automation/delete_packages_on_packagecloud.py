import requests
import json
from datetime import datetime
import argparse
from enum import Enum

PAGE_RECORD_COUNT = 100


class PackageRepository(Enum):
    community_nightlies = "community-nightlies"
    enterprise_nightlies = "enterprise-nightlies"


def delete_packages(repo: PackageRepository, package_cloud_api_token: str) -> None:
    url_prefix = f"https://{package_cloud_api_token}:@packagecloud.io"

    successful_count = 0
    error_count = 0
    end_of_limits_reached = False
    while True:
        list_url = (f"{url_prefix}/api/v1/repos/citusdata/{repo.value}"
                    f"/packages.json?per_page={PAGE_RECORD_COUNT}&page=0")
        result = requests.get(list_url)
        package_info_list = json.loads(result.content)
        if len(package_info_list) == 0 or end_of_limits_reached:
            break
        for package_info in package_info_list:
            package_upload_date = datetime.strptime(package_info['created_at'], "%Y-%m-%dT%H:%M:%S.000Z")
            diff = datetime.now() - package_upload_date
            if diff.days > 10:
                delete_url = f"{url_prefix}{package_info['destroy_url']}"

                del_result = requests.delete(delete_url)
                if del_result.status_code == 200:
                    print(f"{package_info['filename']} deleted successfully")
                    successful_count = successful_count + 1
                else:
                    error_count = error_count + 1
                    print(
                        f"{package_info['filename']} could not be deleted. Error Code:{del_result.status_code} "
                        f"Error message:{del_result.content}")
            else:
                end_of_limits_reached = True

    print("Deletion Stats")
    print(f"Succesful Count: {successful_count}")
    print(f"Error Count:{error_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--package_repo', choices=[r.value for r in PackageRepository], required=True)
    parser.add_argument('--package_cloud_api_token', required=True)
    args = parser.parse_args()

    delete_packages(repo=PackageRepository(args.package_repo), package_cloud_api_token=args.package_cloud_api_token)
