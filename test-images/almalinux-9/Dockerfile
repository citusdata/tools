FROM almalinux:9
ARG CITUS_VERSION
# Format should be XY and should not include dots e.g for 10.2.1=>102
ARG CITUS_MAJOR_VERSION
ARG PG_MAJOR
ARG FANCY=1
ARG HLL_VERSION=2.18.citus-1
ARG TOPN_VERSION=2.6.0.citus-1
ARG PACKAGE_RELEASE_SUFFIX=el9

ENV CITUS_VERSION ${CITUS_VERSION}

ENV PG_MAJOR ${PG_MAJOR}


RUN yum update -y

    
# TODO Parameterize Citus and postgres version
RUN export CITUS_MAJOR_VER=${CITUS_MAJOR_VERSION//./} && \
    curl https://raw.githubusercontent.com/citusdata/packaging/gh-pages/community/rpm.sh |  bash && \
    yum install -y citus${CITUS_MAJOR_VER}_${PG_MAJOR}-${CITUS_VERSION}.citus-${FANCY}.${PACKAGE_RELEASE_SUFFIX} \
           hll_${PG_MAJOR}-${HLL_VERSION}.${PACKAGE_RELEASE_SUFFIX} \
           topn_${PG_MAJOR}-${TOPN_VERSION}.${PACKAGE_RELEASE_SUFFIX}

    
ARG POSTGRES_HOME=/var/lib/pgsql
ENV PATH=/usr/pgsql-${PG_MAJOR}/bin:${PATH}:${POSTGRES_HOME}

WORKDIR ${POSTGRES_HOME}

RUN mkdir citus && chown postgres citus





USER postgres
RUN cd ~ && initdb -D citus && echo "shared_preload_libraries = 'citus'" >> citus/postgresql.conf

USER root
# Enable EPEL repository and install dependencies for Python 3.8
RUN yum install -y epel-release && \
    yum install -y gcc make libcurl-devel openssl-devel bzip2-devel libffi-devel xz-devel wget tar zlib-devel && \
    wget https://www.python.org/ftp/python/3.8.12/Python-3.8.12.tgz && \
    tar xvf Python-3.8.12.tgz && \
    cd Python-3.8.12 && \
    ./configure --enable-optimizations && \
    make altinstall && \
    python3.8 -m pip install pip-tools


COPY scripts/* ./

# Use pip-tools to compile and install requirements
RUN pip-compile && python3.8 -m pip install -r requirements.txt

USER postgres

WORKDIR ${POSTGRES_HOME}

CMD ["test_internal.sh"]

