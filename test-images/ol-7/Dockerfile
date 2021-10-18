FROM oraclelinux:7

ARG CITUS_VERSION
# Format should be XY and should not include dots e.g for 10.2.1=>102
ARG CITUS_MAJOR_VERSION
ARG PG_MAJOR
ARG FANCY=1
ARG HLL_VERSION=2.16.citus-1
ARG TOPN_VERSION=2.4.0.citus-1
ARG PACKAGE_RELEASE_SUFFIX=el7

ENV CITUS_VERSION ${CITUS_VERSION}

ENV PG_MAJOR ${PG_MAJOR}


RUN yum update -y && \
    yum install -y curl



RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

RUN export CITUS_MAJOR_VER=${CITUS_MAJOR_VERSION//./} && \
    curl https://install.citusdata.com/community/rpm.sh |  bash && \
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
# Install python 3.8 and its dependencies
RUN yum install -y gcc make && \
    yum -y install  libcurl-devel \
                    openssl-devel \
                    bzip2-devel \
                    libffi-devel \
                    xz-devel \
                    python38-devel \
                    openssl-devel &&\
      curl  https://www.python.org/ftp/python/3.8.12/Python-3.8.12.tgz --output Python-3.8.12.tgz &&\
      tar xvf Python-3.8.12.tgz &&\
      cd Python-3.8.*/ && \
      ./configure --enable-optimizations && \
       make altinstall && \
       python3.8 -m pip install pip-tools

COPY scripts/* ./

RUN pip-compile && python3.8 -m pip install -r requirements.txt


USER postgres

WORKDIR ${POSTGRES_HOME}

CMD ["test_internal.sh"]

