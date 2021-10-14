FROM centos:8

ARG CITUS_VERSION
# Format should be XY and should not include dots e.g for 10.2.1=>102
ARG CITUS_MAJOR_VERSION
ARG PG_MAJOR
ARG FANCY=1
ARG HLL_VERSION=2.16.citus-1
ARG TOPN_VERSION=2.4.0.citus-1

ENV CITUS_VERSION ${CITUS_VERSION}

ENV PG_MAJOR ${PG_MAJOR}


RUN dnf update -y && \
    dnf module -y install python38 && \
    dnf groupinstall -y 'Development Tools' && \
    dnf install -y curl \
                   libcurl-devel \
                   python38-devel \
                   openssl-devel  && \
    python3.8 -m pip install pip-tools

# TODO Parameterize Citus and postgres version
RUN export CITUS_MAJOR_VER=${CITUS_MAJOR_VERSION//./} && \
    curl https://install.citusdata.com/community/rpm.sh |  bash && \
    yum install -y citus${CITUS_MAJOR_VER}_${PG_MAJOR}-${CITUS_VERSION}.citus-${FANCY}.el8 \
           hll_${PG_MAJOR}-${HLL_VERSION}.el8 \
           topn_${PG_MAJOR}-${TOPN_VERSION}.el8


ARG POSTGRES_HOME=/var/lib/pgsql
ENV PATH=/usr/pgsql-${PG_MAJOR}/bin:${PATH}:${POSTGRES_HOME}

WORKDIR ${POSTGRES_HOME}

RUN mkdir citus && chown postgres citus


COPY scripts/* ./

RUN  pip-compile && python3.8 -m pip install -r requirements.txt

USER postgres
RUN cd ~ && initdb -D citus && echo "shared_preload_libraries = 'citus'" >> citus/postgresql.conf


CMD ["test_internal.sh"]

