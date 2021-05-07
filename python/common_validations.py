import string_utils
from parameters_validation import parameter_validation
import re

CITUS_MINOR_VERSION_PATTERN = r"\d{1,2}\.\d{1,2}"
CITUS_PATCH_VERSION_PATTERN = CITUS_MINOR_VERSION_PATTERN + r".\d{1,2}"


@parameter_validation
def is_version(version: str):
    if not version:
        raise ValueError("version should be non-empty and should not be None")
    if not re.match(CITUS_PATCH_VERSION_PATTERN, version):
        raise ValueError(
            "version should include three level of digits separated by dots, e.g: 10.0.1")


@parameter_validation
def is_tag(tag: str):
    if not tag:
        raise ValueError("tag should be non-empty and should not be None")
    if not re.match(f"v{CITUS_PATCH_VERSION_PATTERN}", tag):
        raise ValueError(
            "tag should start with 'v' and should include three level of digits separated by dots, e.g: v10.0.1")


@parameter_validation
def is_email(email: str):
    if not string_utils.is_email(email):
        raise ValueError("Parameter is not in email format")
