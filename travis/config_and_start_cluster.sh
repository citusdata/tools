#!/bin/bash

# Inspired by https://gist.github.com/petere/6023944

set -eux

# Create fully-trusting cluster on custom port, owned by us
sudo pg_createcluster $PGVERSION test -p 55435 -u `whoami` -- -A trust

# Build and install extension
make all PG_CONFIG=/usr/lib/postgresql/$PGVERSION/bin/pg_config
sudo make install PG_CONFIG=/usr/lib/postgresql/$PGVERSION/bin/pg_config

# Preload library if asked to do so
if [ ${PG_PRELOAD+1} ]
then
  echo "shared_preload_libraries = '$PG_PRELOAD'" >> \
    /etc/postgresql/$PGVERSION/test/postgresql.conf
fi

# Start cluster
sudo pg_ctlcluster $PGVERSION test start
