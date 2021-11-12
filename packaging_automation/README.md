## Python Environment Installation

Before using script, you need to make sure that latest Python 3.8 is installed in your system.

### Clone Tools Repository

```console
git clone https://github.com/citusdata/tools.git
cd tools
```

### Install Required Python Libraries

Verify Python installation is 3.8

```console
python --version
Python 3.8.12
```

Install the required libraries to execute the script

```console
make -C packaging_automation install
```

If you get an error, you should first install pip

```console
sudo apt install python3-pip
```

If all the steps above completed successfully, you are ready for script execution

# Prepare Release

prepare-release.py script performs the pre-packaging configurations in citus/citus-enterprise projects.

## Script Usage

Script can be used for either major release (i.e. third digit of release is '0' e.g. 10.1.0) or patch release (i.e.
third digit of release is other than '0' e.g. 10.0.4).

### Available flags

`--gh_token`: (Required) Personal access token that is authorized to commit citus/citus-enterprise projects.
`--prj_name`: (Required) Project to be released. Allowed values 'citus' and 'citus-enterprise
`--prj_ver`: (Required) Upcoming version to be used for release. Should be in the format vX.Y.Z
`--main_branch`: Branch to be used as base to be used for configuration changes. There is no need for base scenario. This flag can be used for testing purposes. If not used, default branch value is used; e.g. `master` for `citus` and `enterprise-master` for `citus-enterprise`
`--is_test`: (Default:false) If used, branches would not be pushed remote repository and created release branches would be prefixed with `test`.
`--cherry_pick_enabled`: Available only for patch release. If used, `--earliest_pr_date` flag also should be used. Gets all PR's with `backport` label created after `earliest_pr_date`
`--earliest_pr_date`: Required if `--cherry-pick-enabled` flag is set. Date format is `YYYY.MM.DD` e.g `2012.01.21`. PR's merged after this date would be listed and cherry-picked.
`--schema_version`: Available only for patch release. If used, schema version in `citus.control` file would be updated.

### Example Usage

#### Major

```console
python -m packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus --prj_ver 10.1.0
```

#### Patch

```console
python -m packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus-enterprise --prj_ver 10.0.4 --schema_version 10.0-5
```

## Update Package Properties

Update package properties script updates debian and redhat package configuration files.

## Script Usage

Script can be used in projects following: `citus`, `citus-enterprise`, `pg-auto-failover`, `pg-auto-failover-enterprise`

## Available flags

`--gh_token`: (Required) Personal access token that is authorized to commit citus/citus-enterprise projects.
`--prj_name`: (Required) Project to be released. Allowed values `citus` and `citus-enterprise`
`--tag_name`: (Required) Tag to be used for release. Should be in the format vX.Y.Z
`--fancy_ver_no`: (Default=1) If set and greater than 1, fancy versioning is enabled
`--email`: (Required) Email to be printed in changelogs
`--name`: (Required) Name to be printed in changelogs
`--date`: Date to be printed in changelogs
`--pipeline`: (Default=false) If set, exec path should also be set and exec path will be used as packaging source. If not set, packaging code will be cloned
`--exec_path`: If pipeline parameter is used, this parameter should be set. Shows the path of packaging sources
`--is_test`: If true, the branch created will not be published into remote repository

### Example Usage

```console
python -m packaging_automation.update_package_properties \
       --gh_token=${{ secrets.GH_TOKEN }} \
       --prj_name "${PRJ_NAME}" \
       --tag_name ${{ github.event.inputs.tag_name }} \
       --email ${{ github.event.inputs.microsoft_email }} \
       --name ${{ github.event.inputs.name }} \
       --pipeline \
       --exec_path "$(pwd)"
```

## Update Docker

Update docker script updates the docker and changelog files in docker repository required for new release of docker images after citus/postgres release

## Script Usage

Script can be used for both citus version upgrades and PostgreSQL updates.

### Available flags

`--gh_token`: (Required) Personal access token that is authorized to commit docker project.
`--postgres_version`: Optional value that could be set when new postgres version needs to be set in docker images
`--prj_ver`: (Required) Upcoming version to be used for release. Should be in the format vX.Y.Z
`--is_test`: (Optional) If used, branches would not be pushed remote repository and PR would not be created.

### Example

#### Citus Upgrade

```console
 python -m packaging_automation.update_docker --gh_token <your-personal-token> --prj_ver 10.0.4
```

#### Citus and PostgreSQL version upgrade

```console
 python -m packaging_automation.update_docker --gh_token <your-personal-token> --prj_ver 10.0.4 --postgres-version 14.0
```

## Update Pgxn

Update pgxn script updates the files related to pgxn in `all-pgxn` branch in packaging repo.

## Script Usage

Script can be used for citus version upgrades.

### Available flags

`--gh_token`: (Required) Personal access token that is authorized to commit packaging project.
`--prj_ver`: (Required) Upcoming version to be used for release. Should be in the format vX.Y.Z
`--is_test`: (Optional) If used, branches would not be pushed remote repository and PR would not be created

### Example

```console
 python -m packaging_automation.update_pgxn --gh_token <your-personal-token> --prj_ver 10.0.4
```

## Upload to package cloud

This script uploads built deb and rpm packages.

## Script usage

This script uploads all the rpm and deb packages from given directory into package cloud,if current branch equals to main branch .

### Available flags

`--platform`: (Required) Personal access token that is authorized to commit packaging project.
`--package_cloud_api_token`: (Required) Token required to get authorization from package cloud to upload
`--repository_name`: (Required) Packagecloud repository name to upload. Available repos: `sample`, `citusdata/enterprise`, `citusdata/community`, `citusdata/community-nightlies`, `citusdata/enterprise-nightlies`, `citusdata/azure`
`--output_file_path`: (Required) Directory that contains deb and rpm files
`--current_branch`: (Required) Current branch that the pipeline is working on
`--main_branch`: (Required) Main branch that is the script to be executed

### Example

```console
 python -m tools.packaging_automation.upload_to_package_cloud \
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

`--github_ref`: (Required) Github Action parameter denoting tag or branch name depending on trigger type.
`--pipeline_trigger_type`: (Required) Pipeline trigger type. Available options: `push`, `schedule`, `workflow_dispatch`
`--tag_name`: Tag name if trigger type is push
`--manual_trigger_type`: (Required) Trigger type when executing the script manually. Available options: `main`, `tags`, `nightly`
`--image_type`: Image type to be published. Available options: `latest`, `alpine`, `nightly`, `postgres12`

### Example

```console
python -m tools.packaging_automation.publish_docker \
       --pipeline_trigger_type "${GITHUB_EVENT_NAME}" \
       --exec_path "$(pwd)" \
       --tag_name ${{ github.event.inputs.tag_name }} \
       --manual_trigger_type ${{ github.event.inputs.trigger_type }}
```
