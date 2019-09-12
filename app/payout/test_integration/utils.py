from datetime import datetime, timezone

from app.payout.repository.bankdb.model.payout import PayoutCreate
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
)
from app.payout.repository.bankdb.model.transaction import TransactionCreate
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransferCreate,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccountCreate
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
)
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferCreate
from app.payout.repository.maindb.model.transfer import TransferCreate
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.testcase_utils import validate_expected_items_in_dict

"""
For tables in maindb, it has timezone info, when initialize datetime fields in those tables, use datetiem.now(timezone.utc)
For tables in bankdb, it does not have timezone info, when initialize datetime fields in those tables, use datetime.utcnow()
"""


async def prepare_and_insert_transfer(
    transfer_repo: TransferRepository,
    payment_account_id=12345678,
    timestamp=datetime.now(timezone.utc),
):
    data = TransferCreate(
        subtotal=123,
        adjustments="some-adjustment",
        amount=123,
        method="stripe",
        currency="currency",
        submitted_at=timestamp,
        deleted_at=timestamp,
        manual_transfer_reason="manual_transfer_reason",
        status="status",
        status_code="status_code",
        submitting_at=timestamp,
        should_retry_on_failure=True,
        statement_description="statement_description",
        created_by_id=123,
        deleted_by_id=321,
        payment_account_id=payment_account_id,
        recipient_id=321,
        recipient_ct_id=123,
        submitted_by_id=321,
    )
    assert len(data.__fields_set__) == len(data.__fields__), "all fields should be set"

    transfer = await transfer_repo.create_transfer(data)
    assert transfer.id, "transfer is created, assigned an ID"
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=transfer.dict()
    )
    return transfer


async def prepare_and_insert_managed_account_transfer(
    managed_account_transfer_repo: ManagedAccountTransferRepository,
    payment_account_id,
    transfer_id,
):
    data = ManagedAccountTransferCreate(
        amount=2000,
        transfer_id=transfer_id,
        payment_account_id=payment_account_id,
        currency="usd",
    )
    ma_transfer = await managed_account_transfer_repo.create_managed_account_transfer(
        data
    )
    assert ma_transfer.id, "managed_account_transfer is created, assigned an ID"
    assert ma_transfer.stripe_id == ""
    assert ma_transfer.stripe_status == ""
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=ma_transfer.dict()
    )
    return ma_transfer


async def prepare_and_insert_payout(
    payout_repo: PayoutRepository, ide_key="stripe-payout-request-idempotency-key-001"
):
    data = PayoutCreate(
        amount=1000,
        payment_account_id=123,
        status="failed",
        currency="USD",
        fee=199,
        type="instant",
        idempotency_key=ide_key,
        payout_method_id=1,
        transaction_ids=[1, 2, 3],
        token="payout-test-token",
        fee_transaction_id=10,
        error=None,
    )

    payout = await payout_repo.create_payout(data)
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=payout.dict()
    )
    assert payout.id, "payout is created, assigned an ID"
    return payout


async def prepare_and_insert_stripe_payout_request(
    stripe_payout_request_repo: StripePayoutRequestRepository,
    payout_id,
    ide_key="stripe-payout-request-idempotency-key-001",
):
    data = StripePayoutRequestCreate(
        payout_id=payout_id,
        idempotency_key=ide_key,
        payout_method_id=1,
        status="failed",
        stripe_payout_id=f"stripe_tr_xxx_{payout_id}",
        stripe_account_id="cus_xxxx_1",
    )
    stripe_payout_request = await stripe_payout_request_repo.create_stripe_payout_request(
        data
    )
    assert stripe_payout_request.id, "stripe payout request is created, assigned an ID"
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=stripe_payout_request.dict()
    )
    assert (
        stripe_payout_request.stripe_payout_id
    ), "stripe payout request has stripe payout id"
    return stripe_payout_request


async def prepare_and_insert_transaction(transaction_repo: TransactionRepository):
    data = TransactionCreate(
        amount=1000, payment_account_id=123, amount_paid=800, currency="USD"
    )

    transaction = await transaction_repo.create_transaction(data)
    assert transaction.id, "transaction is created, assigned an ID"
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=transaction.dict()
    )
    return transaction


async def prepare_and_insert_stripe_transfer(
    stripe_transfer_repo: StripeTransferRepository,
    transfer_id,
    stripe_status="",
    stripe_id="",
):
    data = StripeTransferCreate(
        stripe_status=stripe_status,
        transfer_id=transfer_id,
        stripe_id=stripe_id,
        stripe_request_id="stripe_request_id",
        stripe_failure_code="stripe_failure_code",
        stripe_account_id="stripe_account_id",
        stripe_account_type="stripe_account_type",
        country_shortname="country_shortname",
        bank_last_four="bank_last_four",
        bank_name="bank_name",
        submission_error_code="submission_error_code",
        submission_error_type="submission_error_type",
        submission_status="submission_status",
        submitted_at=datetime.now(timezone.utc),
    )

    stripe_transfer = await stripe_transfer_repo.create_stripe_transfer(data)
    assert stripe_transfer.id, "stripe_transfer is created, assigned an ID"
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=stripe_transfer.dict()
    )
    return stripe_transfer


async def prepare_and_insert_payment_account(
    payment_account_repo: PaymentAccountRepository
):
    data = PaymentAccountCreate(
        account_id=123,
        account_type="sma",
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

    assert len(data.__fields_set__) == len(data.__fields__), "all fields should be set"

    payment_account = await payment_account_repo.create_payment_account(data)
    assert payment_account.id, "id shouldn't be None"
    assert payment_account.created_at, "created_at shouldn't be None"

    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=payment_account.dict()
    )
    return payment_account


async def prepare_and_insert_stripe_managed_account(
    payment_account_repo: PaymentAccountRepository
):
    data = StripeManagedAccountCreate(
        stripe_id="stripe_id",
        country_shortname="us",
        stripe_last_updated_at=datetime.now(timezone.utc),
        bank_account_last_updated_at=datetime.now(timezone.utc),
        fingerprint="fingerprint",
        default_bank_last_four="last4",
        default_bank_name="bank",
        verification_disabled_reason="no-reason",
        verification_due_by=datetime.now(timezone.utc),
        verification_fields_needed="a lot",
    )

    assert len(data.__fields_set__) == len(data.__fields__), "all fields should be set"

    sma = await payment_account_repo.create_stripe_managed_account(data)
    assert sma.id, "account is created, assigned an ID"

    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=sma.dict()
    )
    return sma
