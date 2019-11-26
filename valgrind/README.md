# valgrind-test-automation

Tools for automating Valgrind tests with Citus. This automation suite will open an instance in AWS and runs Citus with Valgrind. When tests are completed, it will send a mail to burak@citusdata.com and metin@citusdata.com with the valgrind logs. Logs will contain memory related problems and the call stack where each problem is found. If there are no problems, no report will be attached. Only a success message will be sent.

# Usage

You first need to install and configure aws command line client. Refer [here](http://docs.aws.amazon.com/cli/latest/userguide/installing.html) to see how to install aws command line client. After installation, configure it with `aws configure` command. Then to use aws instance for valgrind tests, run;

```sh
./launch-test-instance.sh
```

This command will create a special key pair and start an m3.xlarge instance with that key pair. Created instance will be tagged with Name=ValgrindTest. Then, scripts will build PostgreSQL and Citus from source and runs Citus' regression tests with Valgrind. After tests are completed, valgrind logs will be sent to burak@citusdata.com and metin@citusdata.com for now and instance will terminate itself. It is expected that the tests will take about 5 hours to complete.


# Notes on enterprise-manual-testing branch

Some of the notes above maybe invalid, please read the following.
After doing the improvements below, this readme will also be updated.

run-valgrind-tests:
-------------------
This script installs postgresql-12.0, clones enterprise-master and runs valgrind tests.
To clone enterprise-master, it will ask you to enter your github credentials.
Run this script in a detachable session (tmux, screen ..) for detaching after the valgrind test starts.
It does not send an email for logs.txt etc. for now

launc-test-instance:
--------------------
This script creates an instance on ec2 (just like in the develop branch).
However, it does not start valgrind testing, does not send email and does not shutdown the machine.
It just copies run-valgrind-tests script to the machine we just created and echoes the ssh command to reach that machine.

TODO: improvements to be done on this branch before merging to develop (and then to master):
- automate enterprise repository clonning.
- send email or push logs to an appropriate github repository (maybe we can use test automation scripts).
- parameterize postgresql version.
- parameterize enterprise repository branch name.
- parameterize and divide the pipeline into steps (install postgresql, install citus, just run the tests or all etc.).
- parameterize testing on community or enterprise repository.

