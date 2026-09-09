import pathlib2
import pytest

from ..common_tool_methods import (
    DEFAULT_ENCODING_FOR_FILE_HANDLING,
    DEFAULT_UNICODE_ERROR_HANDLER,
)
from ..packaging_warning_handler import (
    parse_ignore_lists,
    PackageType,
    filter_warning_lines,
    get_warnings_to_be_raised,
    get_error_message,
    validate_output,
)

TEST_BASE_PATH = pathlib2.Path(__file__).parent
IGNORE_FILE = f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml"
DIVERSION_WARNING = (
    "dpkg-shlibdeps: warning: diversions involved - output may be incorrect"
)
DIVERSION_FROM = " diversion by libc6 from: /lib/ld-linux-aarch64.so.1"
DIVERSION_TO = " diversion by libc6 to: /lib/ld-linux-aarch64.so.1.usr-is-merged"
KNOWN_DIVERSION = [DIVERSION_WARNING, DIVERSION_FROM, DIVERSION_WARNING, DIVERSION_TO]


def test_parse_ignore_lists():
    base_ignore_list, debian_ignore_list = parse_ignore_lists(
        f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
        PackageType.deb,
    )
    assert len(base_ignore_list) == 8 and len(debian_ignore_list) == 2

    base_ignore_list, rpm_ignore_list = parse_ignore_lists(
        f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
        PackageType.deb,
    )
    assert len(base_ignore_list) == 8 and len(rpm_ignore_list) == 2


def test_deb_filter_warning_lines():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        lines = reader.read().splitlines()
        base_warning_lines, package_specific_warning_lines = filter_warning_lines(
            lines, PackageType.deb
        )
        assert (
            len(base_warning_lines) == 11 and len(package_specific_warning_lines) == 7
        )


def test_rpm_filter_warning_lines():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_rpm.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        lines = reader.read().splitlines()
        base_warning_lines, package_specific_warning_lines = filter_warning_lines(
            lines, PackageType.rpm
        )
        assert (
            len(base_warning_lines) == 10 and len(package_specific_warning_lines) == 1
        )


def test_get_base_warnings_to_be_raised():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        lines = reader.read().splitlines()
        base_warning_lines, _ = filter_warning_lines(lines, PackageType.deb)
        base_ignore_list, _ = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
            PackageType.deb,
        )
        base_warnings_to_be_raised = get_warnings_to_be_raised(
            base_ignore_list, base_warning_lines
        )
        assert len(base_warnings_to_be_raised) == 1


def test_get_debian_warnings_to_be_raised():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        lines = reader.read().splitlines()
        _, package_specific_warning_lines = filter_warning_lines(lines, PackageType.deb)
        _, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
            PackageType.deb,
        )
        debian_warnings_to_be_raised = get_warnings_to_be_raised(
            debian_ignore_list, package_specific_warning_lines
        )
        assert len(debian_warnings_to_be_raised) == 2


def test_get_error_message():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(
            lines, PackageType.deb
        )
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
            PackageType.deb,
        )
        base_warnings_to_be_raised = get_warnings_to_be_raised(
            base_ignore_list, base_warning_lines
        )
        debian_warnings_to_be_raised = get_warnings_to_be_raised(
            debian_ignore_list, debian_warning_lines
        )
        error_message = get_error_message(
            base_warnings_to_be_raised, debian_warnings_to_be_raised, PackageType.deb
        )
        assert (
            error_message
            == "Warning lines:\nWarning: Unhandled\nDebian Warning lines:\n"
            "citus-enterprise100_11.x86_64: W: invalid-date-format\n"
            "citus-enterprise100_11.x86_64: E: zero-length /usr/pgsql-/usr/lib/share/extension/\n"
        )


def test_get_error_message_empty_package_specific_errors():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb_only_base.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        lines = reader.read().splitlines()
        base_warning_lines, debian_warning_lines = filter_warning_lines(
            lines, PackageType.deb
        )
        base_ignore_list, debian_ignore_list = parse_ignore_lists(
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
            PackageType.deb,
        )
        base_warnings_to_be_raised = get_warnings_to_be_raised(
            base_ignore_list, base_warning_lines
        )
        debian_warnings_to_be_raised = get_warnings_to_be_raised(
            debian_ignore_list, debian_warning_lines
        )
        error_message = get_error_message(
            base_warnings_to_be_raised, debian_warnings_to_be_raised, PackageType.deb
        )
        assert error_message == "Warning lines:\nWarning: Unhandled\n"


def test_validate_output_deb():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_deb.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        output = reader.read()
        with pytest.raises(SystemExit):
            validate_output(
                output,
                f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
                PackageType.deb,
            )


def test_validate_output_rpm():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_rpm.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        output = reader.read()
        with pytest.raises(SystemExit):
            validate_output(
                output,
                f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore_without_rpm_rules.yml",
                PackageType.rpm,
            )


def test_validate_output_rpm_success():
    with open(
        f"{TEST_BASE_PATH}/files/packaging_warning/sample_warning_build_output_rpm_success.txt",
        "r",
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    ) as reader:
        output = reader.read()
        validate_output(
            output,
            f"{TEST_BASE_PATH}/files/packaging_warning/packaging_ignore.yml",
            PackageType.rpm,
        )


@pytest.mark.parametrize(
    "lines",
    [
        pytest.param(KNOWN_DIVERSION, id="serial"),
        pytest.param(KNOWN_DIVERSION * 3, id="repeated"),
        pytest.param(
            [DIVERSION_WARNING, DIVERSION_WARNING, DIVERSION_TO, DIVERSION_FROM],
            id="interleaved",
        ),
        pytest.param(
            KNOWN_DIVERSION + ["   dh_gencontrol -a"] + KNOWN_DIVERSION,
            id="separate-complete-blocks",
        ),
    ],
)
def test_known_arm64_diversion(lines):
    original_lines = lines.copy()
    assert filter_warning_lines(lines, PackageType.deb) == ([], [])
    validate_output("\n".join(lines), IGNORE_FILE, PackageType.deb)
    assert lines == original_lines


def test_known_arm64_diversion_topn_noble_output():
    # Original topn/Noble output, including warning/warning/to/from interleaving.
    output = (
        TEST_BASE_PATH
        / "files/packaging_warning/sample_warning_build_output_deb_arm64_diversions.txt"
    ).read_text(
        encoding=DEFAULT_ENCODING_FOR_FILE_HANDLING,
        errors=DEFAULT_UNICODE_ERROR_HANDLER,
    )
    assert filter_warning_lines(output.splitlines(), PackageType.deb) == ([], [])
    validate_output(output, IGNORE_FILE, PackageType.deb)


@pytest.mark.parametrize(
    "source,target",
    [
        pytest.param(
            DIVERSION_FROM.replace("libc6", "other"),
            DIVERSION_TO.replace("libc6", "other"),
            id="unknown-owner",
        ),
        pytest.param(
            DIVERSION_FROM.replace("libc6", "libc6:arm64"),
            DIVERSION_TO,
            id="different-owner-spelling",
        ),
        pytest.param(
            DIVERSION_FROM.replace("diversion by libc6", "local diversion"),
            DIVERSION_TO.replace("diversion by libc6", "local diversion"),
            id="local-diversion",
        ),
        pytest.param(
            DIVERSION_FROM.replace("aarch64", "x86-64"),
            DIVERSION_TO.replace("aarch64", "x86-64"),
            id="other-architecture",
        ),
        pytest.param(
            DIVERSION_FROM.replace("/lib/", "/usr/lib/"),
            DIVERSION_TO,
            id="other-source-path",
        ),
        pytest.param(
            DIVERSION_FROM,
            DIVERSION_TO.replace(".usr-is-merged", ".distrib"),
            id="other-target-path",
        ),
        pytest.param("", DIVERSION_TO, id="missing-source"),
        pytest.param(DIVERSION_FROM, "", id="missing-target"),
        pytest.param(DIVERSION_FROM, DIVERSION_TO + ".extra", id="target-suffix"),
        pytest.param(DIVERSION_FROM + " extra", DIVERSION_TO, id="extra-text"),
        pytest.param(DIVERSION_FROM.lstrip(), DIVERSION_TO, id="missing-indent"),
        pytest.param("\t" + DIVERSION_FROM, DIVERSION_TO, id="extra-indent"),
        pytest.param(DIVERSION_FROM, DIVERSION_TO + " ", id="trailing-space"),
        pytest.param(
            DIVERSION_FROM.replace("from:", "from"),
            DIVERSION_TO,
            id="malformed-record",
        ),
        pytest.param(
            DIVERSION_FROM,
            DIVERSION_TO.replace("to: /lib/ld-linux-aarch64.so.1.usr-is-merged", "to:"),
            id="incomplete-record",
        ),
    ],
)
@pytest.mark.parametrize("interleaved", [False, True])
def test_unknown_diversion_context(source, target, interleaved):
    if interleaved:
        lines = [DIVERSION_WARNING, DIVERSION_WARNING, target, source]
    else:
        lines = [DIVERSION_WARNING, source, DIVERSION_WARNING, target]
    assert filter_warning_lines(lines, PackageType.deb) == (
        [DIVERSION_WARNING, DIVERSION_WARNING],
        [],
    )
    # Valid records elsewhere must not rescue missing or unknown context.
    output = "\n".join(KNOWN_DIVERSION + lines + KNOWN_DIVERSION)
    with pytest.raises(SystemExit) as error:
        validate_output(output, IGNORE_FILE, PackageType.deb)
    assert error.value.code == 1


@pytest.mark.parametrize(
    "lines",
    [
        pytest.param([DIVERSION_WARNING], id="no-context"),
        pytest.param([DIVERSION_WARNING, DIVERSION_FROM], id="source-only"),
        pytest.param([DIVERSION_WARNING, DIVERSION_TO], id="target-only"),
        pytest.param(
            [DIVERSION_WARNING, DIVERSION_WARNING, DIVERSION_FROM],
            id="truncated-interleaving",
        ),
        pytest.param([DIVERSION_WARNING, DIVERSION_FROM] * 2, id="unbalanced-source"),
        pytest.param([DIVERSION_WARNING, DIVERSION_TO] * 2, id="unbalanced-target"),
        pytest.param(KNOWN_DIVERSION + [DIVERSION_WARNING], id="extra-warning"),
        pytest.param(
            KNOWN_DIVERSION + [DIVERSION_FROM, DIVERSION_TO],
            id="extra-details",
        ),
        pytest.param(
            [DIVERSION_FROM, DIVERSION_WARNING, DIVERSION_WARNING, DIVERSION_TO],
            id="detail-before-warning",
        ),
        pytest.param(
            [DIVERSION_WARNING, DIVERSION_FROM, DIVERSION_TO, DIVERSION_WARNING],
            id="detail-overtakes-warning",
        ),
        pytest.param(
            KNOWN_DIVERSION
            + ["dpkg-shlibdeps: warning: cannot find library libunknown.so"],
            id="other-shlibdeps-warning",
        ),
        pytest.param(
            KNOWN_DIVERSION + ["dpkg-shlibdeps: error: unknown diagnostic"],
            id="extra-diagnostic-type",
        ),
        pytest.param(
            KNOWN_DIVERSION + [" local diversion from: /unknown"],
            id="extra-local-diversion",
        ),
        pytest.param(
            KNOWN_DIVERSION + [DIVERSION_WARNING + " extra"],
            id="nonliteral-warning",
        ),
    ],
)
def test_incomplete_or_ambiguous_diversion_block(lines):
    assert filter_warning_lines(lines, PackageType.deb) == (
        [line for line in lines if "warning" in line.lower()],
        [],
    )
    with pytest.raises(SystemExit) as error:
        validate_output("\n".join(lines), IGNORE_FILE, PackageType.deb)
    assert error.value.code == 1


@pytest.mark.parametrize(
    "boundary",
    ["", "unrelated output", "   dh_gencontrol -a", "compiler: warning: unrelated"],
)
def test_diversion_context_does_not_cross_boundaries(boundary):
    lines = [
        DIVERSION_WARNING,
        DIVERSION_FROM,
        boundary,
        DIVERSION_WARNING,
        DIVERSION_TO,
    ]
    base_warnings, _ = filter_warning_lines(lines, PackageType.deb)
    assert base_warnings.count(DIVERSION_WARNING) == 2
    with pytest.raises(SystemExit):
        validate_output("\n".join(lines), IGNORE_FILE, PackageType.deb)


@pytest.mark.parametrize("before", [False, True])
def test_unrelated_diversion_warning_remains_fatal(before):
    missing_context = [DIVERSION_WARNING]
    blocks = (
        [missing_context, KNOWN_DIVERSION]
        if before
        else [KNOWN_DIVERSION, missing_context]
    )
    lines = blocks[0] + ["   dh_gencontrol -a"] + blocks[1]
    assert filter_warning_lines(lines, PackageType.deb) == ([DIVERSION_WARNING], [])
    with pytest.raises(SystemExit):
        validate_output("\n".join(lines), IGNORE_FILE, PackageType.deb)


def test_known_diversion_does_not_ignore_lintian():
    lintian_lines = ["package: W: unknown-warning", "package: E: unknown-error"]
    lines = KNOWN_DIVERSION + ["Now running lintian"] + lintian_lines
    assert filter_warning_lines(lines, PackageType.deb) == ([], lintian_lines)
    with pytest.raises(SystemExit):
        validate_output("\n".join(lines), IGNORE_FILE, PackageType.deb)


def test_known_diversion_not_ignored_for_rpm():
    assert filter_warning_lines(KNOWN_DIVERSION, PackageType.rpm) == (
        [DIVERSION_WARNING, DIVERSION_WARNING],
        [],
    )
    with pytest.raises(SystemExit):
        validate_output("\n".join(KNOWN_DIVERSION), IGNORE_FILE, PackageType.rpm)
