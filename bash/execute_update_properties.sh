#!/bin/bash

python ../../python/update_package_properties.py --gh_token "${GITHUB_TOKEN}" --prj_name "${PRJ_NAME}" --prj_ver "${PRJ_VER}"  --tag_name "${TAG_NAME}" --fancy "${FANCY}" \
--fancy_ver_no "${FANCY_VERSION_NO}" --email "${MICROSOFT_EMAIL}" --name "${NAME}" --date "$(date  '+%Y.%m.%d %H:%M:%S &z')" --exec-path "$(pwd)" &>2

