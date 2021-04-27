import pathlib2
import pytest

from ..packaging_warning_handler import *

TEST_BASE_PATH = pathlib2.Path(__file__).parent


def test_parse_ignore_lists():
    base_ignore_list, debian_ignore_list = parse_ignore_lists(
        f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml")
    assert len(base_ignore_list) == 8 and len(debian_ignore_list) == 2


def test_filter_warning_lines():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(lines)
        assert len(base_warning_lines) == 11 and len(debian_warning_lines) == 6


def test_get_base_warnings_to_be_raised():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(lines)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml")
        warnings_to_be_raised = get_warnings_to_be_raised(base_ignore_list, base_warning_lines)
        assert len(warnings_to_be_raised) == 1


def test_get_debian_warnings_to_be_raised():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(lines)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml")
        debian_warnings_to_be_raised = get_warnings_to_be_raised(debian_ignore_list,
                                                                 debian_warning_lines)
        assert len(debian_warnings_to_be_raised) == 1


def test_get_error_message():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output.txt", "r") as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(lines)
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml")
        base_warnings_to_be_raised = get_warnings_to_be_raised(base_ignore_list,
                                                               base_warning_lines)
        debian_warnings_to_be_raised = get_warnings_to_be_raised(debian_ignore_list,
                                                                 debian_warning_lines)
        error_message = get_error_message(debian_warnings_to_be_raised,
                                          base_warnings_to_be_raised)
        assert error_message == "Warning lines:\nWarning: Unhandled\nDebian Warning lines:\n" \
                                "citus-enterprise100_11.x86_64: W: invalid-date-format\n"


def test_validate_output():
    with open(f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output.txt", "r") as reader:
        output = reader.read()
        with pytest.raises(ValueError):
            validate_output(output,
                            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml")
