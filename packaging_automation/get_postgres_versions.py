import argparse
import json

from .test_citus_package import (get_postgres_versions_from_matrix_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_version', required=True)

    args = parser.parse_args()
    postgres_versions = get_postgres_versions_from_matrix_file(args.project_version)
    print(json.dumps(postgres_versions))
