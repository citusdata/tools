import os

import pathlib2

from ..common_tool_methods import (
    run, DEFAULT_UNICODE_ERROR_HANDLER, DEFAULT_ENCODING_FOR_FILE_HANDLING)
from ..update_pgxn import update_meta_json, update_pkgvars

BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
TEST_BASE_PATH = f"{BASE_PATH}/packaging_test"
PROJECT_VERSION = "10.0.3"
PROJECT_NAME = "citus"
TEMPLATE_PATH = f"{BASE_PATH}/packaging_automation/templates/pgxn"


def setup_module():
    if not os.path.exists("packaging_test"):
        run(
            "git clone --branch pgxn-citus https://github.com/citusdata/packaging.git packaging_test")


def teardown_module():
    if os.path.exists("packaging_test"):
        run("rm -r packaging_test")


def test_update_meta_json():
    update_meta_json(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    with open(f"{TEST_BASE_PATH}/META.json", "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[4] == f'   "version": "{PROJECT_VERSION}",'
        assert lines[12] == f'         "version": "{PROJECT_VERSION}"'
        assert len(lines) == 54


def test_update_pkgvars():
    update_pkgvars(PROJECT_VERSION, TEMPLATE_PATH, TEST_BASE_PATH)
    with open(f"{TEST_BASE_PATH}/pkgvars", "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        content = reader.read()
        lines = content.splitlines()
        assert lines[2] == f'pkglatest={PROJECT_VERSION}'
        assert len(lines) == 4
