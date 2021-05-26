import argparse
import re
from datetime import date, datetime

import pathlib2
import string_utils
from github import Github
from jinja2 import Environment, FileSystemLoader
from parameters_validation import (no_whitespaces, non_blank, non_empty, non_negative, validate_parameters,
                                   parameter_validation)
from dataclasses import dataclass

from .common_tool_methods import (find_nth_matching_line_and_line_number, find_nth_occurrence_position,
                                  get_project_version_from_tag_name)

BASE_PATH = pathlib2.Path(__file__).parent.absolute()

project_name_suffix_dict = {"citus": "citus", "citus-enterprise": "citus",
                            "pg-auto-failover": "", "pg-auto-failover-enterprise": "", "pg-cron": "", "pg-xn": ""}


@parameter_validation
def is_version(version: str):
    if not version:
        raise ValueError("version should be non-empty and should not be None")
    if not re.match(r"\d+\.\d+\.\d+$", version):
        raise ValueError(
            "version should include 3 levels of versions consists of numbers  separated with dots. e.g: 10.0.1")


@parameter_validation
def is_tag(tag: str):
    if not tag:
        raise ValueError("tag  should be non-empty and should not be None")
    if not re.match(r"v\d+\.\d+\.\d+$", tag):
        raise ValueError(
            "tag  should start with v and should include 3 levels of versions consists of numbers " +
            "separated with dots. e.g: v10.0.1")


@parameter_validation
def is_email(email: str):
    if not string_utils.is_email(email):
        raise ValueError("Parameter is not in email format")


@parameter_validation
def is_project_changelog_header(header: str):
    if not header:
        raise ValueError("header should be non-empty and should not be None")
    if not re.match(r"^### \w+\sv\d+\.\d+\.\d+\s\(\w+\s\d+,\s\d+\)\s###$", header):
        raise ValueError(
            f"changelog header is in invalid format. Actual:{header} Expected: ### citus v8.3.3 (March 23, 2021) ### ")


@dataclass
class PackagePropertiesParams:
    project_name: str
    project_version: str
    fancy: bool
    fancy_version_number: int
    microsoft_email: str = ""
    name_surname: str = ""
    latest_changelog: str = ""
    changelog_date: datetime = datetime.now()

    def spec_file_name(self) -> str:
        return spec_file_name(self.project_name)

    def version_number(self) -> str:
        fancy_suffix = f"-{self.fancy_version_number}" if self.fancy else ""
        return f"{self.project_version}{fancy_suffix}"

    def rpm_version(self) -> str:
        return f"{self.project_version}.{self.project_name}"

    def version_number_with_project_name(self) -> str:
        fancy_suffix = f"-{self.fancy_version_number}" if self.fancy else ""
        return f"{self.project_version}.{self.project_name_suffix()}{fancy_suffix}"

    def project_name_suffix(self) -> str:
        return project_name_suffix_dict[self.project_name] if self.project_name in project_name_suffix_dict else ""

    def rpm_header(self):
        formatted_date = self.changelog_date.strftime("%a %b %d %Y")
        return f"* {formatted_date} - {self.name_surname} <{self.microsoft_email}> " \
               f"{self.version_number_with_project_name()} "

    def debian_trailer(self):
        formatted_date = self.changelog_date.strftime("%a, %d %b %Y %H:%M:%S %z ")
        return f" -- {self.name_surname} <{self.microsoft_email}>  {formatted_date} \n "


def spec_file_name(project_name: str) -> str:
    return f"{project_name}.spec"


def get_template_environment(template_dir: str) -> Environment:
    file_loader = FileSystemLoader(template_dir)
    env = Environment(loader=file_loader)
    return env


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


def get_last_changelog_content_from_debian(all_changelog_content: str) -> str:
    second_changelog_index, second_changelog_line = find_nth_matching_line_and_line_number(all_changelog_content,
                                                                                           "^[a-zA-Z]", 2)
    lines = all_changelog_content.splitlines()
    changelogs = "\n".join(lines[:second_changelog_index - 1]) + "\n"
    if len(lines) < 1:
        raise ValueError("At least one line should be in changelog")
    return changelogs


def remove_parentheses_from_string(param: str) -> str:
    return re.sub(r"[(\[].*?[)\]]", "", param)


def changelog_for_tag(github_token: str, project_name: str, tag_name: str) -> str:
    g = Github(github_token)
    repo = g.get_repo(f"citusdata/{project_name}")
    all_changelog_content = repo.get_contents("CHANGELOG.md", ref=tag_name)
    last_changelog_content = get_last_changelog_content(all_changelog_content.decoded_content.decode())
    return last_changelog_content


# truncates # chars , get the version an put parentheses around version number adds 'stable; urgency=low' at the end
# changelog_header=> ### citus v8.3.3 (March 23, 2021) ###
# debian header =>   citus (10.0.3.citus-1) stable; urgency=low
@validate_parameters
def debian_changelog_header(changelog_header: is_project_changelog_header(str), fancy: bool,
                            fancy_version_number: int) -> str:
    hash_removed_string = changelog_header.lstrip("### ").rstrip(" ###")
    parentheses_removed_string = remove_parentheses_from_string(hash_removed_string)
    words = parentheses_removed_string.strip().split(" ")
    if len(words) != 2:
        raise ValueError("Two words should be included in striped version header")
    project_name = words[0]
    project_version = words[1].lstrip("v")

    package_properties_params = PackagePropertiesParams(project_name=project_name, project_version=project_version,
                                                        fancy=fancy, fancy_version_number=fancy_version_number)

    version_on_changelog = package_properties_params.version_number_with_project_name()

    return f"{project_name} ({version_on_changelog}) stable; urgency=low"


def convert_citus_changelog_into_debian_changelog(package_properties_params: PackagePropertiesParams) -> str:
    lines = package_properties_params.latest_changelog.splitlines()
    lines[0] = debian_changelog_header(lines[0], package_properties_params.fancy,
                                       package_properties_params.fancy_version_number)
    lines.append(package_properties_params.debian_trailer())
    debian_latest_changelog = ""
    for i in range(len(lines)):
        append_line = lines[i] if i == 0 or i == len(lines) - 1 else '  ' + lines[i]
        debian_latest_changelog = debian_latest_changelog + append_line + "\n"
    return debian_latest_changelog


def prepend_latest_changelog_into_debian_changelog(package_properties_params: PackagePropertiesParams,
                                                   changelog_file_path: str) -> None:
    debian_latest_changelog = convert_citus_changelog_into_debian_changelog(package_properties_params)
    with open(changelog_file_path, "r+") as reader:
        if not (f"({package_properties_params.project_version}" in reader.readline()):
            reader.seek(0, 0)
            old_changelog = reader.read()
            changelog = f"{debian_latest_changelog}{old_changelog}"
            reader.seek(0, 0)
            reader.write(changelog)
        else:
            raise ValueError("Already version in the debian changelog")


@validate_parameters
def update_pkgvars(project_name: str, version: is_version(non_empty(no_whitespaces(non_blank(str)))), fancy: bool,
                   fancy_version_number: non_negative(int), templates_path: str, pkgvars_path: str) -> None:
    env = get_template_environment(templates_path)

    package_properties_params = PackagePropertiesParams(project_name=project_name, project_version=version, fancy=fancy,
                                                        fancy_version_number=fancy_version_number)

    version_str = package_properties_params.version_number_with_project_name()

    template = env.get_template('pkgvars.tmpl')

    pkgvars_content = f"{template.render(version=version_str)}\n"
    with open(f'{pkgvars_path}/pkgvars', "w") as writer:
        writer.write(pkgvars_content)


def rpm_changelog_history(spec_file_path: str) -> str:
    with open(spec_file_path, "r") as reader:
        spec_content = reader.read()
        changelog_index = spec_content.find("%changelog")
        changelog_content = spec_content[changelog_index + len("%changelog") + 1:]

    return changelog_content


def convert_citus_changelog_into_rpm_changelog(package_properties_params: PackagePropertiesParams) -> str:
    header = package_properties_params.rpm_header()
    rpm_changelog = f"{header.strip()}\n- Official {package_properties_params.project_version} release of " \
                    f"{package_properties_params.project_name.capitalize()}"

    return rpm_changelog


def update_rpm_spec(package_properties_params: PackagePropertiesParams, spec_full_path: str,
                    templates_path: str) -> None:
    env = get_template_environment(templates_path)

    rpm_version = package_properties_params.rpm_version()
    template = env.get_template('project.spec.tmpl')

    history_lines = rpm_changelog_history(spec_full_path).splitlines()

    if len(history_lines) > 0 and package_properties_params.project_version in history_lines[1]:
        raise ValueError(f"{package_properties_params.project_version} already exists in rpm spec file")

    latest_changelog = convert_citus_changelog_into_rpm_changelog(package_properties_params)
    changelog = f"{latest_changelog}\n\n{rpm_changelog_history(spec_full_path)}"
    content = template.render(version=package_properties_params.project_version, rpm_version=rpm_version,
                              project_name=package_properties_params.project_name,
                              fancy_version_no=package_properties_params.fancy_version_number, changelog=changelog)
    with open(spec_full_path, "w+") as writer:
        writer.write(content)


def validate_package_properties_params_for_update_all_changes(package_props: PackagePropertiesParams):
    if not package_props.project_name:
        raise ValueError("Project Name should not be empty")
    if package_props.fancy_version_number < 0:
        raise ValueError("Fancy version number should not be negative")
    if not string_utils.is_email(package_props.microsoft_email):
        raise ValueError("Microsoft email should be in email format")
    if not package_props.name_surname:
        raise ValueError("Name Surname should not be empty")
    is_version(package_props.project_version)


@validate_parameters
def update_all_changes(github_token: non_empty(non_blank(str)), package_properties_params: PackagePropertiesParams,
                       tag_name: is_tag(str),
                       packaging_path: str):
    validate_package_properties_params_for_update_all_changes(package_properties_params)
    templates_path = f"{BASE_PATH}/templates"
    update_pkgvars(package_properties_params.project_name, package_properties_params.project_version,
                   package_properties_params.fancy, package_properties_params.fancy_version_number, templates_path,
                   f"{packaging_path}")
    latest_changelog = changelog_for_tag(github_token, package_properties_params.project_name, tag_name)
    package_properties_params.latest_changelog = latest_changelog

    prepend_latest_changelog_into_debian_changelog(package_properties_params, f"{packaging_path}/debian/changelog")
    spec_full_path = f"{packaging_path}/{package_properties_params.spec_file_name()}"
    update_rpm_spec(package_properties_params, spec_full_path, templates_path)


# update_all_changes("93647419346e194ae3094598139d68ebf2263ee0", "citus", "10.0.3", "v10.0.3", True, 1,
#                    "gindibay@microsoft.com", "Gurkan Indibay")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token')
    parser.add_argument('--prj_name')
    parser.add_argument('--tag_name')
    parser.add_argument('--fancy')
    parser.add_argument('--fancy_ver_no')
    parser.add_argument('--email')
    parser.add_argument('--name')
    parser.add_argument('--date', nargs='?', default=datetime.now())
    parser.add_argument('--exec_path')
    arguments = parser.parse_args()

    if not string_utils.is_integer(arguments.fancy_ver_no):
        raise ValueError(f"fancy_ver_no is expected to be numeric actual value {arguments.fancy_ver_no}")

    exec_date = datetime.strptime(arguments.date, '%Y.%m.%d %H:%M:%S %z')
    is_tag(arguments.tag_name)
    prj_ver = get_project_version_from_tag_name(arguments.tag_name)

    package_properties = PackagePropertiesParams(project_name=arguments.prj_name,
                                                 project_version=prj_ver, fancy=arguments.fancy,
                                                 fancy_version_number=int(arguments.fancy_ver_no),
                                                 name_surname=arguments.name, microsoft_email=arguments.email,
                                                 changelog_date=exec_date)

    update_all_changes(arguments.gh_token, package_properties, arguments.tag_name, arguments.exec_path)
