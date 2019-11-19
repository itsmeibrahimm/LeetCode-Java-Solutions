import asyncio
import pytest
import pytest_mock
from stripe.error import StripeError
from structlog import BoundLogger
import stripe
from stripe import util

from app.commons.core.errors import DBConnectionError
from app.commons.database.infra import DB
from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_client import StripeAsyncClient

from app.commons.types import CountryCode
import app.payout.core.account.models as models
from app.payout.core.account.processors.get_verification_requirements import (
    GetVerificationRequirements,
    GetVerificationRequirementsRequest,
)
from app.payout.core.account.utils import get_internal_verification_status


from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)

from app.payout.repository.maindb.payment_account import PaymentAccountRepository


@pytest.fixture
def payment_account_repository(payout_maindb: DB) -> PaymentAccountRepository:
    return PaymentAccountRepository(database=payout_maindb)


@pytest.fixture
def log() -> BoundLogger:
    from unittest.mock import MagicMock

    bl = BoundLogger(None, None, None)
    bl.info = MagicMock(return_value=None)
    bl.warning = MagicMock(return_value=None)
    bl.error = MagicMock(return_value=None)
    return bl


def mock_retrieve_account_raise_error():
    return StripeError()


def mock_stripe_account_individual() -> stripe_models.Account:
    return util.convert_to_stripe_object(
        {
            "id": "acct_xxxx",
            "business_type": "individual",
            "country": "US",
            "default_currency": "usd",
            "email": "abc@xmail.com",
            "individual": {
                "id": "person_xxxx",
                "account": "acct_xxxx",
                "email": "abc@xmail.com",
                "ssn_last_4_provided": True,
                "relationship": {
                    "director": False,
                    "executive": False,
                    "owner": False,
                    "percent_ownership": None,
                    "representative": True,
                    "title": None,
                },
                "requirements": {
                    "currently_due": [],
                    "eventually_due": [],
                    "past_due": [],
                    "pending_verification": [],
                },
                "verification": {
                    "details_code": "scan_failed_greyscale",
                    "document": {
                        "back": "",
                        "details": "",
                        "details_code": "",
                        "front": "",
                    },
                    "additional_document": {
                        "back": "",
                        "details": "",
                        "details_code": "",
                        "front": "",
                    },
                    "status": "pending",
                },
                "id_number_provided": True,
                "created": 1571783850,
                "object": "person",
            },
            "payouts_enabled": False,
            "requirements": {
                "current_deadline": None,
                "currently_due": ["external_account"],
                "disabled_reason": "requirements.past_due",
                "eventually_due": ["external_account"],
                "past_due": ["external_account"],
                "pending_verification": [],
            },
            "type": "custom",
            "id_number_provided": True,
            "created": 1571783850,
            "object": "account",
            "charges_enabled": True,
            "details_submitted": False,
        }
    )


def mock_stripe_account_company() -> stripe.api_resources.Account:
    return util.convert_to_stripe_object(
        {
            "id": "acct_xxxx",
            "business_type": "company",
            "country": "US",
            "default_currency": "usd",
            "email": "abc@xmail.com",
            "company": {
                "address": {
                    "city": "SJC",
                    "country": "US",
                    "line1": "123 first ave",
                    "line2": "",
                    "postal_code": "95054",
                    "state": "California",
                },
                "name": "Test Corp.",
                "tax_id": "123432",
                "verification": {
                    "details_code": "scan_failed_greyscale",
                    "document": {
                        "back": "",
                        "details": "",
                        "details_code": "",
                        "front": "",
                    },
                    "additional_document": {
                        "back": "",
                        "details": "",
                        "details_code": "",
                        "front": "",
                    },
                    "status": "unverified",
                },
            },
            "payouts_enabled": True,
            "requirements": {
                "current_deadline": None,
                "currently_due": ["external_account"],
                "disabled_reason": "requirements.past_due",
                "eventually_due": ["external_account"],
                "past_due": ["external_account"],
                "pending_verification": [],
            },
            "type": "custom",
            "id_number_provided": True,
            "created": 1571783850,
            "object": "account",
            "charges_enabled": True,
            "details_submitted": False,
        }
    )


def test_get_internal_verification_status_individual():
    stripe_response = mock_stripe_account_individual()
    stripe_response.payouts_enabled = True

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = util.convert_to_stripe_object(
        {
            "current_deadline": None,
            "currently_due": [],
            "disabled_reason": None,
            "eventually_due": [],
            "past_due": [],
            "pending_verification": ["person.id_number"],
        }
    )

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.PENDING

    stripe_response.requirements = util.convert_to_stripe_object(
        {
            "current_deadline": None,
            "currently_due": ["external_account"],
            "disabled_reason": None,
            "eventually_due": ["external_account"],
            "past_due": ["external_account"],
            "pending_verification": [],
        }
    )
    stripe_response.payouts_enabled = False

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.BLOCKED

    stripe_response.payouts_enabled = True
    stripe_response.requirements = util.convert_to_stripe_object(
        {
            "current_deadline": None,
            "currently_due": [],
            "disabled_reason": None,
            "eventually_due": [],
            "past_due": [],
            "pending_verification": [],
        }
    )

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.VERIFIED


def test_get_internal_verification_status_company():
    stripe_response = mock_stripe_account_company()
    stripe_response.payouts_enabled = True

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = util.convert_to_stripe_object(
        {
            "current_deadline": None,
            "currently_due": [],
            "disabled_reason": None,
            "eventually_due": [],
            "past_due": [],
            "pending_verification": [],
        }
    )

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.VERIFIED

    stripe_response.requirements = util.convert_to_stripe_object(
        {
            "current_deadline": None,
            "currently_due": ["external_account"],
            "disabled_reason": None,
            "eventually_due": ["external_account"],
            "past_due": ["external_account"],
            "pending_verification": [],
        }
    )
    stripe_response.payouts_enabled = False

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.BLOCKED

    stripe_response.payouts_enabled = True

    # But there are fields needed
    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.FIELDS_REQUIRED

    stripe_response.requirements = util.convert_to_stripe_object(
        {
            "current_deadline": None,
            "currently_due": [],
            "disabled_reason": None,
            "eventually_due": [],
            "past_due": [],
            "pending_verification": [],
        }
    )

    internal_status_returned = get_internal_verification_status(stripe_response)
    assert internal_status_returned == models.VerificationStatus.VERIFIED


@pytest.mark.asyncio
async def test_verification_state_update_and_retrieve_company(
    mocker: pytest_mock.MockFixture,
    payment_account_repository: PaymentAccountRepository,
    stripe_async_client: StripeAsyncClient,
):
    @asyncio.coroutine
    def mock_retrieve_stripe_account(*args, **kwargs):
        return mock_stripe_account_company()

    mocker.patch(
        "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_stripe_account",
        side_effect=mock_retrieve_stripe_account,
    )

    @asyncio.coroutine
    def mock_update_stripe_account_db(*args, **kwargs):
        return None

    mocker.patch(
        "app.payout.repository.maindb.payment_account.PaymentAccountRepository.update_stripe_managed_account_by_id",
        side_effect=mock_update_stripe_account_db,
    )
    sma = StripeManagedAccount(
        id=1, country_shortname=CountryCode.US, stripe_id="acct_xxxx"
    )
    request = GetVerificationRequirementsRequest(
        stripe_managed_account_id=sma.id,
        country_shortname=sma.country_shortname,
        stripe_id=sma.stripe_id,
    )
    required_fields_op = GetVerificationRequirements(
        logger=log,
        request=request,
        payment_account_repo=payment_account_repository,
        stripe_client=stripe_async_client,
    )
    verification_requirements = await required_fields_op.execute()
    assert verification_requirements
    assert (
        verification_requirements.verification_status
        == models.VerificationStatus.FIELDS_REQUIRED
    )
    assert verification_requirements.additional_error_info


@pytest.mark.asyncio
async def test_verification_state_update_and_retrieve_individual(
    mocker: pytest_mock.MockFixture,
    payment_account_repository: PaymentAccountRepository,
    stripe_async_client: StripeAsyncClient,
):
    @asyncio.coroutine
    def mock_retrieve_stripe_account(*args, **kwargs):
        return mock_stripe_account_individual()

    mocker.patch(
        "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_stripe_account",
        side_effect=mock_retrieve_stripe_account,
    )

    @asyncio.coroutine
    def mock_update_stripe_account_db(*args, **kwargs):
        return None

    mocker.patch(
        "app.payout.repository.maindb.payment_account.PaymentAccountRepository.update_stripe_managed_account_by_id",
        side_effect=mock_update_stripe_account_db,
    )
    sma = StripeManagedAccount(
        id=1, country_shortname=CountryCode.US, stripe_id="acct_xxxx"
    )
    request = GetVerificationRequirementsRequest(
        stripe_managed_account_id=sma.id,
        country_shortname=sma.country_shortname,
        stripe_id=sma.stripe_id,
    )
    required_fields_op = GetVerificationRequirements(
        logger=log,
        request=request,
        payment_account_repo=payment_account_repository,
        stripe_client=stripe_async_client,
    )
    verification_requirements = await required_fields_op.execute()
    assert verification_requirements
    assert (
        verification_requirements.verification_status
        == models.VerificationStatus.BLOCKED
    )
    assert verification_requirements.additional_error_info


@pytest.mark.asyncio
async def test_verification_state_update_and_retrieve_with_stripe_error(
    mocker: pytest_mock.MockFixture,
    payment_account_repository: PaymentAccountRepository,
    stripe_async_client: StripeAsyncClient,
    log: BoundLogger,
):
    @asyncio.coroutine
    def mock_retrieve_stripe_account(*args, **kwargs):
        return mock_retrieve_account_raise_error()

    mocker.patch(
        "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_stripe_account",
        side_effect=mock_retrieve_stripe_account,
    )

    @asyncio.coroutine
    def mock_update_stripe_account_db(*args, **kwargs):
        return None

    mocker.patch(
        "app.payout.repository.maindb.payment_account.PaymentAccountRepository.update_stripe_managed_account_by_id",
        side_effect=mock_update_stripe_account_db,
    )
    sma = StripeManagedAccount(
        id=1, country_shortname=CountryCode.US, stripe_id="acct_xxxx"
    )

    request = GetVerificationRequirementsRequest(
        stripe_managed_account_id=sma.id,
        country_shortname=sma.country_shortname,
        stripe_id=sma.stripe_id,
    )
    required_fields_op = GetVerificationRequirements(
        logger=log,
        request=request,
        payment_account_repo=payment_account_repository,
        stripe_client=stripe_async_client,
    )
    verification_requirements = await required_fields_op.execute()
    assert verification_requirements == models.VerificationRequirements()
    args, kwargs = log.warning.call_args
    assert (
        "[GetVerificationRequirements] Exception while fetching Account object from PGP/Stripe"
        in args
    )


@pytest.mark.asyncio
async def test_verification_state_update_and_retrieve_with_DB_update_error(
    mocker: pytest_mock.MockFixture,
    payment_account_repository: PaymentAccountRepository,
    stripe_async_client: StripeAsyncClient,
    log: BoundLogger,
):
    @asyncio.coroutine
    def mock_retrieve_stripe_account(*args, **kwargs):
        return mock_stripe_account_individual()

    mocker.patch(
        "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_stripe_account",
        side_effect=mock_retrieve_stripe_account,
    )

    @asyncio.coroutine
    def mock_update_stripe_account_db(*args, **kwargs):
        raise DBConnectionError("DB error mock")

    mocker.patch(
        "app.payout.repository.maindb.payment_account.PaymentAccountRepository.update_stripe_managed_account_by_id",
        side_effect=mock_update_stripe_account_db,
    )
    sma = StripeManagedAccount(
        id=1, country_shortname=CountryCode.US, stripe_id="acct_xxxx"
    )

    request = GetVerificationRequirementsRequest(
        stripe_managed_account_id=sma.id,
        country_shortname=sma.country_shortname,
        stripe_id=sma.stripe_id,
    )
    required_fields_op = GetVerificationRequirements(
        logger=log,
        request=request,
        payment_account_repo=payment_account_repository,
        stripe_client=stripe_async_client,
    )
    verification_requirements = await required_fields_op.execute()
    # DBConnectionError thrown during DB update is caught but verification_requirements is not empty
    assert verification_requirements != models.VerificationRequirements()
    args, kwargs = log.warning.call_args
    assert (
        "[GetVerificationRequirements] Error while updating verification information on SMA"
        in args
    )
