# Enterprise Merge Automation

Tools for automating git merges from Citus community to enterprise. The documentation for the process is at https://github.com/citusdata/citus-enterprise/blob/enterprise-master/ci/README.md#check_enterprise_mergesh

The script is designed to be able to resume where it left off, in the case that it failed on some of the steps.

It is also possible to force the script to start from a particular step by providing an optional parameter.

# Dependencies

The script depends on [GitHub Cli](https://github.com/cli/cli) to be able to open PRs after the merges are complete.

# Usage

The script expects to be run inside the Citus Enterprise repo directory.

```sh
enterprise_merge $PR_BRANCH
# e.g.
enterprise_merge my_feature_branch_name_on_citus_community
```

You can also supply an optional step number to force the script to start from that particular step.

```sh
enterprise_merge $PR_BRANCH $STEP_NUMBER
# e.g. to force the tool to start from pushing the branch to remote
enterprise_merge my_feature_branch_name_on_citus_community 7
```
