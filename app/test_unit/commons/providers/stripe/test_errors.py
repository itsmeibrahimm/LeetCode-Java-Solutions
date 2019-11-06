from typing import cast
from uuid import uuid4

from app.commons.providers.stripe.errors import StripeErrorCode, StripeDeclineCode


def test_stripe_error_code():
    for code in StripeErrorCode:
        assert code is StripeErrorCode.get_or_none(cast(StripeErrorCode, code).value)
        assert code.value == code  # make sure string value == StrEnum member

    unknown_code = str(uuid4())
    assert not StripeErrorCode.get_or_none(unknown_code)


def test_stripe_decline_code():
    for code in StripeDeclineCode:
        assert code is StripeDeclineCode.get_or_none(
            cast(StripeDeclineCode, code).value
        )
        assert code.value == code  # make sure string value == StrEnum member

    unknown_code = str(uuid4())
    assert not StripeDeclineCode.get_or_none(unknown_code)
