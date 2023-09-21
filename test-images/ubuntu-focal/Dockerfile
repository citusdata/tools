FROM ubuntu:focal
ARG CITUS_VERSION
# FOrmat should be XY and should not include dots e.g for 10.2.1=>102
ARG CITUS_MAJOR_VERSION
ARG PG_MAJOR
ARG FANCY=1
ARG HLL_VERSION=2.18.citus-1
ARG TOPN_VERSION=2.6.0.citus-1

ENV CITUS_VERSION ${CITUS_VERSION}

ENV PG_MAJOR ${PG_MAJOR}

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
                            libcurl4-openssl-dev \
                            libssl-dev


# install Citus
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
    && curl -s https://install.citusdata.com/community/deb.sh | bash
RUN apt-get install -y postgresql-${PG_MAJOR}-citus-${CITUS_MAJOR_VERSION}=${CITUS_VERSION}.citus-${FANCY} \
                       postgresql-$PG_MAJOR-hll=${HLL_VERSION} \
                       postgresql-$PG_MAJOR-topn=${TOPN_VERSION} \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*12



ARG POSTGRES_HOME=/var/lib/postgresql/
ENV PATH=${PATH}:/usr/lib/postgresql/${PG_MAJOR}/bin:${POSTGRES_HOME}

WORKDIR ${POSTGRES_HOME}

RUN mkdir citus && chown postgres citus

USER postgres
RUN cd ~ && initdb -D citus && echo "shared_preload_libraries = 'citus'" >> citus/postgresql.conf

USER root
# Install python 3.8 and its dependencies
RUN apt-get install -y  build-essential \
                    libcurl4-openssl-dev \
                    libssl-dev \
                    zlib1g-dev  \
                    curl \
                    libffi-dev \
                    gnupg2 && \
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











