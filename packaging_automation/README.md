## Python Environment Installation

Before using script, you need to make sure that Python > 3.8 is installed in your system.

### Clone Tools Repository

git clone https://github.com/citusdata/tools.git

Enter 'tools' directory

```console
cd tools
```

### Install Required Python Libraries

Verify pip installation

```console
python -m pip --version
```

Output should be like following

```console
pip 21.1.2 from /home/vagrant/.local/lib/python3.8/site-packages/pip (python 3.8)
```

If you get error, you should first install pip

```console
sudo apt install python3-pip
```

Install the required libraries to execute the script

```console
python -m pip install -r packaging_automation/requirements.txt
```

If all the steps above completed successfully , you are ready for script execution

# **Prepare Release **

prepare-release.py script performs the pre-packaging configurations in citus/citus-enterprise projects.

## Script Usage

Script can be used for either major release (i.e. third digit of release is '0' e.g. 10.1.0)  or patch release (i.e.
third digit of release is other than '0' e.g. 10.0.4).

### Available flags

**--gh_token:** Personal access token that is authorized to commit citus/citus-enterprise projects. (Required)

**--prj_name:** Project to be released. Allowed values 'citus' and 'citus-enterprise (Required)

**--prj_ver:** Upcoming version to be used for release. should include three level of digits separated by dots, e.g:
10.0.1
(Required)

**--main_branch:** Branch to be used as base to be used for configuration changes. There is no need for base scenario.
This flag can be used for testing purposes. If not used, default branch value is used; i.e. for 'citus' 'master, for '
citus-enterprise' 'enterprise-master'

**--is_test:** If used, branches would not be pushed remote repository and created release branches would be prefixed
with 'test'. Default value is False

**--cherry_pick_enabled:** Available only for patch release. If used, --earliest_pr_date flag also should be used. Gets
all PR's with 'backport' label created after earliest_pr_date

**--earliest_pr_date:** Used with --cherry-pick-enabled flag. Date format is 'Y.m.d' e.g 2012.01.21. PR's merged after
this date would be listed and cherry-picked.

**--schema_version:** Available only for patch release. If used, schema version in citus.control file would be updated.

### Example Usage

#### Major

```console
python -m  packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus --prj_ver 10.1.0
```

#### Patch

```console
python -m  packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus-enterprise --prj_ver 10.0.4 --schema_version 10.0-5
```

## Update Package Properties

Update package properties script updates debian and redhat package configuration files.

## Script Usage

Script can be used in projects following: citus, citus-enterprise, pg-auto-failover, pg-auto-failover-enterprise

## Available flags

**--gh_token:** Personal access token that is authorized to commit citus/citus-enterprise projects. (Required)

**--prj_name:** Project to be released. Allowed values 'citus' and 'citus-enterprise (Required)

**--tag-name:** Tag to be used for release. should include three level of digits separated by dots starting with v, e.g:
v10.0.1
(Required)

**--fancy_ver_no:** If not set default is 1 and fancy versioning is disabled. If set and greater than 1, fancy is enabled

**--email:** Email to be printed in changelogs (Required)

**--name:** Name to be printed in changelogs (Required)

**--date:**: Date to be printed in changelogs

**--pipeline:** If set, exec path should also be set and exec path will be used as packaging source. If not set, it is evaluated as false and packaging code will be cloned

**--exec_path:** If pipeline parameter is used, this parameter should be set. Shows the path of packaging sources

**--is_test:** If true, the branch created will not be published into remote repository

### Example Usage

```console
python -m packaging_automation.update_package_properties --gh_token=${{ secrets.GH_TOKEN }} \
              --prj_name "${PRJ_NAME}" --tag_name ${{ github.event.inputs.tag_name }} \
              --email ${{ github.event.inputs.microsoft_email }} --name ${{ github.event.inputs.name }} --pipeline \
              --exec_path "$(pwd)"
```

## Update Docker

Update docker script updates the docker and changelog files in docker repository required for new release of docker
images after citus/postgres release

## Script Usage

Script can be used for both citus version upgrades and PostgreSQL updates.

### Available flags

**--gh_token:** Personal access token that is authorized to commit docker project. (Required)

**--postgres_version:** Optional value that could be set when new postgres version needs to be set in docker images

**--prj_ver:** Upcoming version to be used for release. should include three level of digits separated by dots, e.g:
10.0.1
(Required)

**--is_test:** If used, branches would not be pushed remote repository and PR would not be created (Optional)

### Example

#### Citus Upgrade

```console
 python -m  packaging_automation.update_docker --gh_token <your-personal-token>  --prj_ver 10.0.4
```

#### Citus and PostgreSQL version upgrade

```console
 python -m  packaging_automation.update_docker --gh_token <your-personal-token>  --prj_ver 10.0.4 --postgres-version 14.0
```

## Update Pgxn

Update pgxn script updates the files related to pgxn in all-pgxn branch in packaging repo.

## Script Usage

Script can be used for  citus version upgrades.

### Available flags

**--gh_token:** Personal access token that is authorized to commit packaging project. (Required)

**--prj_ver:** Upcoming version to be used for release. should include three level of digits separated by dots, e.g:
10.0.1
(Required)

**--is_test:** If used, branches would not be pushed remote repository and PR would not be created (Optional)

### Example

```console
 python -m  packaging_automation.update_pgxn --gh_token <your-personal-token> --prj_ver 10.0.4
```

## Upload to package cloud

This script uploads built deb and rpm packages.

## Script usage

This script uploads all the rpm and deb packages from given directory into package cloud, if  current branch equals to main branch .

### Available flags

**--platform:** Personal access token that is authorized to commit packaging project. (Required)

**--package_cloud_api_token:** Token required to get authorization from package cloud to upload (Required)

**--repository_name:** Packagecloud repository name to upload Available repos: "sample", "citusdata/enterprise", "citusdata/community", "citusdata/community-nightlies", "citusdata/enterprise-nightlies", "citusdata/azure" (Required)

**--output_file_path:** Directory that contains deb and rpm files (Required)

**--current_branch:** Current branch that the pipeline is working on (Required)

**--main_branch:** Main branch that is the script to be executed (Required)

### Example

```console
 python -m  tools.packaging_automation.upload_to_package_cloud \
          --platform ${{ matrix.platform }} \
          --package_cloud_api_token ${{ secrets.PACKAGE_CLOUD_API_TOKEN }} \
          --repository_name "${PACKAGE_CLOUD_REPO_NAME}" \
          --output_file_path "$(pwd)/packages" \
          --current_branch all-citus \
          --main_branch ${MAIN_BRANCH}
```

## Publish docker

This script builds and publishes given docker image type

## Script Usage

Script executes docker build on given image type and publishes the docker image with related tags

### Available flags

**--github_ref:** Github Action parameter denoting tag or branch name depending on trigger type . (Required)

**--pipeline_trigger_type:** Pipeline trigger type. Available option: push, schedule, workflow_dispatch (Required)

**--tag_name:** Tag name if trigger type is push and

**--manual_trigger_type:** Trigger type when executing the script manually. Available options: main, tags, nightly (Required)

**--image_type:** Image type to be published. Available options: latest, alpine, nightly, postgre12

### Example

```console
            python -m  tools.packaging_automation.publish_docker  --pipeline_trigger_type "${GITHUB_EVENT_NAME}" \
            --exec_path "$(pwd)" --tag_name ${{ github.event.inputs.tag_name }} \
            --manual_trigger_type ${{ github.event.inputs.trigger_type }}
```
