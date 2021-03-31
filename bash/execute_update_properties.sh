#!/bin/bash

git clone https://github.com/citusdata/packaging.git
cd packaging
git checkout all-citus
python ../../python/update_package_properties.py --gh_token "${GITHUB_TOKEN}" --prj_name "${PRJ_NAME}" --tag_name "${TAG_NAME}" --fancy "${FANCY}" \
  --fancy_ver_no "${FANCY_VERSION_NO}" --email "${MICROSOFT_EMAIL}" --name "${NAME}" --date "$(date  '+%Y.%m.%d %H:%M:%S &z')" --exec-path "$(pwd)" &>2

#cd ..
#echo "Removing Packaging directory..."
#rm -r packaging
#echo "Packaging directory Removed"
