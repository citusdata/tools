# Use Ubuntu 22.04 Jammy as the base image
# FROM ubuntu:22.04

# Use Ubuntu 20.04 Focal as the base image
FROM ubuntu:20.04


# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ARG VERSION=13.0.1
ENV CITUS_VERSION=${VERSION}.citus-1
ENV PG_MAJOR=17

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    sudo

# Add PostgreSQL repository
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | tee /etc/apt/trusted.gpg.d/postgresql.asc && \
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list

# Install PostgreSQL $PG_MAJOR and required packages
RUN apt-get update && apt-get install -y postgresql-$PG_MAJOR postgresql-contrib

# Install Citus repository and required extensions
RUN curl -s https://install.citusdata.com/community/deb.sh | bash && \
    apt-get update && apt-get install -y \
        postgresql-$PG_MAJOR-citus-13.0=$CITUS_VERSION \
        postgresql-$PG_MAJOR-hll=2.18.citus-1 \
        postgresql-$PG_MAJOR-topn=2.7.0.citus-1

# Ensure PostgreSQL data directory exists and has correct permissions
RUN mkdir -p /var/lib/postgresql/$PG_MAJOR/main && chown -R postgres:postgres /var/lib/postgresql && chmod -R 700 /var/lib/postgresql

# Switch to postgres user before running PostgreSQL
USER postgres

# Initialize the database only if it's not already initialized
RUN bash -c '[ ! -f "/var/lib/postgresql/${PG_MAJOR}/main/PG_VERSION" ] && /usr/lib/postgresql/${PG_MAJOR}/bin/initdb -D /var/lib/postgresql/${PG_MAJOR}/main || echo "Database already initialized"'

# Fix pg_hba.conf to allow connections
RUN echo "local   all             postgres                                trust" > /var/lib/postgresql/$PG_MAJOR/main/pg_hba.conf && \
    echo "local   all             all                                     md5" >> /var/lib/postgresql/$PG_MAJOR/main/pg_hba.conf && \
    echo "host    all             all             127.0.0.1/32            md5" >> /var/lib/postgresql/$PG_MAJOR/main/pg_hba.conf && \
    echo "host    all             all             ::1/128                 md5" >> /var/lib/postgresql/$PG_MAJOR/main/pg_hba.conf

# Add Citus to PostgreSQL config
RUN echo "shared_preload_libraries = 'citus'" >> /var/lib/postgresql/$PG_MAJOR/main/postgresql.conf

# Create an entrypoint script to start PostgreSQL properly
USER root
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch back to postgres user
USER postgres

# Use custom entrypoint to start PostgreSQL and create the Citus extension
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Expose PostgreSQL port
EXPOSE 5432
