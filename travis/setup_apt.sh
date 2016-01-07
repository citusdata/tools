#!/bin/bash

# Inspired by https://gist.github.com/petere/6023944

set -eux

# import the PostgreSQL repository key
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# add the PostgreSQL 9.5 repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main 9.5" >> /etc/apt/sources.list.d/postgresql.list'

# update package index files from sources
sudo apt-get update -qq

# remove traces of PostgreSQL versions
# see: postgresql.org/message-id/20130508192711.GA9243@msgid.df7cb.de
sudo update-alternatives --remove-all postmaster.1.gz
