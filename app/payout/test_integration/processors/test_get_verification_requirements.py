import pytest
import pytest_mock

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_client import (
    StripeAsyncClient,
    StripeTestClient,
    StripeClient,
)
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import (
    CreateAccountTokenMetaDataRequest,
    Address,
    StripeClientSettings,
)
from app.commons.test_integration.utils import (
    prepare_and_validate_stripe_account_token,
    prepare_and_validate_stripe_account,
)
from app.commons.types import CountryCode
from app.commons.utils.pool import ThreadPoolHelper

from app.payout.core.account.processors.get_verification_requirements import (
    GetVerificationRequirementsRequest,
    GetVerificationRequirements,
)

from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository


class TestGetPayoutAccount:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_async_client(self, app_config: AppConfig):
        stripe_client = StripeClient(
            settings_list=[
                StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ],
            http_client=TimedRequestsClient(),
        )

        stripe_thread_pool = ThreadPoolHelper(
            max_workers=app_config.STRIPE_MAX_WORKERS, prefix="stripe"
        )

        stripe_async_client = StripeAsyncClient(
            executor_pool=stripe_thread_pool, stripe_client=stripe_client
        )
        yield stripe_async_client
        stripe_thread_pool.shutdown()

    async def test_verification_state_update_and_retrieve_individual(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_async_client: StripeAsyncClient,
        stripe_test: StripeTestClient,
    ):
        create_account_token_data = CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=stripe_models.Individual(
                first_name="Test",
                last_name="Payment",
                dob=stripe_models.DateOfBirth(day=1, month=1, year=1990),
                address=stripe_models.Address(
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
        account_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe_test, data=create_account_token_data
        )
        account = prepare_and_validate_stripe_account(stripe_test, account_token)
        data = StripeManagedAccountCreate(
            stripe_id=account.stripe_id,
            country_shortname="US",
            fingerprint="fingerprint",
            verification_disabled_reason="no-reason",
        )
        sma = await payment_account_repo.create_stripe_managed_account(data)
        request = GetVerificationRequirementsRequest(
            stripe_managed_account_id=sma.id,
            country_shortname=sma.country_shortname,
            stripe_id=sma.stripe_id,
        )
        required_fields_op = GetVerificationRequirements(
            logger=mocker.Mock(),
            request=request,
            payment_account_repo=payment_account_repo,
            stripe_client=stripe_async_client,
        )
        verification_requirements = await required_fields_op.execute()
        assert verification_requirements
        assert verification_requirements.verification_status

    async def test_verification_state_update_and_retrieve_company(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_async_client: StripeAsyncClient,
        stripe_test: StripeTestClient,
    ):
        create_account_token_data = CreateAccountTokenMetaDataRequest(
            business_type="company",
            company=stripe_models.Company(
                address=Address(
                    city="SJC",
                    country="US",
                    line1="123 first ave",
                    line2="",
                    postal_code="95054",
                    state="California",
                ),
                name="Test Corp.",
                tax_id="123432",
            ),
            tos_shown_and_accepted=True,
        )
        account_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe_test, data=create_account_token_data
        )
        account = prepare_and_validate_stripe_account(stripe_test, account_token)
        data = StripeManagedAccountCreate(
            stripe_id=account.stripe_id,
            country_shortname="US",
            fingerprint="fingerprint",
            verification_disabled_reason="no-reason",
        )
        sma = await payment_account_repo.create_stripe_managed_account(data)
        request = GetVerificationRequirementsRequest(
            stripe_managed_account_id=sma.id,
            country_shortname=sma.country_shortname,
            stripe_id=sma.stripe_id,
        )
        required_fields_op = GetVerificationRequirements(
            logger=mocker.Mock(),
            request=request,
            payment_account_repo=payment_account_repo,
            stripe_client=stripe_async_client,
        )
        verification_requirements = await required_fields_op.execute()
        assert verification_requirements
        assert verification_requirements.verification_status
