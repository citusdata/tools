docker build -t test_focal .
docker run -it --entrypoint /bin/bash test_focal
