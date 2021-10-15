import subprocess
import shlex
from enum import Enum
import os

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
        return output == expected_result
    elif VerificationType.contains:
        return expected_result in output
    else:
        return False


def verify_output(result, expected_result, verification_type: VerificationType = VerificationType.equals) -> bool:
    if result.returncode != 0:
        print(result.stderr.decode("utf-8"))
        print(f"Error: Error Code : {result.returncode}")
        return False
    else:
        output = result.stdout.decode("utf-8")
        if verify(output, expected_result, verification_type):
            print(output)
            return True
        else:
            print(f"Expected Result: {expected_result}")
            print(f"Actual Result: {output}")
            return False


def test_citus():
    assert verify_output(run_with_output('pg_ctl -D citus -o "-p 9700" -l citus/citus_logfile start'),
                         "waiting for server to start.... done\nserver started\n")
    assert verify_output(run_with_output('psql -p 9700 -c "CREATE EXTENSION citus;"'), 'CREATE EXTENSION\n')
    print(run_with_output('psql -p 9700 -c "select version();"'))
    assert verify_output(run_with_output('psql -p 9700 -c "select citus_version();"'),
                         f" Citus {CITUS_VERSION} on x86_64-pc-linux-gnu, compiled by gcc", VerificationType.contains)

