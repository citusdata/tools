from github import Github, Repository, PullRequest
from datetime import datetime

from typing import List
import subprocess
import uuid

g = Github("6df6f95934896fd559e4b2f7eb630c49f8dad560")
repository = g.get_repo(f"citusdata/citus")

