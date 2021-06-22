import shlex
from subprocess import Popen, PIPE, STDOUT

import gnupg
import os, pathlib2
import subprocess
import base64

TEST_BASE_PATH = os.getenv("BASE_PATH", default=pathlib2.Path(__file__).parents[2])


def run(command, *args, **kwargs):
    result = subprocess.run(shlex.split(command), *args, check=True, **kwargs)
    return result


def generate_new_gpg_key(gpg_file_name: str):
    run(f"gpg --batch --generate-key {gpg_file_name}")


# generate_new_gpg_key(f"{TEST_BASE_PATH}/packaging_automation/tests/files/gpg/packaging.gpg")

def get_secret_key_by_fingerprint_with_password(fingerprint: str, passphrase: str) -> str:
    # When getting gpg key if gpg key is stored with password and if given passphrase is wrong, timeout exception is
    # thrown.
    gpg = gnupg.GPG()

    private_key = gpg.export_keys(fingerprint, secret=True, passphrase=passphrase)
    if private_key:
        return base64.b64encode(private_key.encode("ascii")).decode("ascii")
    else:
        raise ValueError(
            f"Error while getting key. Most probably packaging key is stored with password. "
            f"Please check the password and try again")

#
gpg = gnupg.GPG()
fingerprint = "F035E21234D3C222A7B2AF25CBCBA87D6F30B896"
private_key = gpg.export_keys(fingerprint, secret=True, passphrase="123")
print(private_key)
print(base64.b64encode(private_key.encode("ascii")).decode("ascii"))

# print(get_secret_key_by_fingerprint_with_password("F035E21234D3C222A7B2AF25CBCBA87D6F30B896","123"))
