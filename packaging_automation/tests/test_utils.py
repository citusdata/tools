import difflib
from ..common_tool_methods import *


def are_strings_equal(expected_string: str, actual_str: str) -> bool:
    output_list = [li for li in difflib.ndiff(expected_string, actual_str) if li[0] != ' ']

    for output in output_list:
        if not (output.strip() == '+' or output.strip() == '-'):
            raise Exception(f"Actual and expected string are not same Diff:{''.join(output_list)} ")
    return True;


def generate_new_gpg_key(gpg_file_name: str):
    run(f"gpg --batch --generate-key {gpg_file_name}")


def generate_new_gpg_key_with_password():
    run(f"gpg --batch --generate-key {TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging_with_password.gpg")
