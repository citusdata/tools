#!/bin/bash
[ -z "${JOB_NAME:-}" ] && echo "JOB_NAME should be non-empty value" && exit 1
if [[${JOB_NAME}='docker_pull_citus']]
then
    python -m packaging_automation.docker_statistics_collector --repo_name citus
fi
