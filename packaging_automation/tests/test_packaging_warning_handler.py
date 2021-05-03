import pathlib2
import pytest

from ..packaging_warning_handler import *

TEST_BASE_PATH = pathlib2.Path(__file__).parent


def test_parse_ignore_lists():
    base_ignore_list, debian_ignore_list = parse_ignore_lists(
        f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)
    assert len(base_ignore_list) == 8 and len(debian_ignore_list) == 2

    base_ignore_list, rpm_ignore_list = parse_ignore_lists(
        f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)
    assert len(base_ignore_list) == 8 and len(rpm_ignore_list) == 2


def test_deb_filter_warning_lines():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, package_specific_warning_lines = filter_warning_lines(lines, PackageType.deb)
        assert len(base_warning_lines) == 11 and len(package_specific_warning_lines) == 6


def test_rpm_filter_warning_lines():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_rpm.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, package_specific_warning_lines = filter_warning_lines(lines, PackageType.rpm)
        assert len(base_warning_lines) == 10 and len(package_specific_warning_lines) == 1


def test_get_base_warnings_to_be_raised():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, package_specific_warning_lines = filter_warning_lines(lines, PackageType.deb)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)
        base_warnings_to_be_raised = get_warnings_to_be_raised(base_ignore_list, base_warning_lines)
        assert len(base_warnings_to_be_raised) == 1


def test_get_debian_warnings_to_be_raised():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, package_specific_warning_lines = filter_warning_lines(lines, PackageType.deb)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)
        debian_warnings_to_be_raised = get_warnings_to_be_raised(debian_ignore_list,
                                                                 package_specific_warning_lines)
        assert len(debian_warnings_to_be_raised) == 1


def test_get_error_message():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(lines, PackageType.deb)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)
        base_warnings_to_be_raised = get_warnings_to_be_raised(base_ignore_list,
                                                               base_warning_lines)
        debian_warnings_to_be_raised = get_warnings_to_be_raised(debian_ignore_list,
                                                                 debian_warning_lines)
        error_message = get_error_message(base_warnings_to_be_raised, debian_warnings_to_be_raised, PackageType.deb)
        assert error_message == "Warning lines:\nWarning: Unhandled\nDebian Warning lines:\n" \
                                "citus-enterprise100_11.x86_64: W: invalid-date-format\n"

def test_get_error_message_empty_package_specific_errors():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb_only_base.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(lines, PackageType.deb)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)
        base_warnings_to_be_raised = get_warnings_to_be_raised(base_ignore_list,
                                                               base_warning_lines)
        debian_warnings_to_be_raised = get_warnings_to_be_raised(debian_ignore_list,
                                                                 debian_warning_lines)
        error_message = get_error_message(base_warnings_to_be_raised, debian_warnings_to_be_raised, PackageType.deb)
        assert error_message == "Warning lines:\nWarning: Unhandled\n"


def test_validate_output_deb():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt", "r") as reader:
        output = reader.read()
        with pytest.raises(ValueError):
            validate_output(output,
                            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml", PackageType.deb)


def test_validate_output_rpm():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_rpm.txt", "r") as reader:
        output = reader.read()
        with pytest.raises(ValueError):
            validate_output(output,
                            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore_without_rpm_rules.yml",
                            PackageType.rpm)


def test_validate_output_rpm_success():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_rpm_success.txt", "r") as reader:
        output = reader.read()
        validate_output(output,
                        f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
                        PackageType.rpm)
