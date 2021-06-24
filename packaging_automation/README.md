## Python Environment Installation

Before using script, you need to make sure that Python > 3.8 is installed in your system.

### Clone Tools Repository

git clone https://github.com/citusdata/tools.git

Enter 'tools' directory

``` console
cd tools
```

### Install Required Python Libraries

Verify pip installation

``` console
python -m pip --version
```

Output should be like following

``` console
pip 21.1.2 from /home/vagrant/.local/lib/python3.8/site-packages/pip (python 3.8)
```

If you get error, you should first install pip

``` console
sudo apt install python3-pip
```

Install the required libraries to execute the script

``` console
python -m pip install -r packaging_automation/requirements.txt
```

If all the steps above completed successfully , you are ready for script execution

# **Prepare Release Usage**

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

**--cherry_pick_enabled:** Available only for patch release. If used, --earliest_pr_date flag also should be used.Gets
all PR's with 'backport' label created after earliest_pr_date

**--earliest_pr_date:** Used with --cherry-pick-enabled flag. Date format is 'Y.m.d' e.g 2012.01.21. PR's merged after
this date would be listed and cherry-picked.

**--schema_version:** Available only for patch release. If used, schema version in citus.control file would be updated.

### Example Usage

#### Major

``` console
python -m  packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus --prj_ver 10.1.0
```

#### Patch

``` console
python -m  packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus-enterprise --prj_ver 10.0.4 --schema_version 10.0-5
```

## Update Docker Usage

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

### Example Usage

#### Citus Upgrade

``` console
 python -m  packaging_automation.update_docker --gh_token <your-personal-token>  --prj_ver 10.0.4
```

#### Citus and PostgreSQL version upgrade

``` console
 python -m  packaging_automation.update_docker --gh_token <your-personal-token>  --prj_ver 10.0.4 --postgres-version 14.0
```

## Update Pgxn Usage

Update pgxn script updates the files related to pgxn in all-pgxn branch in packaging repo.

## Script Usage

Script can be used for  citus version upgrades.

### Available flags

**--gh_token:** Personal access token that is authorized to commit packaging project. (Required)

**--prj_ver:** Upcoming version to be used for release. should include three level of digits separated by dots, e.g:
10.0.1
(Required)

**--is_test:** If used, branches would not be pushed remote repository and PR would not be created (Optional)

### Example Usage

#### Citus Upgrade

``` console
 python -m  packaging_automation.update_pgxn --gh_token <your-personal-token> --prj_ver 10.0.4
```
