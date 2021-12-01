import os
import re
from enum import Enum
from typing import List, Tuple

import yaml

from .common_tool_methods import (
    PackageType, DEFAULT_ENCODING_FOR_FILE_HANDLING, DEFAULT_UNICODE_ERROR_HANDLER)


class PackagingWarningIgnoreType(Enum):
    base = 1
    debian = 2
    rpm = 3


def validate_output(output: str, ignore_file_path: str, package_type: PackageType):
    base_ignore_list, package_type_specific_ignore_list = parse_ignore_lists(
        ignore_file_path, package_type)

    output_lines = output.splitlines()
    warning_lines, package_type_specific_warning_lines = filter_warning_lines(
        output_lines, package_type)
    print("Checking build output for warnings")
    print("Package Type:" + package_type.name)
    print(
        f"Package type specific warnings:{package_type_specific_warning_lines}")

    base_warnings_to_be_raised = get_warnings_to_be_raised(
        base_ignore_list, warning_lines)
    package_type_specific_warnings_to_be_raised = get_warnings_to_be_raised(package_type_specific_ignore_list,
                                                                            package_type_specific_warning_lines)

    print(
        f"Package type specific ignore list:{package_type_specific_ignore_list}")
    print(
        f"Package type specific warnings to be raised:{package_type_specific_warnings_to_be_raised}")
    print(f"Base warnings to be raised:{base_warnings_to_be_raised}")

    if len(base_warnings_to_be_raised) > 0 or len(package_type_specific_warnings_to_be_raised) > 0:
        error_message = get_error_message(base_warnings_to_be_raised, package_type_specific_warnings_to_be_raised,
                                          package_type)
        print(f"Build output check failed. Error Message: \n{error_message}")
        raise ValueError(error_message)
    print("Build output check completed succesfully. No warnings")


def filter_warning_lines(output_lines: List[str], package_type: PackageType) -> Tuple[List[str], List[str]]:
    rpm_warning_summary = r"\d+ packages and \d+ specfiles checked; \d+ errors, \d+ warnings."
    rpm_lintian_starter = 'Executing "/usr/bin/rpmlint -f /rpmlintrc'
    debian_lintian_starter = "Now running lintian"
    lintian_warning_error_pattern = r".*: [W|E]: .*"

    base_warning_lines = []
    package_specific_warning_lines = []
    is_deb_warning_line = False
    is_rpm_warning_line = False
    for output_line in output_lines:

        if package_type == PackageType.deb:
            if debian_lintian_starter in output_line:
                is_deb_warning_line = True
            elif "warning" in output_line.lower() or is_deb_warning_line:
                if is_deb_warning_line:
                    match = re.match(
                        lintian_warning_error_pattern, output_line)
                    if match:
                        package_specific_warning_lines.append(output_line)
                    else:
                        is_deb_warning_line = False
                else:
                    base_warning_lines.append(output_line)
        else:
            if rpm_lintian_starter in output_line:
                is_rpm_warning_line = True
            elif "warning" in output_line.lower() or is_rpm_warning_line:
                if is_rpm_warning_line and re.match(
                        rpm_warning_summary, output_line):
                    is_rpm_warning_line = False
                    continue
                if re.match(lintian_warning_error_pattern, output_line):
                    package_specific_warning_lines.append(output_line)
                else:
                    base_warning_lines.append(output_line)
            else:
                continue

    return base_warning_lines, package_specific_warning_lines


def parse_ignore_lists(ignore_file_path: str, package_type: PackageType):
    base_ignore_list = []
    packaging_warning_type = PackagingWarningIgnoreType.debian if package_type == PackageType.deb \
        else PackagingWarningIgnoreType.rpm
    package_type_specific_ignore_list = []
    with open(ignore_file_path, "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        yaml_content = yaml.load(reader, yaml.BaseLoader)
    if PackagingWarningIgnoreType.base.name in yaml_content:
        base_ignore_list = yaml_content[PackagingWarningIgnoreType.base.name]
    if packaging_warning_type.name in yaml_content:
        package_type_specific_ignore_list = yaml_content[packaging_warning_type.name]

    return base_ignore_list, package_type_specific_ignore_list


def get_warnings_to_be_raised(ignore_list: List[str], warning_lines: List[str]) -> List[str]:
    warnings_to_be_raised = []
    for warning_line in warning_lines:
        has_ignore_match = False
        for ignore_line in ignore_list:
            if re.match(ignore_line, warning_line):
                has_ignore_match = True
                break
        if not has_ignore_match:
            warnings_to_be_raised.append(warning_line)
    return warnings_to_be_raised


def get_error_message(base_warnings_to_be_raised: List[str], package_specific_warnings_to_be_raised: List[str],
                      package_type: PackageType) -> str:
    error_message = ""
    package_type_specific_header = "Debian Warning lines:\n" if package_type == PackageType.deb \
        else "Rpm Warning lines:\n"
    error_message = f'{error_message}Warning lines:\n{os.linesep.join(base_warnings_to_be_raised)}\n' if len(
        base_warnings_to_be_raised) > 0 else error_message
    error_message = f"{error_message}{package_type_specific_header}" \
                    f"{os.linesep.join(package_specific_warnings_to_be_raised)}\n" \
        if len(package_specific_warnings_to_be_raised) > 0 else error_message

    return error_message
