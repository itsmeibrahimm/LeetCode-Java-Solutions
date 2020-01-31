from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.stripe.stripe_models import (
    Individual,
    DateOfBirth,
    Address,
    CreateAccountTokenRequest,
    CreateAccountRequest,
    CreateAccountTokenMetaDataRequest,
    Token,
)
from app.commons.types import CountryCode


def prepare_and_validate_stripe_account_token(
    stripe_client: StripeClient, data: CreateAccountTokenMetaDataRequest = None
):
    if not data:
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
    account_token = stripe_client.create_account_token(
        request=CreateAccountTokenRequest(account=data, country=CountryCode.US)
    )
    assert account_token
    assert account_token.id.startswith("ct_")
    return account_token


def prepare_and_validate_stripe_account(
    stripe_client: StripeClient, account_token: Token = None
):
    if not account_token:
        account_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe_client
        )

    account = stripe_client.create_account(
        request=CreateAccountRequest(
            country=CountryCode.US,
            account_token=account_token.id if account_token else None,
        )
    )
    assert account
    assert account.id.startswith("acct_")
    assert account.settings.payouts.schedule.interval == "manual"
    return account
