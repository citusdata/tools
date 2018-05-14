### citustools v0.7.7 (May 14, 2018) ###

* Add latest Ubuntu and Fedora releases

* Remove use of `default_formula` in Homebrew formula

### citustools v0.7.6 (February 7, 2018) ###

* Update Debian patch URL

### citustools v0.7.5 (January 16, 2018) ###

* Add grep to check docker build output

### citustools v0.7.4 (November 15, 2017) ###

* Switches nightly logic to detect Debian Stretch

* Improvements to valgrind logic

### citustools v0.7.3 (October 5, 2017) ###

* Fixes regex problem with PG 10 RPM builds

### citustools v0.7.2 (October 5, 2017) ###

* Changes packaging default PostgreSQL versions from 9.5,9.6 to 9.6,10

### citustools v0.7.1 (August 30, 2017) ###

* Add support for testing against PostgreSQL 11/master branch

* Fixes bug causing early exit during first nightly of new OS/package

* Add `--enable-depend` to avoid build problems with changed headers

### citustools v0.7.0 (August 30, 2017) ###

* Removes Ubuntu Precise from supported packaging versions

* Removes Fedora 22, 23, and 24 from supported packaging versions

* Adds Fedora 25 and 26 to supported packaging versions

### citustools v0.6.5 (August 29, 2017) ###

* Bumps PostgreSQL version for valgrind tests

* Adds Debian Stretch to supported packaging versions

### citustools v0.6.4 (August 15, 2017) ###

* Bumps Homebrew formula

* Adds automation script for valgrind tests

* Starts to use `REL_10_STABLE` branch for PostgreSQL tests

### citustools v0.6.3 (July 11, 2017) ###

* Addresses citus-style compatibility issues with uncrustify 0.65

### citustools v0.6.2 (June 19, 2017) ###

* Fixes bug causing early exit during first release of new package

* Adds support for building against PostgreSQL 10

* Adds caching logic for PostgreSQL source builds

### citustools v0.6.1 (May 12, 2017) ###

* Adds logic to apply PGDG's directory patches to custom builds

* Fixes bug preventing builds where `USE_CUSTOM_PG` is undefined

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
