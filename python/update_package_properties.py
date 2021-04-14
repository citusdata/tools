import argparse
from datetime import date

import pathlib2
from github import Github
from parameters_validation import no_whitespaces, non_blank, non_empty, non_negative, validate_parameters

from .common_tool_methods import *

BASE_PATH = pathlib2.Path(__file__).parent.absolute()


class ChangelogParams:
    __latest_changelog: str = ""
    __project_version: str = ""
    __project_name: str = ""
    __fancy: bool = False
    __fancy_version_number: int
    __microsoft_email: str = ""
    __name_surname: str = ""
    __changelog_date: datetime = datetime.now()

    def get_latest_changelog(self) -> str:
        return self.__latest_changelog

    def set_latest_changelog(self, param: str):
        self.__latest_changelog = param
        return self

    def get_project_name(self) -> str:
        return self.__project_name

    def set_project_name(self, param: non_empty(non_blank(str))):
        self.__project_name = param
        return self

    def get_project_version(self) -> str:
        return self.__project_version

    def set_project_version(self, param: is_version(str)):
        self.__project_version = param
        return self

    def get_fancy(self) -> bool:
        return self.__fancy

    def set_fancy(self, param: bool):
        self.__fancy = param
        return self

    def get_fancy_version_number(self) -> int:
        return self.__fancy_version_number

    def set_fancy_version_number(self, param: non_negative(int)):
        self.__fancy_version_number = param
        return self

    def get_microsoft_email(self) -> str:
        return self.__microsoft_email

    def set_microsoft_email(self, param: is_email(str)):
        self.__microsoft_email = param
        return self

    def get_name_surname(self) -> str:
        return self.__name_surname

    def set_name_surname(self, param: non_empty(non_blank(str))):
        self.__name_surname = param
        return self

    def get_changelog_date(self) -> datetime:
        return self.__changelog_date

    def set_changelog_date(self, param: datetime):
        self.__changelog_date = param
        return self


def get_rpm_version(project_name: str, version: str) -> str:
    return f"{version}.{project_name}"


def get_last_changelog_content(all_changelog_content: str) -> str:
    second_changelog_index = find_nth_overlapping(all_changelog_content, "###", 3)
    changelogs = all_changelog_content[:second_changelog_index]
    lines = changelogs.splitlines()
    if len(lines) < 1:
        raise ValueError("At least one line should be in changelog")
    changelog_header = lines[0]
    if not changelog_header.startswith("###"):
        raise ValueError("Changelog header should start with '###'")
    return changelogs


def get_last_changelog_content_from_debian(all_changelog_content: str) -> str:
    second_changelog_index = find_nth_overlapping_line_by_regex(all_changelog_content, "^[a-zA-Z]", 2)
    lines = all_changelog_content.splitlines()
    changelogs = "\n".join(lines[:second_changelog_index - 1]) + "\n"
    if len(lines) < 1:
        raise ValueError("At least one line should be in changelog")
    return changelogs


@parameter_validation
def is_project_changelog_header(header: str):
    if header is None or not header:
        raise ValueError("header should be non-empty and should not be None")
    if not re.match(r"^### \w+\sv\d+\.\d+\.\d+\s\(\w+\s\d+,\s\d+\)\s###$", header):
        raise ValueError(
            f"changelog header is in invalid format. Actual:{header} Expected: ### citus v8.3.3 (March 23, 2021) ### ")


def get_changelog_for_tag(github_token: str, project_name: str, tag_name: str) -> str:
    g = Github(github_token)
    repo = g.get_repo(f"citusdata/{project_name}")
    all_changelog_content = repo.get_contents("CHANGELOG.md", ref=tag_name)
    last_changelog_content = get_last_changelog_content(all_changelog_content.decoded_content.decode())
    return last_changelog_content


# truncates # chars , get the version an put parentheses around version number adds 'stable; urgency=low' at the end
# changelog_header=> ### citus v8.3.3 (March 23, 2021) ###
# debian header =>   citus (10.0.3.citus-1) stable; urgency=low
@validate_parameters
def get_debian_changelog_header(changelog_header: is_project_changelog_header(str), fancy: bool,
                                fancy_version_number: int) -> str:
    hash_removed_string = changelog_header.lstrip("### ").rstrip(" ###")
    parentheses_removed_string = remove_string_inside_parentheses(hash_removed_string)
    words = parentheses_removed_string.strip().split(" ")
    if len(words) != 2:
        raise ValueError("Two words should be included in striped version header")
    project_name = words[0]
    project_version = words[1].lstrip("v")
    version_on_changelog = get_version_number_with_project_name(project_name, project_version, fancy,
                                                                fancy_version_number)

    return f"{project_name} ({version_on_changelog}) stable; urgency=low"


def convert_citus_changelog_into_debian_changelog(changelog_params: ChangelogParams) -> str:
    lines = changelog_params.get_latest_changelog().splitlines()
    lines[0] = get_debian_changelog_header(lines[0], changelog_params.get_fancy(),
                                           changelog_params.get_fancy_version_number())
    lines.append(get_debian_trailer(changelog_params.get_microsoft_email(), changelog_params.get_name_surname(),
                                    changelog_params.get_changelog_date()))
    debian_latest_changelog = ""
    for i in range(len(lines)):
        append_line = lines[i] if i == 0 or i == len(lines) - 1 else '  ' + lines[i]
        debian_latest_changelog = debian_latest_changelog + append_line + "\n"
    return debian_latest_changelog


def prepend_latest_changelog_into_debian_changelog(changelog_param: ChangelogParams, changelog_file_path: str) -> None:
    debian_latest_changelog = convert_citus_changelog_into_debian_changelog(changelog_param)
    with open(changelog_file_path, "r+") as reader:
        if not (f"({changelog_param.get_project_version()}" in reader.readline()):
            reader.seek(0, 0)
            old_changelog = reader.read()
            changelog = f"{debian_latest_changelog}{old_changelog}"
            reader.seek(0, 0)
            reader.write(changelog)
        else:
            raise ValueError("Already version in the debian changelog")


@validate_parameters
def update_pkgvars(project_name: str, version: is_version(non_empty(no_whitespaces(non_blank(str)))), fancy: bool,
                   fancy_release_count: non_negative(int), templates_path: str, pkgvars_path: str) -> None:
    env = get_template_environment(templates_path)

    version_str = get_version_number_with_project_name(project_name, version, fancy, fancy_release_count)

    template = env.get_template('pkgvars.tmpl')

    pkgvars_content = f"{template.render(version=version_str)}\n"
    with open(f'{pkgvars_path}/pkgvars', "w") as writer:
        writer.write(pkgvars_content)


def get_rpm_changelog_history(spec_file_path: str) -> str:
    with open(spec_file_path, "r") as reader:
        spec_content = reader.read()
        changelog_index = spec_content.find("%changelog")
        changelog_content = spec_content[changelog_index + len("%changelog") + 1:]

    return changelog_content


def get_rpm_header(changelog_params: ChangelogParams):
    formatted_date = changelog_params.get_changelog_date().strftime("%a %b %d %Y")
    return f"* {formatted_date} - {changelog_params.get_name_surname()} <{changelog_params.get_microsoft_email()}> " \
           f"{get_version_number_with_project_name(changelog_params.get_project_name(), changelog_params.get_project_version(), changelog_params.get_fancy(), changelog_params.get_fancy_version_number())} "


def get_debian_trailer(microsoft_email: str, name_surname: str, changelog_date: date):
    formatted_date = changelog_date.strftime("%a, %d %b %Y %H:%M:%S %z ")
    return f" -- {name_surname} <{microsoft_email}>  {formatted_date} \n "


def convert_citus_changelog_into_rpm_changelog(changelog_params: ChangelogParams) -> str:
    header = get_rpm_header(changelog_params)
    rpm_changelog = f"{header.strip()}\n- Official {changelog_params.get_project_version()} release of {changelog_params.get_project_name().capitalize()}"

    return rpm_changelog


def update_rpm_spec(changelog_param: ChangelogParams, spec_file_name: str,
                    templates_path: str) -> None:
    env = get_template_environment(templates_path)

    rpm_version = get_rpm_version(changelog_param.get_project_name(), changelog_param.get_project_version())
    template = env.get_template('project.spec.tmpl')
    rpm_changelog_history = get_rpm_changelog_history(spec_file_name)

    history_lines = rpm_changelog_history.splitlines()

    if len(history_lines) > 0 and changelog_param.get_project_version() in history_lines[1]:
        raise ValueError(f"{changelog_param.get_project_version()} already exists in rpm spec file")

    latest_changelog = convert_citus_changelog_into_rpm_changelog(changelog_param)
    changelog = f"{latest_changelog}\n\n{rpm_changelog_history}"
    content = template.render(version=changelog_param.get_project_version(), rpm_version=rpm_version,
                              project_name=changelog_param.get_project_name(),
                              fancy_version_no=changelog_param.get_fancy_version_number(), changelog=changelog)
    with open(spec_file_name, "w+") as writer:
        writer.write(content)


@validate_parameters
def update_all_changes(github_token: non_empty(non_blank(str)), project_name: non_empty(str),
                       project_version: is_version(str),
                       tag_name: is_tag(str), fancy: bool, fancy_version_number: non_negative(int),
                       microsoft_email: is_email(str),
                       name_surname: non_empty(non_blank(str)), release_date: datetime, packaging_path: str):
    templates_path = f"{BASE_PATH}/templates"
    update_pkgvars(project_name, project_version, fancy, fancy_version_number, templates_path, f"{packaging_path}")
    latest_changelog = get_changelog_for_tag(github_token, project_name, tag_name)
    changelog_param = ChangelogParams()
    changelog_param.set_project_version(project_version).set_project_name(project_name).set_microsoft_email(
        microsoft_email).set_name_surname(name_surname).set_fancy_version_number(
        fancy_version_number).set_changelog_date(release_date).set_fancy(fancy).set_latest_changelog(latest_changelog)

    prepend_latest_changelog_into_debian_changelog(changelog_param, f"{packaging_path}/debian/changelog")
    spec_file_name = f"{packaging_path}/{get_spec_file_name(project_name)}"
    update_rpm_spec(changelog_param, spec_file_name, templates_path)


# update_all_changes("93647419346e194ae3094598139d68ebf2263ee0", "citus", "10.0.3", "v10.0.3", True, 1,
#                    "gindibay@microsoft.com", "Gurkan Indibay")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--gh_token')
    parser.add_argument('--prj_name')
    parser.add_argument('--prj_ver')
    parser.add_argument('--tag_name')
    parser.add_argument('--fancy')
    parser.add_argument('--fancy_ver_no')
    parser.add_argument('--email')
    parser.add_argument('--name')
    parser.add_argument('--date')
    parser.add_argument('--exec_path')
    args = parser.parse_args()

    if not string_utils.is_integer(args.fancy_ver_no):
        raise ValueError(f"fancy_ver_no is expected to be numeric actual value {args.fancy_ver_no}")

    exec_date = datetime.strptime(args.date, '%Y.%m.%d %H:%M:%S %z')

    update_all_changes(args.gh_token, args.prj_name, args.prj_ver, args.tag_name, args.fancy,
                       int(args.fancy_ver_no),
                       args.email, args.name, exec_date, args.exec_path)
