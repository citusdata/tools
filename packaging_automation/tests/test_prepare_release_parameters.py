import argparse

import pytest

from ..prepare_release import validate_parameters


@pytest.mark.parametrize(
    "major_release,cherry_pick,earliest_date,schema_version,error",
    [
        (True, False, None, None, None),
        (False, False, None, None, None),
        (False, True, "2026.10.05", None, None),
        (False, False, None, "15.0-1", None),
        (True, True, None, None, "Cherry pick could be enabled only for patch release"),
        (True, False, "2026.10.05", None, "earliest_pr_date could not be used"),
        (True, False, None, "15.0-1", "schema_version could not be set"),
        (False, True, None, None, "earliest_pr_date parameter could  not be empty"),
    ],
)
def test_validate_parameters(
    major_release, cherry_pick, earliest_date, schema_version, error
):
    arguments = argparse.Namespace(
        cherry_pick_enabled=cherry_pick,
        earliest_pr_date=earliest_date,
        schema_version=schema_version,
    )
    if error is None:
        validate_parameters(major_release, arguments)
    else:
        with pytest.raises(ValueError, match=error):
            validate_parameters(major_release, arguments)
