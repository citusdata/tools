#!/bin/bash

set -eux

status=0

# Create Ubuntu's PostgreSQL socket dir and relax permissions.
sudo mkdir -p /var/run/postgresql
sudo chown -R `whoami` /var/run/postgresql

# Configure, build, and install extension
./configure PG_CONFIG=/usr/lib/postgresql/$PGVERSION/bin/pg_config
make all
sudo make install

# Change to test directory for remainder
cd src/test/regress

# Run tests. DBs owned by non-standard owner put socket in /tmp
make check-multi check-multi-fdw check-worker || status=$?

# Print diff if it exists
if test -f regression.diffs; then cat regression.diffs; fi

exit $status
