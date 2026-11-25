import json
import os

import pathlib2
import pytest

from ..common_tool_methods import (
    DEFAULT_UNICODE_ERROR_HANDLER,
    DEFAULT_ENCODING_FOR_FILE_HANDLING,
)
from ..update_pgxn import parse_arguments, update_meta_json, update_pkgvars

BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])
PROJECT_VERSION = "14.3.0"
TEMPLATE_PATH = f"{BASE_PATH}/packaging_automation/templates/pgxn"


def read(path):
    with open(
        path,
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        return reader.read()


def test_meta_json_requires_the_lowest_postgres_major_of_the_release_line(tmp_path):
    update_meta_json(PROJECT_VERSION, TEMPLATE_PATH, str(tmp_path), 16)

    meta = json.loads(read(f"{tmp_path}/META.json"))
    assert meta["version"] == PROJECT_VERSION
    assert meta["provides"]["citus"]["version"] == PROJECT_VERSION
    assert meta["prereqs"]["runtime"]["requires"]["PostgreSQL"] == "16.0.0"


@pytest.mark.parametrize(
    "pg_min_major_args",
    [[], ["--pg_min_major", "9"], ["--pg_min_major", "16.0"]],
)
def test_pgxn_update_refuses_a_missing_or_invalid_postgres_minimum(
    pg_min_major_args,
):
    with pytest.raises(SystemExit):
        parse_arguments(
            ["--prj_ver", PROJECT_VERSION, "--gh_token", "unused", *pg_min_major_args]
        )


def test_update_pkgvars(tmp_path):
    update_pkgvars(PROJECT_VERSION, TEMPLATE_PATH, str(tmp_path))

    lines = read(f"{tmp_path}/pkgvars").splitlines()
    assert lines[2] == f"pkglatest={PROJECT_VERSION}"
    assert len(lines) == 3
