#!/bin/bash
set -e

# Set PG_MAJOR to 16 by default if not provided
PG_MAJOR=${PG_MAJOR:-16}

# Define PostgreSQL paths dynamically
PG_CTL="/usr/lib/postgresql/${PG_MAJOR}/bin/pg_ctl"
PG_DATA_DIR="/var/lib/postgresql/${PG_MAJOR}/main"
PG_LOG="/var/lib/postgresql/logfile"
PG_BIN="/usr/lib/postgresql/${PG_MAJOR}/bin/postgres"

# Ensure PostgreSQL data directory exists
if [ ! -d "$PG_DATA_DIR" ]; then
    echo "Error: PostgreSQL data directory $PG_DATA_DIR does not exist!"
    exit 1
fi

# Start PostgreSQL in the background
$PG_CTL -D "$PG_DATA_DIR" -l "$PG_LOG" start

# Wait for PostgreSQL to be ready
until pg_isready -q -d postgres; do
    sleep 1
done

# Ensure Citus extension is installed
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS citus;"
psql -U postgres -c "SELECT * FROM pg_extension WHERE extname = 'citus';"

# Stop PostgreSQL before running the container foreground process
$PG_CTL -D "$PG_DATA_DIR" stop

# Start PostgreSQL in the foreground
exec $PG_BIN -D "$PG_DATA_DIR"
