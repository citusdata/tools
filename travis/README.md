# Travis CI

These scripts are intended for use within the Travis CI continuous integration system. Because most of the projects tested by Citus Data take the form of PostgreSQL extensions, the scripts are specialized for that use case.

## Getting Started

Travis CI itself has [_fantastic_ documentation](https://docs.travis-ci.com) covering the options available within that service. To figure out how to do something within Travis itself, go there first. Most Travis builds are configured entirely by their `.travis.yml` files, so the config for `pg_shard` and `cstore_fdw` might provide some inspiration or clarity.

## What's Included

With the provided scripts, it's fairly easy to set up a matrix build (on all PostgreSQL and CitusDB versions) to run tests against an installed extension in a "system" cluster (`make installcheck`) or against a one-off cluster started for the test itself (often `make check`).

These scripts were inspired by [a similar workflow](https://gist.github.com/petere) used by Peter Eisentraut to test his own PostgreSQL extensions (e.g. [`pguri`](https://github.com/petere/pguri/blob/1.20151224/.travis.yml)). Jason Petersen adapted that workflow into a set of scripts, which lived in [a Gist](https://gist.github.com/jasonmp85/9963879) before the creation of this repository.

### `setup_apt.sh`

This script simply adds all necessary official PostgreSQL APT repositories (including those with prerelease software) and updates package lists to prepare for installation.

### `nuke_pg.sh`

It is possible that your Travis CI virtual machine starts with a PostgreSQL instance already running, though you probably don't want to use it as-is. So we "nuke" it by stopping it and ensuring it never comes back.

### `install_pg.sh`

A PostgreSQL version will be installed based on the value of the `PGVERSION` environment variable. In addition, common extension dependencies and development headers are installed. Suitable values for `PGVERSION` might be `9.3`, `9.4`, or `9.5`.

### `install_citus.sh`

Similar to `install_pg.sh`, but installs CitusDB instead of vanilla PostgreSQL. The convention is that `PGVERSION` should be set to ten times the CitusDB version (to avoid possible collisions with existing PostgreSQL versions). For instance, a value of `40.0` installs CitusDB 4.0, and `41.0` installs CitusDB 4.1.

### `config_and_start_cluster.sh`

Since the "nuke" script removed the only running PostgreSQL cluster, you'll probably want to have one up and running to build, install, and test an extension. This script starts just such a cluster. If the `PG_PRELOAD` environment variable is set, the cluster uses its value for the `shared_preload_libraries` setting.

Note that starting your own cluster is necessary only if you want to build, install, and test your extension in a system-wide cluster. This is the case for most extensions using the PostgreSQL extension build system (i.e. `make install` followed by `make installcheck`), but some advanced use cases may not need a cluster created.

### `pg_travis_test.sh`

Runs regression tests against a system-wide cluster, echoing any failures to standard out (and exiting abnormally on failure). This is the actual "test" part of the whole workflow (for most extensions).

### `pg_travis_multi_test.sh`

Runs regression tests against a more "complex" extension, usually one that:

  * Requires that `./configure` be run before `make` can proceed
  * Starts its own PostgreSQL instances within a `check` Make target.

If this script is used, it is likely that `config_and_start_cluster.sh` is unnecessary.
