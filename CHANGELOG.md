### citustools v0.6.0 (May 5, 2017) ###

* Adds scripts to query, normalize, and load download KPI data

* Supports compiling and running tests against a custom-compiled PostgreSQL

### citustools v0.5.3 (May 2, 2017) ###

* Fixes `trigger_docker_nightly` to expect intermediate pkgs directory

### citustools v0.5.2 (May 2, 2017) ###

* Adds support for version numbers baked in to package names ("fancy")

* Fixes bug preventing Travis from producing both a release and nightly at once

* Addresses all shellcheck warnings and errors

### citustools v0.5.1 (December 6, 2016) ###

* Adds `--enable-coverage` configure flag in `pg_travis_multi_test`

### citustools v0.5.0 (November 7, 2016) ###

* Adds support for per-project, per-build-type multi-PostgreSQL builds

* Extends citus_package to understand new pkgvars metadata file

* Adds support for arbitrary projects (must be in GitHub)

* Adds support for building packages from local build files

### citustools v0.4.3 (September 30, 2016) ###

* Makes Travis install scripts PostgreSQL 9.6-aware

### citustools v0.4.2 (September 27, 2016) ###

* Adds support for building the HyperLogLog package

### citustools v0.4.1 (August 19, 2016) ###

* Multi test now requires args rather than using hardcoded targets

### citustools v0.4.0 (August 2, 2016) ###

* Adds Travis script to alleviate uncrustify installation

* Adds logic to fully install Travis scripts

* Removes .sh prefix from all Travis executables

### citustools v0.3.3 (August 1, 2016) ###

* Removes packaging support for PostgreSQL 9.4

* Fixes minor documentation typo

### citustools v0.3.2 (July 6, 2016) ###

* Fixes bug that caused Travis to unnecessarily build rebalancer

### citustools v0.3.1 (July 6, 2016) ###

* Adds support for building Fedora 24 packages

### citustools v0.3.0 (June 16, 2016) ###

* Adds support for building PGXN releases

* Adds support for signing generated deb and rpm files

* Adds Travis CI scripts to build nightlies and releases

* Adds Travis CI script to push new OSS commits to Enterprise

* Adds Travis CI script to trigger Docker Hub nightly image build

* Copies several scripts from the Citus packaging repo

### citustools v0.2.0 (May 13, 2016) ###

* Adds wrapper to simplify generating OS packages for Citus projects

* Some perlcritic and perltidy cleanup here and there

### citustools v0.1.0 (February 16, 2016) ###

* Initial release

* Adds scripts for Travis CI build workflows

* Adds wrapper script to help apply Citus C style
