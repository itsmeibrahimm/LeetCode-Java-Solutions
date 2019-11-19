from typing import cast

from app.payin.core.exceptions import _payin_error_message_maps, PayinErrorCode


def test_payin_error_code():

    payin_error_docstring = str(PayinErrorCode.__doc__)

    for code in PayinErrorCode:
        code = cast(PayinErrorCode, code)

        # test new message property compatible with deprecated error message
        assert code.message == _payin_error_message_maps.get(code.value, None)

        # test StrEnum and Str equality
        assert code.value == code

        # test value of error code is built into docstring
        assert code.value in payin_error_docstring

        # test message of error code is build into docstring
        assert code.message in payin_error_docstring
