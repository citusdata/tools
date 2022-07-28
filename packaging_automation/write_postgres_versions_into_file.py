import argparse

from .citus_package import (write_postgres_versions_into_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--project_version', required=True)
    parser.add_argument('--input_files_dir', required=True)

    args = parser.parse_args()
    write_postgres_versions_into_file(args.input_files_dir,args.project_version)
