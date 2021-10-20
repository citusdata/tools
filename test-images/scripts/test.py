import subprocess
import shlex
from enum import Enum
import os
import re

CITUS_VERSION = os.getenv("CITUS_VERSION")
POSTGRES_VERSION = os.getenv("POSTGRES_VERSION")


def run_with_output(command, *args, **kwargs):
    # this method's main objective is to return output. Therefore it is caller's responsibility to handle
    # success status
    # pylint: disable=subprocess-run-check
    result = subprocess.run(shlex.split(command), *args, capture_output=True, **kwargs)
    return result


class VerificationType(Enum):
    equals = 1
    contains = 2


def verify(output, expected_result, verification_type: VerificationType = VerificationType.equals) -> bool:
    if verification_type == VerificationType.equals:
        return_value = output == expected_result
    elif VerificationType.contains:
        return_value = expected_result in output
    else:
        return_value = False
    return return_value


def verify_output(result, expected_result) -> bool:
    if result.returncode != 0:
        print(result.stderr.decode("utf-8"))
        print(f"Error: Error Code : {result.returncode}")
        return False
    output = result.stdout.decode("utf-8")
    print("Result:")
    print(output)
    if re.match(expected_result, repr(output)):
        print(output)
        return True

    print(rf"Expected Result: {expected_result}")
    print(rf"Actual Result: {repr(output)}")
    return False


def test_citus():
    assert verify_output(run_with_output('pg_ctl -D citus -o "-p 9700" -l citus/citus_logfile start'),
                         r"^'waiting for server to start.... done\\nserver started\\n'$")
    assert verify_output(run_with_output('psql -p 9700 -c "CREATE EXTENSION citus;"'), r"^'CREATE EXTENSION\\n'$")
    assert verify_output(run_with_output('psql -p 9700 -c "select version();"'),
                         rf".*PostgreSQL {POSTGRES_VERSION}.* on x86_64-pc-linux-gnu, compiled by gcc \(.*")
    # Since version info for ol and el 7 contains undefined, undefined was needed to add as expected param for pc
    assert verify_output(run_with_output('psql -p 9700 -c "select citus_version();"'),
                         rf".*Citus {CITUS_VERSION} on x86_64-(pc|unknown)-linux-gnu, compiled by gcc.*")
