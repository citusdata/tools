import difflib


def are_strings_equal(expected_string: str, actual_str: str) -> bool:
    output_list = [li for li in difflib.ndiff(expected_string, actual_str) if li[0] != ' ']

    for output in output_list:
        if not (output.strip() == '+' or output.strip() == '-'):
            raise Exception(f"Actual and expected string are not same Diff:{''.join(output_list)} ")
    return True;
