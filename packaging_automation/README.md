# **Prepare Release Usage**

prepare-release.py script performs the  pre-packaging configurations in citus/citus-enterprise projects.

## Installation

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

## Script Usage

Script can be used for either major release (i.e. third digit of release is '0' e.g. 10.1.0)  or 
patch release (i.e. third digit of release is other than '0' e.g. 10.0.4).

### Available flags

**--gh_token:** Personal access token that is authorized to commit citus/citus-enterprise projects. (Required)

**--prj_name:** Project to be released. Allowed values 'citus' and 'citus-enterprise (Required)

**--prj_ver:** Upcoming version to be used for release. should include three level of digits separated by dots, e.g: 10.0.1
(Required)

**--main-branch:** Branch to be used as base to be used for configuration changes. There is no need for base scenario. 
This flag can be used for testing purposes. If not used, default branch value is used; i.e. for 'citus' 'master, for 'citus-enterprise' 'enterprise-master'

**--is_test:** If used, branches would not be pushed remote repository and created release branches would be prefixed with 'test'. Default value is False

**--cherry_pick_enabled:** Available only for patch release. If used, --earliest_pr_date flag also should be used.Gets all PR's with 'backport' label created after earliest_pr_date

**--earliest_pr_date:** Used with --cherry-pick-enabled flag. Date format is 'Y.m.d' e.g 2012.01.21. PR's merged after this date would be listed and cherry-picked.

**--schema-version:** Available only for patch release. If used, schema version in citus.control file would be updated.

###Example Usage

####Major
``` console
python -m  packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus --prj_ver 10.1.0 
```
#### Patch
``` console
python -m  packaging_automation.prepare_release --gh_token <your-personal-token> --prj_name citus-enterprise --prj_ver 10.0.4 --schema_version 10.0-5
```



