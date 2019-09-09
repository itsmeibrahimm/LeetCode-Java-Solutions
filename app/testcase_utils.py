from typing import Any, Dict, Set


def validate_expected_items_in_dict(
    expected: Dict[str, Any], actual: Dict[str, Any], strict_equal: bool = False
):
    """
    Validate if actual dict has data specified by expected dict
    :param expected: contains expected items
    :param actual: dict to be validated
    :param strict_equal: if set to True, actual dict should contains exact same items as expected dict
    :raise AssertionError if validation failed

    Note: naive implementation to validate two dict like data e.g. JSON responses, or plain dict from dataclass
    which relies on __eq__ being correctly implemented in complex data structure.
    """

    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())

    failed = False
    unexpected: Dict[str, Any] = {}
    missing: Set[str] = set()
    for ek in expected_keys:
        expected_val = expected.get(ek)
        actual_val = actual.get(ek, None)
        if actual_val != expected_val:
            failed = True
            if not actual_val:
                missing.add(ek)
            else:
                unexpected[ek] = actual.get(ek)

    if strict_equal and (len(actual_keys) > len(expected_keys)):
        failed = True
        missing.update(set(actual_keys.difference(expected_keys)))

    if failed:
        raise AssertionError(
            f"Dict validation failed. expected={expected}, actual={actual}, "
            f"missing fields={missing}, unexpected={unexpected}"
        )
