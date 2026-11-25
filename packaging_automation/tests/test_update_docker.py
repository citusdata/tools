import os
import subprocess

import pytest
import requests

from .. import update_docker
from ..update_docker import (
    PackageNotPublishedError,
    SourceTagNotFoundError,
    main,
    parse_citus_release,
    parse_postgres_versions,
    update_all_docker_files,
)

DOCKER_MASTER_PKGVARS = (
    "postgres_19_version=19beta3\n"
    "postgres_18_version=18.4\n"
    "postgres_17_version=17.10\n"
    "postgres_16_version=16.14\n"
)
PG19_PREVIEW = "FROM postgres:19beta3\nARG VERSION=14.1.0\n"
RELEASE_14_POSTGRES_DOCKER = {16: "16.14", 17: "17.10", 18: "18.4"}
RELEASE_14_3_0 = parse_citus_release("v14.3.0", "14.3.0.citus-1")
TRIXIE_AMD64_INDEX = "https://packagecloud.io/citusdata/community/debian/dists/trixie/main/binary-amd64/Packages"


def apt_index(deb_version, majors=(16, 17, 18)):
    minor = ".".join(deb_version.split(".")[:2])
    return "".join(
        f"Package: postgresql-{major}-citus-{minor}\nVersion: {deb_version}\nArchitecture: amd64\n\n"
        for major in majors
    )


@pytest.fixture(name="apt_repository")
def fixture_apt_repository(monkeypatch):
    """Serves the community APT index and Citus tags; each fetch returns the next response,
    repeating the last one."""
    state = {
        "responses": [apt_index("14.3.0.citus-1")],
        "urls": [],
        "sleeps": [],
        "tags": {"v14.3.0", "v14.3.1"},
    }

    def fetch(url):
        state["urls"].append(url)
        response = state["responses"][
            min(len(state["urls"]), len(state["responses"])) - 1
        ]
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(update_docker, "fetch_apt_packages_index", fetch)
    monkeypatch.setattr(update_docker, "source_tag_exists", state["tags"].__contains__)
    monkeypatch.setattr(update_docker.time, "sleep", state["sleeps"].append)
    return state


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as writer:
        writer.write(content)


def read(path):
    with open(path, "r", encoding="utf8") as reader:
        return reader.read()


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture(name="docker_repo")
def fixture_docker_repo(tmp_path):
    """A docker repository laid out like citusdata/docker master on Citus 14.2.0: PG16-18 images,
    latest/alpine on PG18, a PG19 preview outside the release-14 line, and an origin remote.
    """
    repo = str(tmp_path / "docker")
    write(f"{repo}/pkgvars", DOCKER_MASTER_PKGVARS)
    write(f"{repo}/Dockerfile", "FROM postgres:18.4\nARG VERSION=14.2.0\n")
    write(f"{repo}/alpine/Dockerfile", "FROM postgres:18.4-alpine\n")
    for major, version in RELEASE_14_POSTGRES_DOCKER.items():
        write(f"{repo}/postgres-{major}/Dockerfile", f"FROM postgres:{version}\n")
    write(f"{repo}/postgres-19/Dockerfile", PG19_PREVIEW)
    write(
        f"{repo}/CHANGELOG.md",
        "### citus-docker v14.2.0.docker (September 01,2026) ###\n\n* Bump Citus version to 14.2.0\n",
    )
    git(repo, "init", "-q", "-b", "master")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "docker master")
    origin = str(tmp_path / "origin.git")
    subprocess.run(["git", "clone", "-q", "--bare", repo, origin], check=True)
    git(repo, "remote", "add", "origin", origin)
    return repo


@pytest.fixture(name="pipeline_checkout")
def fixture_pipeline_checkout(docker_repo):
    """Adds a nested citusdata/tools clone and an unrelated untracked file, matching
    update_version.yml's checkout layout."""
    tools = f"{docker_repo}/tools"
    write(f"{tools}/README.md", "tools clone\n")
    git(tools, "init", "-q")
    git(tools, "add", "-A")
    git(tools, "commit", "-q", "-m", "tools")
    write(f"{docker_repo}/scratch.txt", "unrelated\n")
    return docker_repo


def run_main(docker_repo, monkeypatch, *extra_args):
    monkeypatch.chdir(docker_repo)
    main(
        [
            "--pipeline",
            "--exec_path",
            docker_repo,
            "--is_test",
            "--postgres_versions",
            "16.14,17.10,18.4",
            *extra_args,
        ]
    )


def run_release(docker_repo, monkeypatch, deb_version, *extra_args):
    run_main(
        docker_repo,
        monkeypatch,
        "--source_tag",
        f"v{deb_version.split('.citus-')[0]}",
        "--deb_version",
        deb_version,
        *extra_args,
    )


def test_stable_release_refreshes_the_release_line_images(docker_repo):
    update = update_all_docker_files(
        RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER
    )

    for major, version in RELEASE_14_POSTGRES_DOCKER.items():
        content = read(f"{docker_repo}/postgres-{major}/Dockerfile")
        assert f"FROM postgres:{version}\n" in content
        assert "ARG VERSION=14.3.0\n" in content
        assert "ENV CITUS_VERSION ${VERSION}.citus-1\n" in content
        assert "postgresql-$PG_MAJOR-citus-14.3=$CITUS_VERSION" in content
    assert "FROM postgres:18.4\n" in read(f"{docker_repo}/Dockerfile")
    assert "FROM postgres:18.4-alpine\n" in read(f"{docker_repo}/alpine/Dockerfile")
    assert 'image: "citusdata/citus:14.3.0"' in read(
        f"{docker_repo}/docker-compose.yml"
    )
    assert (
        read(f"{docker_repo}/CHANGELOG.md")
        .split("### citus-docker v14.2.0")[0]
        .endswith("\n\n* Bump Citus version to 14.3.0\n\n")
    )
    assert update.latest_major == 18


def test_majors_outside_the_release_line_are_left_untouched(docker_repo):
    update = update_all_docker_files(
        RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER
    )

    assert update.untouched_majors == [19]
    assert read(f"{docker_repo}/postgres-19/Dockerfile") == PG19_PREVIEW
    assert "postgres_19_version=19beta3\n" in read(f"{docker_repo}/pkgvars")


def test_images_install_the_exact_published_debian_revision(docker_repo):
    repackaged = parse_citus_release("v14.3.0", "14.3.0.citus-2")

    update_all_docker_files(repackaged, docker_repo, RELEASE_14_POSTGRES_DOCKER)

    for path in ("Dockerfile", "postgres-16/Dockerfile", "postgres-17/Dockerfile"):
        assert "ENV CITUS_VERSION ${VERSION}.citus-2\n" in read(f"{docker_repo}/{path}")


def test_base_rebuild_keeps_the_citus_version_and_records_new_bases(docker_repo):
    update_all_docker_files(RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER)

    update_all_docker_files(
        RELEASE_14_3_0, docker_repo, {16: "16.15", 17: "17.11", 18: "18.6"}
    )

    assert "FROM postgres:18.6\n" in read(f"{docker_repo}/Dockerfile")
    assert "FROM postgres:16.15\n" in read(f"{docker_repo}/postgres-16/Dockerfile")
    pkgvars = read(f"{docker_repo}/pkgvars")
    assert "postgres_18_version=18.6\n" in pkgvars
    assert "postgres_16_version=16.15\n" in pkgvars
    changelog = read(f"{docker_repo}/CHANGELOG.md")
    assert (
        changelog.split("\n\n")[1]
        == "* Bump PostgreSQL base images to 18.6, 17.11, 16.15"
    )
    assert changelog.count("Bump Citus version to 14.3.0") == 1


def test_replaying_a_release_changes_nothing(docker_repo):
    update_all_docker_files(RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER)
    git(docker_repo, "add", "-A")
    git(docker_repo, "commit", "-q", "-m", "14.3.0")

    update_all_docker_files(RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER)

    assert git(docker_repo, "status", "--porcelain") == ""


def test_release_cannot_add_a_postgres_major(docker_repo):
    write(
        f"{docker_repo}/pkgvars",
        "postgres_18_version=18.4\npostgres_17_version=17.10\n",
    )

    with pytest.raises(ValueError, match="no postgres_<major>_version entry"):
        update_all_docker_files(RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER)

    assert git(docker_repo, "status", "--porcelain") == " M pkgvars\n"


def test_latest_moves_only_when_requested_and_never_to_a_prerelease(docker_repo):
    with pytest.raises(ValueError, match="prerelease"):
        update_all_docker_files(
            RELEASE_14_3_0, docker_repo, {18: "18.4", 19: "19beta3"}, 19
        )

    update_all_docker_files(RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER, 17)

    assert "FROM postgres:17.10\n" in read(f"{docker_repo}/Dockerfile")
    assert "FROM postgres:17.10-alpine\n" in read(f"{docker_repo}/alpine/Dockerfile")


def test_postgres_versions_accepts_list_json_array_and_apt_mapping():
    assert parse_postgres_versions('{"18": "18.4", "19": "19~rc1"}') == {
        18: "18.4",
        19: "19rc1",
    }
    assert parse_postgres_versions('["16.14", "17.10", "18.4"]') == (
        RELEASE_14_POSTGRES_DOCKER
    )
    assert parse_postgres_versions("16.14, 17.10,18.4") == RELEASE_14_POSTGRES_DOCKER
    with pytest.raises(ValueError, match="not a PostgreSQL 17 version"):
        parse_postgres_versions('{"17": "18.4"}')


@pytest.mark.parametrize(
    "source_tag,deb_version",
    [
        ("v14.3.0", "14.2.0.citus-1"),
        ("v15.0.0-rc1", "15.0.0.rc1.citus-1"),
        ("14.3.0", "14.3.0.citus-1"),
        ("v14.3.0", "14.3.0"),
    ],
)
def test_release_identity_must_be_exact_and_stable(source_tag, deb_version):
    with pytest.raises(ValueError):
        parse_citus_release(source_tag, deb_version)


def test_patch_release_needs_an_explicit_request(
    docker_repo, monkeypatch, apt_repository
):
    apt_repository["responses"] = [apt_index("14.3.1.citus-1")]
    with pytest.raises(ValueError, match="patch release"):
        run_main(
            docker_repo,
            monkeypatch,
            "--source_tag",
            "v14.3.1",
            "--deb_version",
            "14.3.1.citus-1",
        )
    assert git(docker_repo, "status", "--porcelain") == ""

    run_main(
        docker_repo,
        monkeypatch,
        "--source_tag",
        "v14.3.1",
        "--deb_version",
        "14.3.1.citus-1",
        "--explicitly_requested",
    )
    assert "ARG VERSION=14.3.1" in read(f"{docker_repo}/Dockerfile")


def test_missing_package_prevents_any_docker_change(
    docker_repo, monkeypatch, apt_repository
):
    apt_repository["responses"] = [apt_index("14.3.0.citus-1", majors=(17, 18))]

    with pytest.raises(
        PackageNotPublishedError, match="postgresql-16-citus-14.3=14.3.0.citus-1"
    ):
        run_release(
            docker_repo, monkeypatch, "14.3.0.citus-1", "--apt_check_attempts", "1"
        )

    assert git(docker_repo, "status", "--porcelain") == ""
    assert git(docker_repo, "branch", "--format=%(refname:short)") == "master\n"


@pytest.mark.usefixtures("apt_repository")
def test_package_with_another_revision_is_not_accepted(docker_repo, monkeypatch):
    with pytest.raises(PackageNotPublishedError, match="14.3.0.citus-2"):
        run_release(
            docker_repo, monkeypatch, "14.3.0.citus-2", "--apt_check_attempts", "1"
        )

    assert git(docker_repo, "status", "--porcelain") == ""


def test_repository_index_lag_is_retried_within_a_bound(
    docker_repo, monkeypatch, apt_repository
):
    apt_repository["responses"] = [
        apt_index("14.2.0.citus-1"),
        requests.ConnectionError("index unavailable"),
        apt_index("14.3.0.citus-1"),
    ]

    run_release(
        docker_repo, monkeypatch, "14.3.0.citus-1", "--apt_retry_interval_seconds", "7"
    )

    assert len(apt_repository["urls"]) == 3
    assert apt_repository["sleeps"] == [7, 7]
    assert "ARG VERSION=14.3.0" in read(f"{docker_repo}/Dockerfile")


def test_package_that_never_appears_fails_after_the_last_attempt(
    docker_repo, monkeypatch, apt_repository
):
    apt_repository["responses"] = [apt_index("14.2.0.citus-1")]

    with pytest.raises(PackageNotPublishedError, match="after 3 attempts"):
        run_release(
            docker_repo, monkeypatch, "14.3.0.citus-1", "--apt_check_attempts", "3"
        )

    assert len(apt_repository["urls"]) == 3
    assert git(docker_repo, "status", "--porcelain") == ""


def test_alpine_builds_from_the_source_tag_not_the_debian_package(docker_repo):
    update_all_docker_files(RELEASE_14_3_0, docker_repo, RELEASE_14_POSTGRES_DOCKER)
    alpine = read(f"{docker_repo}/alpine/Dockerfile")

    update_all_docker_files(
        parse_citus_release("v14.3.0", "14.3.0.citus-2"),
        docker_repo,
        RELEASE_14_POSTGRES_DOCKER,
    )

    assert read(f"{docker_repo}/alpine/Dockerfile") == alpine
    assert "ARG VERSION=14.3.0\n" in alpine
    assert "https://github.com/citusdata/citus/archive/v${VERSION}.tar.gz" in alpine
    assert ".citus-" not in alpine
    assert "ENV CITUS_VERSION ${VERSION}.citus-2\n" in read(f"{docker_repo}/Dockerfile")


def test_release_without_a_source_tag_prevents_any_docker_change(
    docker_repo, monkeypatch, apt_repository
):
    apt_repository["tags"].discard("v14.3.0")

    with pytest.raises(SourceTagNotFoundError, match="v14.3.0"):
        run_release(docker_repo, monkeypatch, "14.3.0.citus-1")

    assert git(docker_repo, "status", "--porcelain") == ""


def test_docker_update_depends_only_on_the_debian_index(
    docker_repo, monkeypatch, apt_repository
):
    run_release(docker_repo, monkeypatch, "14.3.0.citus-1")

    assert apt_repository["urls"] == [TRIXIE_AMD64_INDEX]
    for path in ("Dockerfile", "alpine/Dockerfile", "postgres-16/Dockerfile"):
        content = read(f"{docker_repo}/{path}").lower()
        assert "rpm" not in content and "yum" not in content


@pytest.mark.usefixtures("apt_repository")
def test_release_commit_contains_exactly_the_generated_files(
    pipeline_checkout, monkeypatch
):
    # PG16 is declared in pkgvars but its Dockerfile does not exist yet, so the release creates a new file.
    git(pipeline_checkout, "rm", "-q", "postgres-16/Dockerfile")
    git(pipeline_checkout, "commit", "-q", "-m", "PG16 image not generated yet")

    run_release(pipeline_checkout, monkeypatch, "14.3.0.citus-1")

    committed = dict(
        reversed(line.split("\t"))
        for line in git(
            pipeline_checkout, "show", "--name-status", "--format=", "HEAD"
        ).splitlines()
    )
    assert committed["postgres-16/Dockerfile"] == "A"
    assert set(committed) <= {
        "Dockerfile",
        "alpine/Dockerfile",
        "docker-compose.yml",
        "postgres-16/Dockerfile",
        "postgres-17/Dockerfile",
        "postgres-18/Dockerfile",
        "pkgvars",
        "CHANGELOG.md",
    }
    assert (
        git(pipeline_checkout, "status", "--porcelain") == "?? scratch.txt\n?? tools/\n"
    )


@pytest.mark.usefixtures("apt_repository")
def test_replaying_a_release_commits_nothing_new(pipeline_checkout, monkeypatch):
    run_release(pipeline_checkout, monkeypatch, "14.3.0.citus-1")
    first_commit = git(pipeline_checkout, "rev-parse", "HEAD")

    run_release(pipeline_checkout, monkeypatch, "14.3.0.citus-1")

    assert git(pipeline_checkout, "rev-parse", "HEAD") == first_commit


def propose_already_pushed_release(pipeline_checkout, monkeypatch, pull_request):
    """An earlier run pushed the update branch; this run starts from a fresh docker master checkout."""
    run_release(pipeline_checkout, monkeypatch, "14.3.0.citus-1")
    proposed_branch = git(pipeline_checkout, "branch", "--show-current").strip()
    git(pipeline_checkout, "push", "-q", "origin", proposed_branch)
    git(pipeline_checkout, "checkout", "-q", "master")
    git(pipeline_checkout, "branch", "-q", "-D", proposed_branch)
    monkeypatch.setattr(
        update_docker, "find_pull_request", lambda token, branch: pull_request
    )
    monkeypatch.chdir(pipeline_checkout)
    main(
        [
            "--gh_token",
            "unused",
            "--pipeline",
            "--exec_path",
            pipeline_checkout,
            "--source_tag",
            "v14.3.0",
            "--deb_version",
            "14.3.0.citus-1",
            "--postgres_versions",
            "16.14,17.10,18.4",
        ]
    )


@pytest.mark.usefixtures("apt_repository")
def test_update_with_an_open_pull_request_is_not_proposed_again(
    pipeline_checkout, monkeypatch
):
    propose_already_pushed_release(
        pipeline_checkout, monkeypatch, "https://github.com/citusdata/docker/pull/1"
    )

    assert git(pipeline_checkout, "branch", "--format=%(refname:short)") == "master\n"
    assert (
        git(pipeline_checkout, "status", "--porcelain") == "?? scratch.txt\n?? tools/\n"
    )


@pytest.mark.usefixtures("apt_repository")
def test_pushed_update_without_an_open_pull_request_is_reported(
    pipeline_checkout, monkeypatch
):
    with pytest.raises(RuntimeError, match="no open pull request"):
        propose_already_pushed_release(pipeline_checkout, monkeypatch, None)

    assert git(pipeline_checkout, "branch", "--format=%(refname:short)") == "master\n"
    assert (
        git(pipeline_checkout, "status", "--porcelain") == "?? scratch.txt\n?? tools/\n"
    )


def test_new_debian_revision_of_the_shipped_version_is_recorded(
    pipeline_checkout, monkeypatch, apt_repository
):
    apt_repository["responses"] = [
        apt_index("14.3.0.citus-1") + apt_index("14.3.0.citus-2")
    ]
    run_release(pipeline_checkout, monkeypatch, "14.3.0.citus-1")

    run_release(pipeline_checkout, monkeypatch, "14.3.0.citus-2")

    assert (
        git(pipeline_checkout, "log", "-1", "--format=%s")
        == "Update docker 14.3.0: bump the Citus Debian package to 14.3.0.citus-2\n"
    )
    changelog = read(f"{pipeline_checkout}/CHANGELOG.md")
    assert (
        changelog.split("\n\n")[1]
        == "* Bump the Citus Debian package to 14.3.0.citus-2"
    )


def test_old_version_only_invocation_is_refused(docker_repo, monkeypatch):
    with pytest.raises(SystemExit):
        run_main(docker_repo, monkeypatch, "--prj_ver", "14.3.0")


@pytest.mark.usefixtures("apt_repository")
def test_unreachable_origin_fails_instead_of_silently_continuing(
    docker_repo, monkeypatch
):
    git(docker_repo, "remote", "set-url", "origin", "/nonexistent/origin.git")

    with pytest.raises(RuntimeError, match="Could not check branch"):
        run_release(docker_repo, monkeypatch, "14.3.0.citus-1")

    assert git(docker_repo, "branch", "--format=%(refname:short)") == "master\n"
    assert git(docker_repo, "status", "--porcelain") == ""


@pytest.mark.usefixtures("apt_repository")
def test_pipeline_accepts_a_relative_exec_path(docker_repo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(
        [
            "--pipeline",
            "--exec_path",
            "docker",
            "--is_test",
            "--source_tag",
            "v14.3.0",
            "--deb_version",
            "14.3.0.citus-1",
            "--postgres_versions",
            "16.14,17.10,18.4",
        ]
    )

    assert os.getcwd() == str(tmp_path)
    assert "ARG VERSION=14.3.0\n" in read(f"{docker_repo}/Dockerfile")
