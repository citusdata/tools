import argparse
import json
import os

from .test_citus_package import (get_postgres_versions_from_matrix_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prj_ver', required=True)

    args = parser.parse_args()
    postgres_versions = get_postgres_versions_from_matrix_file(args.prj_ver)
    os.environ["POSTGRES_VERSIONS"] = json.dumps(postgres_versions)
    print(os.getenv("POSTGRES_VERSIONS"))
