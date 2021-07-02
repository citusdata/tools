#!/bin/bash
[ -z "${JOB_NAME:-}" ] && echo "JOB_NAME should be non-empty value" && exit 1
[ -z "${DB_USER_NAME:-}" ] && echo "DB_USER_NAME should be non-empty value" && exit 1
[ -z "${DB_PASSWORD:-}" ] && echo "DB_PASSWORD should be non-empty value" && exit 1
[ -z "${DB_HOST_AND_PORT:-}" ] && echo "DB_HOST_AND_PORT should be non-empty value" && exit 1
[ -z "${DB_NAME:-}" ] && echo "DB_NAME should be non-empty value" && exit 1

if [[ ${JOB_NAME} == 'docker_pull_citus' ]]; then
  python -m packaging_automation.docker_statistics_collector --repo_name citus \
    --db_user_name "${DB_USER_NAME}" --db_password "${DB_PASSWORD}" --db_host_and_port "${DB_HOST_AND_PORT}" \
    --db_name "${DB_NAME}"
elif [[ ${JOB_NAME} == 'github_clone_citus' ]]; then
  [ -z "${GH_TOKEN:-}" ] && echo "GH_TOKEN should be non-empty value" && exit 1
  python -m packaging_automation.github_statistics_collector --repo_name citus \
    --db_user_name "${DB_USER_NAME}" --db_password "${DB_PASSWORD}" --db_host_and_port "${DB_HOST_AND_PORT}" \
    --db_name "${DB_NAME}" --github_token "${GH_TOKEN}"
fi
