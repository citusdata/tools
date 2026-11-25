import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pathlib2
import requests
from dotenv import dotenv_values
from github import Github

from .common_tool_methods import (
    get_template_environment,
    write_to_file,
    run_with_output,
    initialize_env,
    create_pr_with_repo,
    remove_cloned_code,
    DEFAULT_ENCODING_FOR_FILE_HANDLING,
    DEFAULT_UNICODE_ERROR_HANDLER,
)

REPO_OWNER = "citusdata"
PROJECT_NAME = "docker"
MAIN_BRANCH = "master"
CHECKOUT_DIR = "docker_temp"

# PostgreSQL majors this helper has templates for; exposing a major here does
# not publish it because citusdata/docker workflow matrices decide publication.
SUPPORTED_POSTGRES_MAJORS = (16, 17, 18, 19)

LATEST_TEMPLATE = "latest/latest.tmpl.dockerfile"
DOCKER_COMPOSE_TEMPLATE = "latest/docker-compose.tmpl.yml"
ALPINE_TEMPLATE = "alpine/alpine.tmpl.dockerfile"

LATEST_OUTPUT = "Dockerfile"
DOCKER_COMPOSE_OUTPUT = "docker-compose.yml"
ALPINE_OUTPUT = "alpine/Dockerfile"
PKGVARS_FILE = "pkgvars"
CHANGELOG_FILE = "CHANGELOG.md"

POSTGRES_VERSION_PATTERN = re.compile(r"^(\d+)(?:\.\d+|(beta|rc)\d+)$")
PKGVARS_POSTGRES_LINE_PATTERN = re.compile(r"^postgres_(\d+)_version=(.*)$")
DOCKERFILE_BASE_PATTERN = re.compile(r"^FROM postgres:(\S+)\s*$", re.MULTILINE)
DOCKERFILE_VERSION_PATTERN = re.compile(r"^ARG VERSION=(\S+)\s*$", re.MULTILINE)
DOCKERFILE_DEB_REVISION_PATTERN = re.compile(
    r"^ENV CITUS_VERSION \$\{VERSION\}\.citus-(\d+)\s*$", re.MULTILINE
)
# Only stable Citus releases get Docker images, so pre-release tags are rejected.
SOURCE_TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
DEB_VERSION_PATTERN = re.compile(r"^(\d+\.\d+\.\d+)\.citus-(\d+)$")

BASE_PATH = pathlib2.Path(__file__).parent.absolute()
TEMPLATE_PATH = f"{BASE_PATH}/templates/docker"

# Debian-based images install Citus from the community APT repository on Debian trixie.
DEFAULT_APT_REPOSITORY = "https://packagecloud.io/citusdata/community"
DEFAULT_APT_DISTRIBUTION = "debian/trixie"
# Only the Alpine image is multi-arch, and it builds Citus from source.
DEB_ARCHITECTURE = "amd64"
DEFAULT_APT_CHECK_ATTEMPTS = 5
DEFAULT_APT_RETRY_INTERVAL_SECONDS = 60

# The Alpine image builds Citus from the source archive of the release tag.
CITUS_REPOSITORY_URL = "https://github.com/citusdata/citus.git"


class PackageNotPublishedError(Exception):
    pass


class SourceTagNotFoundError(PackageNotPublishedError):
    pass


@dataclass(frozen=True)
class CitusRelease:
    """Exact identity of a published Citus release: the source tag Alpine builds from and
    the Debian package version the Debian-based images install."""

    source_tag: str
    deb_version: str

    @property
    def version(self) -> str:
        return self.source_tag[1:]

    @property
    def minor_version(self) -> str:
        return ".".join(self.version.split(".")[:2])

    @property
    def deb_revision(self) -> str:
        return self.deb_version.rsplit("-", 1)[1]

    @property
    def is_patch_release(self) -> bool:
        return self.version.split(".")[2] != "0"


@dataclass
class DockerUpdate:
    written_files: List[str] = field(default_factory=list)
    untouched_majors: List[int] = field(default_factory=list)
    latest_major: int = 0
    changes: List[str] = field(default_factory=list)
    citus_version_changed: bool = False


@dataclass
class DockerUpdatePlan:
    targets: Dict[int, str]
    docker_files: Dict[str, str]
    base_changes: Dict[int, str]
    update: DockerUpdate
    has_changes: bool


def parse_citus_release(source_tag: str, deb_version: str) -> CitusRelease:
    if not SOURCE_TAG_PATTERN.match(source_tag):
        raise ValueError(
            f"Invalid Citus source tag '{source_tag}'. Docker images are built for stable tags like v14.3.0 only."
        )
    deb_match = DEB_VERSION_PATTERN.match(deb_version)
    if not deb_match:
        raise ValueError(
            f"Invalid Debian package version '{deb_version}'. Expected the published version, e.g. 14.3.0.citus-1."
        )
    if deb_match.group(1) != source_tag[1:]:
        raise ValueError(
            f"Debian package version {deb_version} does not belong to source tag {source_tag}."
        )
    return CitusRelease(source_tag=source_tag, deb_version=deb_version)


def postgres_template(postgres_major: int) -> str:
    return f"postgres-{postgres_major}/postgres-{postgres_major}.tmpl.dockerfile"


def postgres_output(postgres_major: int) -> str:
    return f"postgres-{postgres_major}/Dockerfile"


def normalize_postgres_version(postgres_version: str) -> str:
    # PGDG apt form uses tilde (19~rc1); official postgres Docker tags drop it (19rc1).
    return postgres_version.strip().replace("~", "")


def postgres_major_of(postgres_version: str) -> int:
    match = POSTGRES_VERSION_PATTERN.match(postgres_version)
    if not match:
        raise ValueError(
            f"Invalid PostgreSQL version '{postgres_version}'. Expected forms like 18.4, 19beta3 or 19rc1."
        )
    return int(match.group(1))


def is_prerelease_postgres_version(postgres_version: str) -> bool:
    match = POSTGRES_VERSION_PATTERN.match(postgres_version)
    return bool(match and match.group(2))


def _extract_postgres_version_pairs(value: str) -> List[Tuple[Optional[int], str]]:
    value = value.strip()
    if not (value.startswith("{") or value.startswith("[")):
        return [
            (None, normalize_postgres_version(version))
            for version in re.split(r"[,\s]+", value)
            if version
        ]
    parsed = json.loads(value)
    if isinstance(parsed, dict):
        raw_pairs = [(int(major), version) for major, version in parsed.items()]
    elif isinstance(parsed, list):
        raw_pairs = [(None, version) for version in parsed]
    else:
        raise ValueError("JSON --postgres_versions must be an object or array")
    pairs = []
    for declared_major, version in raw_pairs:
        if not isinstance(version, str):
            raise ValueError(
                f"Invalid PostgreSQL version {version!r}; expected a string."
            )
        pairs.append((declared_major, normalize_postgres_version(version)))
    return pairs


def parse_postgres_versions(value: str) -> Dict[int, str]:
    """Parses Docker base PostgreSQL versions from a comma/space list ("16.14,17.10,18.4"),
    a JSON array (["16.14", ...]), or a JSON mapping ({"16": "16.14", ...})."""
    postgres_versions: Dict[int, str] = {}
    for declared_major, version in _extract_postgres_version_pairs(value):
        major = postgres_major_of(version)
        if declared_major is not None and declared_major != major:
            raise ValueError(f"{version} is not a PostgreSQL {declared_major} version")
        if major in postgres_versions:
            raise ValueError(f"PostgreSQL {major} is listed more than once")
        postgres_versions[major] = version
    if not postgres_versions:
        raise ValueError("At least one Docker base PostgreSQL version is required")
    return postgres_versions


def ensure_postgres_majors_supported(postgres_majors):
    unsupported = sorted(set(postgres_majors) - set(SUPPORTED_POSTGRES_MAJORS))
    if unsupported:
        raise ValueError(
            f"PostgreSQL {', '.join(str(m) for m in unsupported)} has no Docker template in this tools release. "
            f"Supported majors: {', '.join(str(m) for m in SUPPORTED_POSTGRES_MAJORS)}."
        )


def read_file(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    with open(
        path,
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        return reader.read()


def read_pkgvars_postgres_versions(exec_path: str) -> Dict[int, str]:
    """Returns the Docker base PostgreSQL version of every major declared in pkgvars."""
    config = dotenv_values(f"{exec_path}/{PKGVARS_FILE}")
    postgres_versions = {}
    for key, value in config.items():
        if value is None:
            continue
        match = PKGVARS_POSTGRES_LINE_PATTERN.match(f"{key}={value}")
        if match:
            postgres_versions[int(match.group(1))] = value
    return postgres_versions


def select_target_versions(
    requested_versions: Dict[int, str], pkgvars_versions: Dict[int, str]
) -> Dict[int, str]:
    """A release only refreshes majors the docker repository already ships. Adding or removing
    a PostgreSQL major is a reviewed structural change, never a side effect of a release update.
    """
    ensure_postgres_majors_supported(requested_versions)
    unknown = sorted(set(requested_versions) - set(pkgvars_versions))
    if unknown:
        raise ValueError(
            f"PostgreSQL {', '.join(str(m) for m in unknown)} has no postgres_<major>_version entry in the docker "
            f"repository's {PKGVARS_FILE}. Adding a PostgreSQL major to Docker is a manual, reviewed change."
        )
    return requested_versions


def read_latest_postgres_major(exec_path: str) -> int:
    """Returns the PostgreSQL major the repository's latest image is currently built on."""
    content = read_file(f"{exec_path}/{LATEST_OUTPUT}") or ""
    match = DOCKERFILE_BASE_PATTERN.search(content)
    if not match:
        raise ValueError(
            f"Could not find the 'FROM postgres:<version>' line in {exec_path}/{LATEST_OUTPUT}"
        )
    return postgres_major_of(match.group(1))


def select_latest_postgres_major(
    postgres_versions: Dict[int, str],
    current_latest_major: int,
    requested_latest_major: Optional[int] = None,
) -> int:
    """The latest and alpine images keep their current PostgreSQL major unless explicitly
    overridden, and never move to a prerelease base.
    """
    latest_major = (
        requested_latest_major
        if requested_latest_major is not None
        else current_latest_major
    )
    if latest_major not in postgres_versions:
        raise ValueError(
            f"The latest image would use PostgreSQL {latest_major}, which is not among the updated majors "
            f"{sorted(postgres_versions)}. Select the latest major explicitly."
        )
    if is_prerelease_postgres_version(postgres_versions[latest_major]):
        raise ValueError(
            f"The latest image cannot use the prerelease base postgres:{postgres_versions[latest_major]}."
        )
    return latest_major


def render_docker_template(
    template_file: str, release: CitusRelease, postgres_version: str = ""
) -> str:
    template = get_template_environment(TEMPLATE_PATH).get_template(template_file)
    rendered = template.render(
        project_version=release.version,
        project_minor_version=release.minor_version,
        deb_revision=release.deb_revision,
        postgres_version=postgres_version,
    )
    return f"{rendered}\n"


def write_docker_file(exec_path: str, relative_path: str, content: str):
    dest_file_name = f"{exec_path}/{relative_path}"
    os.makedirs(os.path.dirname(dest_file_name), exist_ok=True)
    write_to_file(content, dest_file_name)


def update_pkgvars(exec_path: str, postgres_versions: Dict[int, str]):
    lines = (read_file(f"{exec_path}/{PKGVARS_FILE}") or "").splitlines()
    for index, line in enumerate(lines):
        match = PKGVARS_POSTGRES_LINE_PATTERN.match(line)
        if match and int(match.group(1)) in postgres_versions:
            major = int(match.group(1))
            lines[index] = f"postgres_{major}_version={postgres_versions[major]}"
    write_to_file("\n".join(lines) + "\n", f"{exec_path}/{PKGVARS_FILE}")


def get_new_changelog_entry(release_version: str, changes: List[str]) -> str:
    header = f"### citus-docker v{release_version}.docker ({datetime.strftime(datetime.now(), '%B %d,%Y')}) ###\n"
    bullets = "".join(f"\n* {change}\n" for change in changes)
    return f"{header}{bullets}\n"


def read_shipped_deb_version(exec_path: str) -> Optional[str]:
    """Returns the Debian package version the repository's latest image installs today."""
    content = read_file(f"{exec_path}/{LATEST_OUTPUT}") or ""
    version = DOCKERFILE_VERSION_PATTERN.search(content)
    revision = DOCKERFILE_DEB_REVISION_PATTERN.search(content)
    if version and revision:
        return f"{version.group(1)}.citus-{revision.group(1)}"
    return None


def changelog_starts_with_version(changelog: str, release_version: str) -> bool:
    return changelog.startswith(f"### citus-docker v{release_version}.docker ")


def describe_changes(
    release: CitusRelease,
    old_changelog: str,
    shipped_deb_version: Optional[str],
    base_changes: Dict[int, str],
    dockerfiles_changed: bool,
) -> List[str]:
    """Changelog bullets for a new Citus version, a new Debian revision of the version Docker ships,
    a rebuild on new PostgreSQL base images, or regenerated Dockerfiles."""
    changes = []
    if not changelog_starts_with_version(old_changelog, release.version):
        changes.append(f"Bump Citus version to {release.version}")
    elif shipped_deb_version and shipped_deb_version != release.deb_version:
        changes.append(f"Bump the Citus Debian package to {release.deb_version}")
    if base_changes:
        bases = ", ".join(
            base_changes[major] for major in sorted(base_changes, reverse=True)
        )
        changes.append(f"Bump PostgreSQL base images to {bases}")
    if not changes and dockerfiles_changed:
        changes.append("Regenerate the Dockerfiles from the citusdata/tools templates")
    return changes


def update_changelog(release: CitusRelease, exec_path: str, changes: List[str]):
    changelog_file_path = f"{exec_path}/{CHANGELOG_FILE}"
    if changes:
        write_to_file(
            get_new_changelog_entry(release.version, changes)
            + (read_file(changelog_file_path) or ""),
            changelog_file_path,
        )


def render_docker_files(
    release: CitusRelease, targets: Dict[int, str], latest_major: int
) -> Dict[str, str]:
    latest_postgres_version = targets[latest_major]
    docker_files = {
        LATEST_OUTPUT: render_docker_template(
            LATEST_TEMPLATE, release, latest_postgres_version
        ),
        DOCKER_COMPOSE_OUTPUT: render_docker_template(DOCKER_COMPOSE_TEMPLATE, release),
        ALPINE_OUTPUT: render_docker_template(
            ALPINE_TEMPLATE, release, latest_postgres_version
        ),
    }
    for major in sorted(targets):
        docker_files[postgres_output(major)] = render_docker_template(
            postgres_template(major), release, targets[major]
        )
    return docker_files


def plan_docker_update(
    release: CitusRelease,
    exec_path: str,
    postgres_versions: Dict[int, str],
    latest_postgres_major: Optional[int] = None,
) -> DockerUpdatePlan:
    """Validates inputs and computes the file updates in memory without writing to disk."""
    pkgvars_versions = read_pkgvars_postgres_versions(exec_path)
    targets = select_target_versions(postgres_versions, pkgvars_versions)
    latest_major = select_latest_postgres_major(
        targets, read_latest_postgres_major(exec_path), latest_postgres_major
    )
    shipped_deb_version = read_shipped_deb_version(exec_path)
    old_changelog = read_file(f"{exec_path}/{CHANGELOG_FILE}") or ""

    docker_files = render_docker_files(release, targets, latest_major)
    dockerfiles_changed = any(
        read_file(f"{exec_path}/{path}") != content
        for path, content in docker_files.items()
    )
    base_changes = {
        major: version
        for major, version in targets.items()
        if pkgvars_versions[major] != version
    }
    changes = describe_changes(
        release, old_changelog, shipped_deb_version, base_changes, dockerfiles_changed
    )
    update = DockerUpdate(
        written_files=list(docker_files) + [PKGVARS_FILE, CHANGELOG_FILE],
        untouched_majors=sorted(set(pkgvars_versions) - set(targets)),
        latest_major=latest_major,
        changes=changes,
        citus_version_changed=not changelog_starts_with_version(
            old_changelog, release.version
        ),
    )
    return DockerUpdatePlan(
        targets=targets,
        docker_files=docker_files,
        base_changes=base_changes,
        update=update,
        has_changes=bool(dockerfiles_changed or base_changes or changes),
    )


def write_docker_update(
    release: CitusRelease, exec_path: str, plan: DockerUpdatePlan
) -> DockerUpdate:
    for relative_path, content in plan.docker_files.items():
        if read_file(f"{exec_path}/{relative_path}") != content:
            write_docker_file(exec_path, relative_path, content)
    if plan.base_changes:
        update_pkgvars(exec_path, plan.targets)
    update_changelog(release, exec_path, plan.update.changes)
    return plan.update


def update_all_docker_files(
    release: CitusRelease,
    exec_path: str,
    postgres_versions: Dict[int, str],
    latest_postgres_major: Optional[int] = None,
) -> DockerUpdate:
    """Regenerates the Docker files of one Citus release on the given Docker base PostgreSQL versions.
    Every input is validated before the first file is written."""
    plan = plan_docker_update(
        release, exec_path, postgres_versions, latest_postgres_major
    )
    return write_docker_update(release, exec_path, plan)


def apt_packages_index_url(repository: str, distribution: str) -> str:
    parts = distribution.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(
            f"Invalid APT distribution '{distribution}'. Expected <os>/<codename>, e.g. debian/trixie."
        )
    return (
        f"{repository.rstrip('/')}/{parts[0]}/dists/{parts[1]}/main/"
        f"binary-{DEB_ARCHITECTURE}/Packages"
    )


def parse_apt_packages_index(index_text: str) -> Dict[str, Set[str]]:
    published: Dict[str, Set[str]] = {}
    package = None
    version = None
    for line in index_text.splitlines() + [""]:
        if line.startswith("Package: "):
            package = line[len("Package: ") :].strip()
        elif line.startswith("Version: "):
            version = line[len("Version: ") :].strip()
        elif not line.strip():
            if package and version:
                published.setdefault(package, set()).add(version)
            package = None
            version = None
    return published


def missing_citus_debs(
    release: CitusRelease, postgres_majors, published: Dict[str, Set[str]]
) -> List[str]:
    missing = []
    for major in sorted(postgres_majors):
        package = f"postgresql-{major}-citus-{release.minor_version}"
        if release.deb_version not in published.get(package, set()):
            missing.append(f"{package}={release.deb_version}")
    return missing


def fetch_apt_packages_index(index_url: str) -> str:
    response = requests.get(index_url, timeout=60)
    response.raise_for_status()
    return response.text


def verify_citus_debs_published(
    release: CitusRelease,
    postgres_majors,
    index_url: str,
    attempts: int = DEFAULT_APT_CHECK_ATTEMPTS,
    retry_interval_seconds: int = DEFAULT_APT_RETRY_INTERVAL_SECONDS,
):
    """Fails closed unless the exact Citus package of every Debian-based image is in the APT
    repository the images install from. RPM packages are not a Docker dependency."""
    problem = ""
    for attempt in range(1, attempts + 1):
        try:
            index_text = fetch_apt_packages_index(index_url)
        except requests.RequestException as error:
            problem = f"could not read {index_url}: {error}"
        else:
            missing = missing_citus_debs(
                release, postgres_majors, parse_apt_packages_index(index_text)
            )
            if not missing:
                print(
                    f"Verified {release.deb_version} for PostgreSQL {sorted(postgres_majors)} in {index_url}"
                )
                return
            problem = f"not published in {index_url}: {', '.join(missing)}"
        if attempt < attempts:
            print(
                f"Attempt {attempt}/{attempts}: {problem}. Retrying in {retry_interval_seconds} seconds.",
                file=sys.stderr,
            )
            time.sleep(retry_interval_seconds)
    raise PackageNotPublishedError(
        f"No Docker change was made after {attempts} attempts, {problem}"
    )


def source_tag_exists(source_tag: str) -> bool:
    result = run_with_output(
        f"git ls-remote --exit-code --tags {CITUS_REPOSITORY_URL} refs/tags/{source_tag}"
    )
    if result.returncode == 0:
        return True
    if result.returncode == 2:
        return False
    stderr = result.stderr.decode("utf-8", "replace").strip()
    raise RuntimeError(
        f"Could not verify tag {source_tag} in {CITUS_REPOSITORY_URL}: {stderr}"
    )


def verify_release_is_installable(args, release: CitusRelease, targets: Dict[int, str]):
    """Verifies the Citus source tag (for Alpine) and published Debian packages (for every
    regenerated major) before any branch or file is created."""
    if not source_tag_exists(release.source_tag):
        raise SourceTagNotFoundError(
            f"No Docker change was made: {release.source_tag} is not a tag of {CITUS_REPOSITORY_URL}, "
            "and the Alpine image builds Citus from it."
        )
    verify_citus_debs_published(
        release,
        targets,
        apt_packages_index_url(args.apt_repository, args.apt_distribution),
        args.apt_check_attempts,
        args.apt_retry_interval_seconds,
    )


def docker_update_branch_name(
    release: CitusRelease, targets: Dict[int, str], latest_major: int
) -> str:
    """Deterministic branch name for one release, base-version set, and latest major."""
    bases = "-".join(targets[major] for major in sorted(targets))
    return f"release-{release.deb_version}-pg-{bases}-latest-{latest_major}"


def pr_branch_exists(pr_branch: str) -> bool:
    result = run_with_output(
        f"git ls-remote --exit-code --heads origin refs/heads/{pr_branch}"
    )
    if result.returncode == 0:
        return True
    if result.returncode == 2:
        return False
    stderr = result.stderr.decode("utf-8", "replace").strip()
    raise RuntimeError(f"Could not check branch {pr_branch} on origin: {stderr}")


def pull_request_body(
    release: CitusRelease, targets: Dict[int, str], update: DockerUpdate
) -> str:
    lines = [
        "Generated by citusdata/tools `packaging_automation.update_docker`.",
        "",
        f"* Citus source tag (Alpine): `{release.source_tag}`",
        f"* Debian package version, verified in the community APT repository: `{release.deb_version}`",
        "* PostgreSQL base images: "
        + ", ".join(f"`{targets[major]}`" for major in sorted(targets)),
        f"* `latest` and `alpine` base: PostgreSQL {update.latest_major}",
    ]
    if update.untouched_majors:
        lines.append(
            "* Left untouched, not part of this release line: PostgreSQL "
            + ", ".join(str(major) for major in update.untouched_majors)
        )
    return "\n".join(lines) + "\n"


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(
        description="Updates citusdata/docker for one published Citus release."
    )
    parser.add_argument(
        "--source_tag", help="Citus source tag, e.g. v14.3.0 (required)"
    )
    parser.add_argument(
        "--deb_version",
        help="Exact published Debian package version, e.g. 14.3.0.citus-1 (required)",
    )
    parser.add_argument(
        "--postgres_versions",
        help='Docker base PostgreSQL versions, as "16.14,17.10,18.4", '
        'JSON array ["16.14", ...], or JSON mapping {"16": "16.14", ...} (required)',
    )
    parser.add_argument(
        "--latest_postgres_major",
        type=int,
        help="PostgreSQL major for the latest and alpine images. Defaults to the major they use today.",
    )
    parser.add_argument(
        "--explicitly_requested",
        action="store_true",
        help="Docker images for patch releases (vX.Y.Z with Z > 0) are only built on explicit request.",
    )
    parser.add_argument("--apt_repository", default=DEFAULT_APT_REPOSITORY)
    parser.add_argument("--apt_distribution", default=DEFAULT_APT_DISTRIBUTION)
    parser.add_argument(
        "--apt_check_attempts", type=int, default=DEFAULT_APT_CHECK_ATTEMPTS
    )
    parser.add_argument(
        "--apt_retry_interval_seconds",
        type=int,
        default=DEFAULT_APT_RETRY_INTERVAL_SECONDS,
    )
    parser.add_argument("--prj_ver", help=argparse.SUPPRESS)
    parser.add_argument("--gh_token")
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument("--exec_path")
    parser.add_argument("--is_test", action="store_true")
    args = parser.parse_args(argv)

    if args.prj_ver:
        parser.error(
            "--prj_ver was replaced by --source_tag and --deb_version, the exact published release identity."
        )
    for required in ("source_tag", "deb_version", "postgres_versions"):
        if not getattr(args, required):
            parser.error(f"--{required} is required")
    if not args.is_test and not args.gh_token:
        parser.error("--gh_token is required unless --is_test is set")
    if args.pipeline and not args.exec_path:
        parser.error("--exec_path is required with --pipeline")
    if args.apt_check_attempts < 1:
        parser.error("--apt_check_attempts must be at least 1")
    if args.apt_retry_interval_seconds < 0:
        parser.error("--apt_retry_interval_seconds must be non-negative")
    return args


def find_pull_request(gh_token: str, pr_branch: str) -> Optional[str]:
    repository = Github(gh_token).get_repo(f"{REPO_OWNER}/{PROJECT_NAME}")
    for pull_request in repository.get_pulls(
        state="open", head=f"{REPO_OWNER}:{pr_branch}"
    ):
        return pull_request.html_url
    return None


def ensure_not_proposed_yet(args, pr_branch: str) -> bool:
    """Returns False when an open PR already proposes this update. Fails loudly if the branch
    exists on origin without an open PR so orphaned branches are never silently ignored.
    """
    if not pr_branch_exists(pr_branch):
        return True
    if args.is_test:
        print(
            f"{pr_branch} already exists on origin; test mode does not look up its pull request."
        )
        return False
    pull_request = find_pull_request(args.gh_token, pr_branch)
    if pull_request is None:
        raise RuntimeError(
            f"{pr_branch} exists on origin with no open pull request. "
            "Open a pull request from that branch or delete it, then run again."
        )
    print(f"This update is already proposed in {pull_request}.")
    return False


def commit_title(release: CitusRelease, update: DockerUpdate) -> str:
    if update.citus_version_changed:
        return f"Bump docker to version {release.version}"
    if update.changes:
        details = "; ".join(change[0].lower() + change[1:] for change in update.changes)
        return f"Update docker {release.version}: {details}"
    return f"Regenerate docker {release.version} files"


def propose_docker_update(
    args, release: CitusRelease, execution_path: str, postgres_versions: Dict[int, str]
):
    previous_cwd = os.getcwd()
    execution_path = os.path.abspath(execution_path)
    os.chdir(execution_path)
    try:
        plan = plan_docker_update(
            release, execution_path, postgres_versions, args.latest_postgres_major
        )
        verify_release_is_installable(args, release, plan.targets)
        if not plan.has_changes:
            print(
                f"citusdata/docker already matches {release.deb_version}; nothing to propose."
            )
            return
        pr_branch = docker_update_branch_name(
            release, plan.targets, plan.update.latest_major
        )
        if not ensure_not_proposed_yet(args, pr_branch):
            return

        subprocess.run(["git", "checkout", "-B", pr_branch], check=True)
        update = write_docker_update(release, execution_path, plan)
        if update.untouched_majors:
            print(
                "Left untouched, not part of this release line: PostgreSQL "
                + ", ".join(str(m) for m in update.untouched_majors),
                file=sys.stderr,
            )
        # Stage only generated paths: consumers clone tools into the docker checkout.
        subprocess.run(["git", "add", "--", *update.written_files], check=True)
        if run_with_output("git diff --cached --quiet").returncode == 0:
            print(
                f"citusdata/docker already matches {release.deb_version}; nothing to propose."
            )
            return

        title = commit_title(release, update)
        subprocess.run(["git", "commit", "-m", title], check=True)
        if not args.is_test:
            subprocess.run(
                ["git", "push", "--set-upstream", "origin", pr_branch], check=True
            )
            repository = Github(args.gh_token).get_repo(f"{REPO_OWNER}/{PROJECT_NAME}")
            create_pr_with_repo(
                repository,
                pr_branch,
                title,
                MAIN_BRANCH,
                pull_request_body(release, plan.targets, update),
            )
    finally:
        os.chdir(previous_cwd)


def main(argv=None):
    args = parse_arguments(argv)
    release = parse_citus_release(args.source_tag, args.deb_version)
    if release.is_patch_release and not args.explicitly_requested:
        raise ValueError(
            f"{release.source_tag} is a patch release. Patch releases ship packages only; pass "
            "--explicitly_requested when Docker images were explicitly requested."
        )
    postgres_versions = parse_postgres_versions(args.postgres_versions)

    if args.pipeline:
        propose_docker_update(args, release, args.exec_path, postgres_versions)
        return
    working_directory = os.getcwd()
    execution_path = f"{working_directory}/{CHECKOUT_DIR}"
    # Always start from a fresh clone so a leftover checkout of an earlier run is never reused.
    initialize_env(working_directory, PROJECT_NAME, CHECKOUT_DIR)
    try:
        propose_docker_update(args, release, execution_path, postgres_versions)
    finally:
        os.chdir(working_directory)
        if not args.is_test:
            remove_cloned_code(execution_path)


if __name__ == "__main__":
    main()
