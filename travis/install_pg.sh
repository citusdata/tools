#!/bin/bash

# Inspired by https://gist.github.com/petere/6023944

set -eux

# always install postgresql-common
packages="postgresql-common libedit-dev libpam0g-dev"

# we set PGVERSION to 10x of the Citus version when testing Citus, so
# only install PostgreSQL proper if it's 9.5 or lower
if [ "${PGVERSION//./}" -le "95" ]; then
  packages="$packages postgresql-$PGVERSION postgresql-server-dev-$PGVERSION"
fi

sudo apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install $packages
