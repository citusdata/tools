# Travis CI

These scripts are intended for use within the Travis CI continuous integration system. Because most of the projects tested by Citus Data take the form of PostgreSQL extensions, the scripts are specialized for that use case.

## Getting Started

Travis CI itself has [_fantastic_ documentation](https://docs.travis-ci.com) covering the options available within that service. To figure out how to do something within Travis itself, go there first. Most Travis builds are configured entirely by their `.travis.yml` files, so the config for `pg_shard` and `cstore_fdw` might provide some inspiration or clarity.

## What's Included

With the provided scripts, it's fairly easy to set up a matrix build (on all PostgreSQL and CitusDB versions) to run tests against an installed extension in a "system" cluster (`make installcheck`) or against a one-off cluster started for the test itself (often `make check`).

These scripts were inspired by [a similar workflow](https://gist.github.com/petere) used by Peter Eisentraut to test his own PostgreSQL extensions (e.g. [`pguri`](https://github.com/petere/pguri/blob/1.20151224/.travis.yml)). Jason Petersen adapted that workflow into a set of scripts, which lived in [a Gist](https://gist.github.com/jasonmp85/9963879) before the creation of this repository.

### `setup_apt`

This script simply adds all necessary official PostgreSQL APT repositories (including those with prerelease software) and updates package lists to prepare for installation.

### `nuke_pg`

It is possible that your Travis CI virtual machine starts with a PostgreSQL instance already running, though you probably don't want to use it as-is. So we "nuke" it by stopping it and ensuring it never comes back.

### `install_pg`

A PostgreSQL version will be installed based on the value of the `PGVERSION` environment variable. In addition, common extension dependencies and development headers are installed. Suitable values for `PGVERSION` might be `9.3`, `9.4`, or `9.5`.

### `install_uncrustify`

Installs a recent `uncrustify` version from a Citus-specific Trusty package stored in S3.
### `install_citus`

Similar to `install_pg`, but installs CitusDB instead of vanilla PostgreSQL. The convention is that `PGVERSION` should be set to ten times the CitusDB version (to avoid possible collisions with existing PostgreSQL versions). For instance, a value of `40.0` installs CitusDB 4.0, and `41.0` installs CitusDB 4.1.

### `config_and_start_cluster`

Since the "nuke" script removed the only running PostgreSQL cluster, you'll probably want to have one up and running to build, install, and test an extension. This script starts just such a cluster. If the `PG_PRELOAD` environment variable is set, the cluster uses its value for the `shared_preload_libraries` setting.

Note that starting your own cluster is necessary only if you want to build, install, and test your extension in a system-wide cluster. This is the case for most extensions using the PostgreSQL extension build system (i.e. `make install` followed by `make installcheck`), but some advanced use cases may not need a cluster created.

### `pg_travis_test`

Runs regression tests against a system-wide cluster, echoing any failures to standard out (and exiting abnormally on failure). This is the actual "test" part of the whole workflow (for most extensions).

### `pg_travis_multi_test`

Runs regression tests against a more "complex" extension, usually one that:

  * Requires that `./configure` be run before `make` can proceed
  * Starts its own PostgreSQL instances within a `check` Make target.

If this script is used, it is likely that `config_and_start_cluster` is unnecessary.

### `build_new_nightly`

Checks packagecloud.io for the last nightly for the project being built. If any commits have been made to that project's GitHub development branch since the last nightly upload, this script builds a new nightly release (using `citus_package`).

If no nightly is needed, exits immediately.

### `build_new_release`

Downloads the packaging files for the project being built. If the packaging files specify a version that is not yet in packagecloud.io, this script builds a new official release (using `citus_package`).

If no new release is needed, exits immediately.

### `release_pgxn`

Downloads the PGXN `META.json` file for the project build built, produces a new PGXN-compatible archive, and uploads that archive to pgxn.org.

Does not presently check ahead of time if PGXN already contains the archive; instead the script will exit successfully with a message indicating that the server already contained the version it uploaded.

### `sync_to_enterprise`

Pushes branches from the open-source Citus GitHub repository to the closed-source Citus Enterprise repository. Intended for use with the `master` branch and any branches beginning with `release-`.

### `trigger_docker_nightly`

Pairs with `build_new_nightly` to trigger a new Docker Hub nightly image build. Only runs if the following conditions are met:

  * Project is `citus`
  * OS is `debian`
  * Release is `jessie`
  * New nightly was produced

### `fetch_build_files` and `parse_latest_release`

Needed by packaging-related scripts. Copy-pasted from the `citusdata/packaging` repository. See that project for details.
