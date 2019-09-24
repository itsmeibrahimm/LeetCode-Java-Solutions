from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.stripe.stripe_models import (
    Individual,
    DateOfBirth,
    Address,
    CreateAccountTokenRequest,
    CreateAccountRequest,
    CreateAccountTokenMetaDataRequest,
)
from app.commons.types import CountryCode


def prepare_and_validate_stripe_account_token(stripe: StripeClient):
    data = CreateAccountTokenMetaDataRequest(
        business_type="individual",
        individual=Individual(
            first_name="Test",
            last_name="Payment",
            dob=DateOfBirth(day=1, month=1, year=1990),
            address=Address(
                city="Mountain View",
                country=CountryCode.US.value,
                line1="123 Castro St",
                line2="",
                postal_code="94041",
                state="CA",
            ),
            ssn_last_4="1234",
        ),
        tos_shown_and_accepted=True,
    )
    account_token = stripe.create_account_token(
        request=CreateAccountTokenRequest(account=data, country=CountryCode.US)
    )
    assert account_token
    assert account_token.id.startswith("ct_")


def prepare_and_validate_stripe_account(stripe: StripeClient):
    data = CreateAccountTokenMetaDataRequest(
        business_type="individual",
        individual=Individual(
            first_name="Test",
            last_name="Payment",
            dob=DateOfBirth(day=1, month=1, year=1990),
            address=Address(
                city="Mountain View",
                country=CountryCode.US.value,
                line1="123 Castro St",
                line2="",
                postal_code="94041",
                state="CA",
            ),
            ssn_last_4="1234",
        ),
        tos_shown_and_accepted=True,
    )
    account_token = stripe.create_account_token(
        request=CreateAccountTokenRequest(account=data, country=CountryCode.US)
    )
    assert account_token

    account = stripe.create_stripe_account(
        request=CreateAccountRequest(
            country=CountryCode.US,
            type="custom",
            account_token=account_token.id,
            requested_capabilities=["legacy_payments"],
        )
    )
    assert account
    assert account.id.startswith("acct_")
    return account
