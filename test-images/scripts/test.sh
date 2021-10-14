docker build -t test_centos --build-arg CITUS_VERSION=10.2.1 --build-arg PG_MAJOR=14  --build-arg CITUS_MAJOR_VERSION=102 .
docker run -it  test_centos

docker build -t test_focal .
docker run -it --entrypoint /bin/bash test_focal
