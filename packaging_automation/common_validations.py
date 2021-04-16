import string_utils
from parameters_validation import parameter_validation
import re


@parameter_validation
def is_version(version: str):
    if version is None or not version:
        raise ValueError("version should be non-empty and should not be None")
    if not re.match(r"\d+\.\d+\.\d+$", version):
        raise ValueError(
            "version should include 3 levels of versions consists of numbers  separated with dots. e.g: 10.0.1")


@parameter_validation
def is_tag(tag: str):
    if tag is None or not tag:
        raise ValueError("tag  should be non-empty and should not be None")
    if not re.match(r"v\d+\.\d+\.\d+$", tag):
        raise ValueError(
            "tag  should start with v and should include 3 levels of versions consists of numbers " +
            "separated with dots. e.g: v10.0.1")


@parameter_validation
def is_email(email: str):
    if not string_utils.is_email(email):
        raise ValueError("Parameter is not in email format")
