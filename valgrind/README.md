# valgrind-test-automation

Tools for automating Valgrind tests with Citus. This automation suite will open an instance in AWS and runs Citus with Valgrind. When tests are completed, it will send a mail to burak@citusdata.com and metin@citusdata.com with the valgrind logs. Logs will contain memory related problems and the call stack where each problem is found. If there are no problems, no report will be attached. Only a success message will be sent.

# Usage

You first need to install and configure aws command line client. Refer [here](http://docs.aws.amazon.com/cli/latest/userguide/installing.html) to see how to install aws command line client. After installation, configure it with `aws configure` command. Then to use aws instance for valgrind tests, run;

```sh
./launch-test-instance.sh
```

This command will create a special key pair and start an m3.xlarge instance with that key pair. Created instance will be tagged with Name=ValgrindTest. Then, scripts will build PostgreSQL and Citus from source and runs Citus' regression tests with Valgrind. After tests are completed, valgrind logs will be sent to burak@citusdata.com and metin@citusdata.com for now and instance will terminate itself. It is expected that the tests will take about 5 hours to complete.
