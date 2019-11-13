from typing import cast

from app.payin.core.exceptions import _payin_error_message_maps, PayinErrorCode


def test_payin_error_code():
    assert len(_payin_error_message_maps) == len(PayinErrorCode._value2member_map_)

    payin_error_docstring = str(PayinErrorCode.__doc__)

    for code in PayinErrorCode:
        code = cast(PayinErrorCode, code)
        assert code.value in _payin_error_message_maps
        assert code.message == _payin_error_message_maps.get(code.value)
        assert code.value in payin_error_docstring
        assert PayinErrorCode.known_value(code.value)
        assert code.message in payin_error_docstring
