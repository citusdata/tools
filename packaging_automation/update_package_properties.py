import argparse
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pathlib2
import string_utils
from parameters_validation import ( validate_parameters,
                                   parameter_validation)

from .common_tool_methods import (find_nth_occurrence_position,
                                  get_project_version_from_tag_name, get_template_environment, initialize_env, run,
                                  create_pr, remove_cloned_code, DEFAULT_ENCODING_FOR_FILE_HANDLING,
                                  DEFAULT_UNICODE_ERROR_HANDLER)
from .common_validations import (is_version, is_tag)

BASE_PATH = pathlib2.Path(__file__).parent.absolute()
REPO_OWNER = "citusdata"
PROJECT_NAME = "packaging"


@dataclass()
class ProjectDetails:
    name: str
    version_suffix: str
    github_repo_name: str
    changelog_project_name: str
    packaging_branch: str


class SupportedProject(Enum):
    citus = ProjectDetails(name="citus", version_suffix="citus", github_repo_name="citus",
                           changelog_project_name="citus", packaging_branch="all-citus")
    citus_enterprise = ProjectDetails(name="citus-enterprise", version_suffix="citus",
                                      github_repo_name="citus-enterprise", changelog_project_name="citus-enterprise",
                                      packaging_branch="all-enterprise")
    pg_auto_failover = ProjectDetails(name="pg-auto-failover", version_suffix="",
                                      github_repo_name="pg_auto_failover", changelog_project_name="pg_auto_failover",
                                      packaging_branch="all-pgautofailover")
    pg_auto_failover_enterprise = ProjectDetails(name="pg-auto-failover-enterprise", version_suffix="",
                                                 github_repo_name="citus-ha",
                                                 changelog_project_name="pg_auto_failover-enterprise",
                                                 packaging_branch="all-pgautofailover-enterprise")


@parameter_validation
def is_project_changelog_header(header: str):
    if not header:
        raise ValueError("header should be non-empty and should not be None")
    # an example matching string is "### citus-enterprise v10.1.0 (July 14, 2021) ###"
    if not re.match(r"^### \w+[-]?\w+\sv\d+\.\d+\.\d+\s\(\w+\s\d+,\s\d+\)\s###$", header):
        raise ValueError(
            f"changelog header is in invalid format. Actual:{header} Expected: ### citus v8.3.3 (March 23, 2021) ### ")


@dataclass
class PackagePropertiesParams:
    project: SupportedProject
    project_version: str
    fancy: bool
    fancy_version_number: int
    microsoft_email: str = ""
    name_surname: str = ""
    changelog_date: datetime = datetime.now()
    changelog_entry: str = ""

    @property
    def changelog_version_entry(self):
        return f"{self.project_version}-{self.fancy_version_number}"

    @property
    def spec_file_name(self) -> str:
        return spec_file_name(self.project.value.name)

    @property
    def pkgvars_template_file_name(self) -> str:
        return f"{self.project.value.name}-pkgvars.tmpl"

    @property
    def rpm_spec_template_file_name(self) -> str:
        return f"{self.project.value.name}.spec.tmpl"

    @property
    def version_number(self) -> str:
        fancy_suffix = f"-{self.fancy_version_number}" if self.fancy else ""
        return f"{self.project_version}{fancy_suffix}"

    @property
    def version_number_with_project_name(self) -> str:
        fancy_suffix = f"{self.fancy_version_number}" if self.fancy else "1"
        return f"{self.project_version}{self.project_name_suffix}-{fancy_suffix}"

    @property
    def rpm_version(self) -> str:
        return f"{self.project_version}{self.project_name_suffix}"

    @property
    def project_name_suffix(self) -> str:
        return (
            self.project.value.version_suffix if not self.project.value.version_suffix
            else f".{self.project.value.version_suffix}")

    @property
    def changelog_project_name(self) -> str:
        return self.project.value.name.replace("-", " ").replace("_", " ").title()

    @property
    def rpm_header(self):
        formatted_date = self.changelog_date.strftime("%a %b %d %Y")
        return f"* {formatted_date} - {self.name_surname} <{self.microsoft_email}> " \
               f"{self.version_number_with_project_name} "

    @property
    def debian_trailer(self):
        formatted_date = self.changelog_date.strftime("%a, %d %b %Y %H:%M:%S %z")
        return f" -- {self.name_surname} <{self.microsoft_email}>  {formatted_date}\n"


def get_enum_from_changelog_project_name(project_name) -> SupportedProject:
    for e in SupportedProject:
        if e.value.changelog_project_name == project_name:
            return e
    raise ValueError(f"{project_name} could not be found in supported project changelog names.")


def spec_file_name(project_name: str) -> str:
    return f"{project_name}.spec"


def get_last_changelog_content(all_changelog_content: str) -> str:
    second_changelog_index = find_nth_occurrence_position(all_changelog_content, "###", 3)
    changelogs = all_changelog_content[:second_changelog_index]
    lines = changelogs.splitlines()
    if len(lines) < 1:
        raise ValueError("At least one line should be in changelog")
    changelog_header = lines[0]
    if not changelog_header.startswith("###"):
        raise ValueError("Changelog header should start with '###'")
    return changelogs


def remove_paranthesis_from_string(param: str) -> str:
    return re.sub(r"[(\[].*?[)\]]", "", param)


# truncates # chars , get the version an put paranthesis around version number adds 'stable; urgency=low' at the end
# changelog_header=> ### citus v8.3.3 (March 23, 2021) ###
# debian header =>   citus (10.0.3.citus-1) stable; urgency=low
@validate_parameters
def debian_changelog_header(supported_project: SupportedProject, project_version: str, fancy: bool,
                            fancy_version_number: int) -> str:
    package_properties_params = PackagePropertiesParams(project=supported_project,
                                                        project_version=project_version,
                                                        fancy=fancy, fancy_version_number=fancy_version_number)

    version_on_changelog = package_properties_params.version_number_with_project_name

    return f"{supported_project.value.name} ({version_on_changelog}) stable; urgency=low"


def get_debian_latest_changelog(package_properties_params: PackagePropertiesParams) -> str:
    lines = []
    lines.append(
        debian_changelog_header(package_properties_params.project,
                                package_properties_params.project_version,
                                package_properties_params.fancy,
                                package_properties_params.fancy_version_number))
    lines.append(f"  * {get_changelog_entry(package_properties_params)}")
    lines.append(package_properties_params.debian_trailer)
    debian_latest_changelog = ""
    for i, line in enumerate(lines):
        append_line = line if i in (0, len(lines) - 1) else '' + line
        debian_latest_changelog = debian_latest_changelog + append_line + "\n\n"
    return debian_latest_changelog[:-1]


def prepend_latest_changelog_into_debian_changelog(package_properties_params: PackagePropertiesParams,
                                                   changelog_file_path: str) -> None:
    debian_latest_changelog = get_debian_latest_changelog(package_properties_params)
    with open(changelog_file_path, mode="r+", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        if not (package_properties_params.changelog_version_entry in reader.readline()):
            reader.seek(0, 0)
            old_changelog = reader.read()
            changelog = f"{debian_latest_changelog}{old_changelog}"
            reader.seek(0, 0)
            reader.write(changelog)
        else:
            raise ValueError("Already version in the debian changelog")


@validate_parameters
def update_pkgvars(package_properties_params: PackagePropertiesParams, templates_path: str, pkgvars_path: str) -> None:
    env = get_template_environment(templates_path)

    version_str = package_properties_params.version_number_with_project_name

    template = env.get_template(package_properties_params.pkgvars_template_file_name)

    pkgvars_content = f"{template.render(version=version_str)}\n"
    with open(f'{pkgvars_path}/pkgvars', "w", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        writer.write(pkgvars_content)


def rpm_changelog_history(spec_file_path: str) -> str:
    with open(spec_file_path, "r", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as reader:
        spec_content = reader.read()
        changelog_index = spec_content.find("%changelog")
        changelog_content = spec_content[changelog_index + len("%changelog") + 1:]

    return changelog_content


def get_changelog_entry(package_properties_params: PackagePropertiesParams):
    default_changelog_entry = f"Official {package_properties_params.project_version} release of " \
                              f"{package_properties_params.changelog_project_name}"
    return (
        package_properties_params.changelog_entry if package_properties_params.changelog_entry
        else default_changelog_entry)


def get_rpm_changelog(package_properties_params: PackagePropertiesParams) -> str:
    changelog = (package_properties_params.changelog_entry if package_properties_params.changelog_entry
                 else get_changelog_entry(package_properties_params))
    header = package_properties_params.rpm_header
    rpm_changelog = f"{header.strip()}\n- {changelog}"

    return rpm_changelog


def update_rpm_spec(package_properties_params: PackagePropertiesParams, spec_full_path: str,
                    templates_path: str) -> None:
    env = get_template_environment(templates_path)

    rpm_version = package_properties_params.rpm_version
    template = env.get_template(package_properties_params.rpm_spec_template_file_name)

    history_lines = rpm_changelog_history(spec_full_path).splitlines()

    if len(history_lines) > 0 and package_properties_params.version_number_with_project_name in history_lines[0]:
        raise ValueError(f"{package_properties_params.project_version} already exists in rpm spec file")

    latest_changelog = get_rpm_changelog(package_properties_params)
    changelog = f"{latest_changelog}\n\n{rpm_changelog_history(spec_full_path)}"

    content = template.render(version=package_properties_params.project_version, rpm_version=rpm_version,
                              project_name=package_properties_params.project.value.name,
                              fancy_version_no=package_properties_params.fancy_version_number, changelog=changelog)
    with open(spec_full_path, "w+", encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
              errors=DEFAULT_UNICODE_ERROR_HANDLER) as writer:
        writer.write(content)


def validate_package_properties_params_for_update_all_changes(package_props: PackagePropertiesParams):
    if package_props.fancy_version_number < 0:
        raise ValueError("Fancy version number should not be negative")
    if not string_utils.is_email(package_props.microsoft_email):
        raise ValueError("Microsoft email should be in email format")
    if not package_props.name_surname:
        raise ValueError("Name Surname should not be empty")
    is_version(package_props.project_version)


@validate_parameters
def update_all_changes(package_properties_params: PackagePropertiesParams,
                       packaging_path: str):
    validate_package_properties_params_for_update_all_changes(package_properties_params)
    templates_path = f"{BASE_PATH}/templates"
    update_pkgvars(package_properties_params, templates_path,
                   f"{packaging_path}")
    prepend_latest_changelog_into_debian_changelog(package_properties_params, f"{packaging_path}/debian/changelog")
    spec_full_path = f"{packaging_path}/{package_properties_params.spec_file_name}"
    update_rpm_spec(package_properties_params, spec_full_path, templates_path)


CHECKOUT_DIR = "update_properties_temp"
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token', required=True)
    parser.add_argument('--prj_name', choices=[r.name for r in SupportedProject])
    parser.add_argument('--tag_name', required=True)
    parser.add_argument('--fancy_ver_no', type=int, choices=range(1, 10), default=1)
    parser.add_argument('--email', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--date')
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument('--exec_path')
    parser.add_argument('--is_test', action="store_true")
    parser.add_argument('--changelog_entry')
    arguments = parser.parse_args()

    prj_ver = get_project_version_from_tag_name(arguments.tag_name)

    project = SupportedProject[arguments.prj_name]
    if arguments.pipeline:
        if not arguments.exec_path:
            raise ValueError("exec_path should be defined")
        execution_path = arguments.exec_path
        os.chdir(execution_path)

    else:
        execution_path = f"{os.getcwd()}/{CHECKOUT_DIR}"
        initialize_env(execution_path, PROJECT_NAME, execution_path)
        os.chdir(execution_path)
        run(f"git checkout {project.value.packaging_branch}")

    pr_branch = f"{project.value.packaging_branch}-{prj_ver}-{uuid.uuid4()}"
    run(f"git checkout -b {pr_branch}")
    exec_date = datetime.strptime(arguments.date,
                                  '%Y.%m.%d %H:%M') if arguments.date else datetime.now().astimezone()
    is_tag(arguments.tag_name)

    fancy = arguments.fancy_ver_no > 1

    package_properties = PackagePropertiesParams(project=project,
                                                 project_version=prj_ver, fancy=fancy,
                                                 fancy_version_number=arguments.fancy_ver_no,
                                                 name_surname=arguments.name, microsoft_email=arguments.email,
                                                 changelog_date=exec_date, changelog_entry=arguments.changelog_entry)
    update_all_changes(package_properties, execution_path)

    commit_message = f"Bump to {arguments.prj_name} {prj_ver}"
    run(f'git commit -am "{commit_message}"')

    if not arguments.is_test:
        run(f'git push --set-upstream origin {pr_branch}')
        create_pr(arguments.gh_token, pr_branch, commit_message, REPO_OWNER, PROJECT_NAME,
                  project.value.packaging_branch)
    if not arguments.pipeline and not arguments.is_test:
        remove_cloned_code(execution_path)
