from datetime import datetime

from attr import dataclass
from enum import Enum

@dataclass()
class ProjectDetails:
    name: str
    version_suffix: str
    github_repo_name: str

class SupportedProjects(Enum):
    citus = ProjectDetails(name="citus", version_suffix="citus", github_repo_name="citus")
    citus_enterprise = ProjectDetails(name="citus-enterprise", version_suffix="citus",
                                      github_repo_name="citus-enterprise")
    pg_auto_failover = ProjectDetails(name="pg-auto-failover", version_suffix="",
                                      github_repo_name="pg_auto_failover")

@dataclass
class PackagePropertiesParams:
    project_name: str
    project_version: str
    fancy: bool
    fancy_version_number: int
    microsoft_email: str = ""
    name_surname: str = ""
    latest_changelog: str = ""
    changelog_date: datetime = datetime.now()


param: bool = "False"

# print(param)

print(SupportedProjects["citus"].name)
