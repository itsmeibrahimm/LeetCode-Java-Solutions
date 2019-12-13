import asyncio
from datetime import datetime, timezone

import pytest
import pytest_mock
from IPython.utils.tz import utcnow

from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.providers.stripe.stripe_models import CreateAccountTokenMetaDataRequest
from app.commons.test_integration.utils import (
    prepare_and_validate_stripe_account_token,
    prepare_and_validate_stripe_account,
)
from app.commons.types import CountryCode
from app.payout.core.account.processors.get_account import (
    GetPayoutAccountRequest,
    GetPayoutAccount,
)
from app.payout.core.account import models as account_models
from app.payout.core.exceptions import (
    payout_account_not_found_error,
    PayoutErrorCode,
    payout_error_message_maps,
    PayoutError,
)
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountCreate,
    PaymentAccount,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.models import AccountType


class TestGetPayoutAccount:
    pytestmark = [pytest.mark.asyncio]

    async def test_get_payout_account(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_test: StripeTestClient,
    ):
        # enable get_verification_requirements to be returned
        mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        data = PaymentAccountCreate(
            account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
            entity="dasher",
            resolve_outstanding_balance_frequency="daily",
            payout_disabled=True,
            charges_enabled=True,
            old_account_id=1234,
            upgraded_to_managed_account_at=datetime.now(timezone.utc),
            is_verified_with_stripe=True,
            transfers_enabled=True,
            statement_descriptor="test_statement_descriptor",
        )
        created_account = await payment_account_repo.create_payment_account(data)
        assert created_account.id, "id shouldn't be None"
        assert created_account.created_at, "created_at shouldn't be None"

        request = GetPayoutAccountRequest(payout_account_id=created_account.id)
        payment_account = PaymentAccount(
            id=created_account.id,
            account_type=data.account_type,
            entity=data.entity,
            resolve_outstanding_balance_frequency=data.resolve_outstanding_balance_frequency,
            payout_disabled=data.payout_disabled,
            charges_enabled=data.charges_enabled,
            old_account_id=data.old_account_id,
            upgraded_to_managed_account_at=data.upgraded_to_managed_account_at,
            is_verified_with_stripe=data.is_verified_with_stripe,
            transfers_enabled=data.transfers_enabled,
            statement_descriptor=data.statement_descriptor,
            created_at=utcnow(),
        )

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
        sma_data = StripeManagedAccountCreate(
            stripe_id=account.stripe_id,
            country_shortname="US",
            fingerprint="fingerprint",
            verification_disabled_reason="no-reason",
        )
        sma = await payment_account_repo.create_stripe_managed_account(sma_data)

        await payment_account_repo.update_payment_account_by_id(
            created_account.id, PaymentAccountUpdate(account_id=sma.id)
        )

        get_account_op = GetPayoutAccount(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
        )

        internal_account = await get_account_op._execute()

        assert internal_account.verification_requirements

        @asyncio.coroutine
        def mock_get_payment_account(*args):
            return payment_account

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )
        get_payout_account: account_models.PayoutAccountInternal = await get_account_op._execute()
        assert get_payout_account.payment_account.id == created_account.id
        assert (
            get_payout_account.payment_account.statement_descriptor
            == data.statement_descriptor
        )

        get_error = payout_account_not_found_error()
        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=get_error,
        )
        with pytest.raises(PayoutError) as e:
            await get_account_op._execute()
        assert e.value.error_code == PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND.value]
        )
