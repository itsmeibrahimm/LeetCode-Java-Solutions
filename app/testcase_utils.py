from typing import Dict, Any


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

    expected_items: set = set(expected.items())
    actual_items: set = set(actual.items())

    failed = False
    if strict_equal:
        failed = expected_items != actual_items
    else:
        failed = not (expected_items <= actual_items)

    if failed:
        missing = expected_items.difference(actual_items)
        unexpected: Dict[str, Any] = {}
        if strict_equal:
            unexpected.update(actual_items.difference(expected_items))
        raise AssertionError(
            f"Dict validation failed. expected={expected}, actual={actual_items}, "
            f"missing fields={missing}, unexpected fields={unexpected}"
        )
