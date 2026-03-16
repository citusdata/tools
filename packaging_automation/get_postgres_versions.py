import argparse
import json
import requests

from typing import List

from .common_tool_methods import (
    get_supported_postgres_release_versions,
)

POSTGRES_MATRIX_FILE = "postgres-matrix.yml"
POSTGRES_MATRIX_WEB_ADDRESS = "https://raw.githubusercontent.com/citusdata/packaging/all-citus/postgres-matrix.yml"

def get_postgres_versions_from_matrix_file(project_version: str) -> List[str]:
    r = requests.get(POSTGRES_MATRIX_WEB_ADDRESS, allow_redirects=True, timeout=60)

    with open(POSTGRES_MATRIX_FILE, "wb") as writer:
        writer.write(r.content)
    pg_versions = get_supported_postgres_release_versions(
        POSTGRES_MATRIX_FILE, project_version
    )

    return pg_versions

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_version", required=True)

    args = parser.parse_args()
    postgres_versions = get_postgres_versions_from_matrix_file(args.project_version)
    print(json.dumps(postgres_versions))
