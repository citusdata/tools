# This file is auto generated from it's template,
# see citusdata/tools/packaging_automation/templates/docker/latest/latest.tmpl.dockerfile.
FROM ubuntu:focal
ARG VERSION
ARG PG_MAJOR
LABEL maintainer="Citus Data https://citusdata.com" \
      org.label-schema.name="Citus" \
      org.label-schema.description="Scalable PostgreSQL for multi-tenant and real-time workloads" \
      org.label-schema.url="https://www.citusdata.com" \
      org.label-schema.vcs-url="https://github.com/citusdata/citus" \
      org.label-schema.vendor="Citus Data, Inc." \
      org.label-schema.version=${VERSION} \
      org.label-schema.schema-version="1.0"

ENV CITUS_VERSION ${VERSION}.citus-1

ENV TZ=Europe/Istanbul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# install prequisities
RUN apt-get update \
    && apt-get install -y   lsb-release \
                            apt-utils \
                            vim \
                            wget \
                            curl \
                            gnupg2 \
                            software-properties-common \
                            python3.8 \
                            python3-pip \
                            libcurl4-openssl-dev \
                            libssl-dev \
    && pip install pip-tools


# install Citus
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
    && curl -s https://install.citusdata.com/community/deb.sh | bash
RUN apt-get install -y postgresql-$PG_MAJOR-citus-10.2=$CITUS_VERSION \
                          postgresql-$PG_MAJOR-hll=2.16.citus-1 \
                          postgresql-$PG_MAJOR-topn=2.4.0 \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*12



ARG POSTGRES_HOME=/var/lib/postgresql/
ENV PATH=${PATH}:/usr/lib/postgresql/14/bin:$POSTGRES_HOME

WORKDIR /var/lib/postgresql/

RUN mkdir citus && chown postgres citus

COPY test.sh test_internal.sh requirements.in test.py ./

RUN  pip-compile && python3.8 -m pip install -r requirements.txt


USER postgres
RUN cd ~ && initdb -D citus && echo "shared_preload_libraries = 'citus'" >> citus/postgresql.conf


CMD ["test_internal.sh"]











