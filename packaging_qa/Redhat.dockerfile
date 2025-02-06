# RHEL 8-based	EL8	rockylinux:8 / ubi8
# RHEL 9-based	EL9	rockylinux:9 / ubi9
# Oracle Linux 8	OL8	oraclelinux:8 # may need to run docker pull oraclelinux:8
# Oracle Linux 9	OL9	oraclelinux:9
# Use Red Hat or Oracle Linux as the base image
ARG OS_TYPE=oraclelinux
ARG VERSION_ID=8
ARG BASE_IMAGE=${OS_TYPE}:${VERSION_ID}
FROM $BASE_IMAGE

# Set environment variables to avoid interactive prompts
ARG CITUS_VERSION_FULL=13.0.1
ARG CITUS_VERSION_COMPACT=130
ARG PG_MAJOR=17

# Install dependencies
RUN dnf install -y --allowerasing \
    epel-release \
    dnf-utils \
    sudo \
    curl \
    gnupg2 \
    which \
    libffi-devel \
    readline-devel \
    gcc \
    make \
    which \
    tar

# Add PostgreSQL repository based on EL version
RUN export EL_VERSION=$(source /etc/os-release && echo ${VERSION_ID%%.*}) && \
    dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-${EL_VERSION}-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# Disable built-in PostgreSQL module
RUN dnf -qy module disable postgresql

# Install PostgreSQL and required packages
RUN dnf install -y postgresql${PG_MAJOR} postgresql${PG_MAJOR}-server postgresql${PG_MAJOR}-contrib

# Install Citus repository and extensions
RUN export VERSION_ID=$(source /etc/os-release && echo ${VERSION_ID%%.*}) && \
    curl -s https://packagecloud.io/install/repositories/citusdata/community/script.rpm.sh | sudo bash && \
    yum install -y citus${CITUS_VERSION_COMPACT}_${PG_MAJOR}-${CITUS_VERSION_FULL}.citus-1.el${VERSION_ID}.x86_64 \
                   topn_${PG_MAJOR}-2.7.0.citus-1.el${VERSION_ID}.x86_64 \
                   hll_${PG_MAJOR}-2.18.citus-1.el${VERSION_ID}.x86_64

# Ensure PostgreSQL data directory exists and has correct permissions
RUN mkdir -p /var/lib/pgsql/${PG_MAJOR}/data && chown -R postgres:postgres /var/lib/pgsql && chmod -R 700 /var/lib/pgsql

# Switch to postgres user before running PostgreSQL
USER postgres

# Initialize the database only if it's not already initialized
RUN [ ! -f "/var/lib/pgsql/${PG_MAJOR}/data/PG_VERSION" ] && /usr/pgsql-${PG_MAJOR}/bin/initdb -D /var/lib/pgsql/${PG_MAJOR}/data || echo "Database already initialized"

# Fix pg_hba.conf to allow connections
RUN echo "local   all             postgres                                trust" > /var/lib/pgsql/${PG_MAJOR}/data/pg_hba.conf && \
    echo "local   all             all                                     md5" >> /var/lib/pgsql/${PG_MAJOR}/data/pg_hba.conf && \
    echo "host    all             all             127.0.0.1/32            md5" >> /var/lib/pgsql/${PG_MAJOR}/data/pg_hba.conf && \
    echo "host    all             all             ::1/128                 md5" >> /var/lib/pgsql/${PG_MAJOR}/data/pg_hba.conf

# Add Citus to PostgreSQL config
RUN echo "shared_preload_libraries = 'citus'" >> /var/lib/pgsql/${PG_MAJOR}/data/postgresql.conf

# Create an entrypoint script to start PostgreSQL properly
USER root
COPY docker-entrypoint-rhel.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint-rhel.sh

# Switch back to postgres user
USER postgres

# Use custom entrypoint to start PostgreSQL and create the Citus extension
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-rhel.sh"]

# Expose PostgreSQL port
EXPOSE 5432
