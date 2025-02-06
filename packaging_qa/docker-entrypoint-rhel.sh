#!/bin/bash
set -e

# Set PG_MAJOR to 15 by default if not provided
if command -v psql &> /dev/null; then
    PG_MAJOR=$(psql -V | awk '{print $3}' | cut -d. -f1)
else
    PG_MAJOR=15
fi

# Define PostgreSQL paths dynamically
PG_CTL="/usr/pgsql-${PG_MAJOR}/bin/pg_ctl"
PG_DATA_DIR="/var/lib/pgsql/${PG_MAJOR}/data"
PG_LOG="/var/lib/pgsql/logfile"
PG_BIN="/usr/pgsql-${PG_MAJOR}/bin/postgres"
PG_ISREADY="/usr/pgsql-${PG_MAJOR}/bin/pg_isready"

# Ensure PostgreSQL data directory exists
if [ ! -d "$PG_DATA_DIR" ]; then
    echo "Initializing PostgreSQL data directory: $PG_DATA_DIR"
    mkdir -p "$PG_DATA_DIR"
    chown -R postgres:postgres "$PG_DATA_DIR"
    chmod 700 "$PG_DATA_DIR"
    /usr/pgsql-${PG_MAJOR}/bin/initdb -D "$PG_DATA_DIR"
fi

# Start PostgreSQL in the background
$PG_CTL -D "$PG_DATA_DIR" -l "$PG_LOG" start

# Wait for PostgreSQL to be ready
until $PG_ISREADY -q -d postgres; do
    sleep 1
done

# Ensure Citus extension is installed
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS citus;"
psql -U postgres -c "SELECT * FROM pg_extension WHERE extname = 'citus';"

# Stop PostgreSQL before running the container foreground process
$PG_CTL -D "$PG_DATA_DIR" stop

# Start PostgreSQL in the foreground
exec $PG_BIN -D "$PG_DATA_DIR"
