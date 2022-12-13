import argparse

from .packaging_warning_handler import (validate_output)
from .common_tool_methods import (PackageType)
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_file', required=True)
    parser.add_argument('--ignore_file', required=True)
    parser.add_argument('--package_type', choices=[p.name for p in PackageType], required=True)

    args = parser.parse_args()
    build_output = Path(args.output_file).read_text(encoding="utf-8")
    validate_output(build_output, args.ignore_file, PackageType[args.package_type])
