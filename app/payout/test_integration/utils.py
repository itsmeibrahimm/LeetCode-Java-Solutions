from datetime import datetime, timezone
from typing import List, Tuple, Optional

from app.commons.test_integration.constants import TEST_DEFAULT_PAGE_SIZE
from app.commons.types import CountryCode, Currency
from stripe.error import StripeError

from app.payout.constants import CREATE_STRIPE_ACCOUNT_TYPE
from app.payout.repository.bankdb.model.payment_account_edit_history import (
    PaymentAccountEditHistoryCreate,
)
from app.payout.repository.bankdb.model.payout import PayoutCreate
from app.payout.repository.bankdb.model.payout_card import PayoutCardCreate, PayoutCard
from app.payout.repository.bankdb.model.payout_method import (
    PayoutMethodCreate,
    PayoutMethod,
)
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
)
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransferCreate,
)
from app.payout.repository.bankdb.model.transaction import (
    TransactionCreateDBEntity,
    TransactionDBEntity,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransferCreate,
)
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountCreate,
    PaymentAccount,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
    StripeManagedAccount,
)
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferCreate
from app.payout.repository.maindb.model.transfer import TransferCreate
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.testcase_utils import validate_expected_items_in_dict
import uuid
from app.commons.providers.stripe import stripe_models as models
import app.payout.models as payout_models


"""
For tables in maindb, it has timezone info, when initialize datetime fields in those tables, use datetiem.now(timezone.utc)
For tables in bankdb, it does not have timezone info, when initialize datetime fields in those tables, use datetime.utcnow()
"""


async def prepare_and_insert_transfer(
    transfer_repo: TransferRepository,
    payment_account_id=12345678,
    timestamp=datetime.now(timezone.utc),
    deleted_at=None,
    submitted_at=None,
    amount=123,
    status="status",
    method="stripe",
):
    data = TransferCreate(
        subtotal=123,
        adjustments="some-adjustment",
        amount=amount,
        method=method,
        currency="currency",
        submitted_at=submitted_at,
        deleted_at=deleted_at,
        manual_transfer_reason="manual_transfer_reason",
        status=status,
        status_code="status_code",
        submitting_at=timestamp,
        should_retry_on_failure=True,
        statement_description="statement_description",
        created_by_id=None,
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
    amount=2000,
):
    data = ManagedAccountTransferCreate(
        amount=amount,
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
    payout_repo: PayoutRepository,
    ide_key="stripe-payout-request-idempotency-key-001",
    status="failed",
    payout_account_id=123,
):
    data = PayoutCreate(
        amount=1000,
        payment_account_id=payout_account_id,
        status=status,
        currency=Currency.USD.value,
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
        status="new",
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


async def prepare_and_insert_transaction(
    transaction_repo: TransactionRepository,
    payout_account_id: int,
    state: Optional[payout_models.TransactionState] = None,
    transfer_id=None,
    amount=1000,
) -> TransactionDBEntity:
    data = TransactionCreateDBEntity(
        amount=amount,
        amount_paid=800,
        payment_account_id=payout_account_id,
        currency=Currency.USD.value,
        state=state,
        transfer_id=transfer_id,
    )

    transaction = await transaction_repo.create_transaction(data)
    assert transaction.id, "transaction is created, assigned an ID"
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=transaction.dict()
    )
    assert transaction.created_at, "created_at shouldn't be None"
    assert transaction.updated_at, "updated_at shouldn't be None"
    return transaction


async def prepare_and_insert_transaction_list_for_same_account(
    transaction_repo: TransactionRepository,
    payout_account_id: int,
    transfer_id: Optional[int] = None,
    payout_id: Optional[int] = None,
    count: int = 10,
) -> List[TransactionDBEntity]:
    transaction_list: List[TransactionDBEntity] = []
    for i in range(0, count):
        data = TransactionCreateDBEntity(
            amount=1000,
            amount_paid=800,
            payment_account_id=payout_account_id,
            currency=Currency.USD.value,
            transfer_id=transfer_id,
            payout_id=payout_id,
        )

        transaction = await transaction_repo.create_transaction(data)
        assert transaction.id, "transaction is created, assigned an ID"
        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=transaction.dict()
        )
        assert transaction.created_at, "created_at shouldn't be None"
        assert transaction.updated_at, "updated_at shouldn't be None"
        transaction_list.insert(0, transaction)
    return transaction_list


async def prepare_and_insert_paid_transaction_list_for_transfer(
    transaction_repo: TransactionRepository,
    payout_account_id: int,
    transfer_id: int,
    count: int = 5,
) -> List[TransactionDBEntity]:
    transaction_list: List[TransactionDBEntity] = []
    for i in range(0, count):
        data = TransactionCreateDBEntity(
            amount=1000,
            amount_paid=800,
            payment_account_id=payout_account_id,
            currency=Currency.USD.value,
            transfer_id=transfer_id,
            state=payout_models.TransactionState.ACTIVE.value,
        )

        transaction = await transaction_repo.create_transaction(data)
        assert transaction.id, "transaction is created, assigned an ID"
        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=transaction.dict()
        )
        assert transaction.created_at, "created_at shouldn't be None"
        assert transaction.updated_at, "updated_at shouldn't be None"
        transaction_list.insert(0, transaction)
    return transaction_list


async def prepare_and_insert_transaction_list_for_different_targets(
    transaction_repo: TransactionRepository,
    payment_account_repo: PaymentAccountRepository,
    count: int = TEST_DEFAULT_PAGE_SIZE + 5,
) -> Tuple[List[TransactionDBEntity], List[int]]:
    transaction_list: List[TransactionDBEntity] = []
    target_size = 5
    payment_account_list = await prepare_and_insert_payment_account_list(
        payment_account_repo, count=target_size
    )
    # fake 5 target_id
    target_id_list: List[int] = [
        payment_account.id for payment_account in payment_account_list
    ]

    for i in range(0, count):
        index = i % target_size
        payment_account = payment_account_list[index]
        data = TransactionCreateDBEntity(
            amount=1000,
            amount_paid=800,
            payment_account_id=payment_account.id,
            currency=Currency.USD.value,
            target_type=payout_models.TransactionTargetType.DASHER_DELIVERY
            if i % 2 == 0
            else payout_models.TransactionTargetType.DASHER_JOB,
            target_id=target_id_list[index],
        )

        transaction = await transaction_repo.create_transaction(data)
        assert transaction.id, "transaction is created, assigned an ID"
        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=transaction.dict()
        )
        transaction_list.insert(0, transaction)
    return transaction_list, target_id_list


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
        stripe_account_type="stripe_managed_account",
        country_shortname="US",
        bank_last_four="bank_last_four",
        bank_name="bank_name",
        submission_error_code="submission_error_code",
        submission_error_type="submission_error_type",
        submission_status=payout_models.StripeTransferSubmissionStatus.SUBMITTING,
        submitted_at=datetime.now(timezone.utc),
    )

    stripe_transfer = await stripe_transfer_repo.create_stripe_transfer(data)
    assert stripe_transfer.id, "stripe_transfer is created, assigned an ID"
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=stripe_transfer.dict()
    )
    return stripe_transfer


async def prepare_and_insert_payment_account(
    payment_account_repo: PaymentAccountRepository,
    account_id=None,
    entity="dasher",
    account_type=payout_models.AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
    transfers_enabled=True,
) -> PaymentAccount:
    data = PaymentAccountCreate(
        account_id=account_id,
        account_type=account_type,
        entity=entity,
        resolve_outstanding_balance_frequency="daily",
        payout_disabled=True,
        charges_enabled=True,
        old_account_id=1234,
        upgraded_to_managed_account_at=datetime.now(timezone.utc),
        is_verified_with_stripe=True,
        transfers_enabled=transfers_enabled,
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


async def prepare_and_insert_payment_account_list(
    payment_account_repo: PaymentAccountRepository,
    account_ids: List[payout_models.PgpAccountId] = None,
    count: int = 5,
) -> List[PaymentAccount]:
    payout_account_list: List[PaymentAccount] = []
    if account_ids:
        assert len(account_ids) == count
    for i in range(0, count):
        # create payout_account
        account_id = account_ids[i] if account_ids else None
        data = PaymentAccountCreate(
            account_id=account_id,
            account_type=payout_models.AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
            entity=payout_models.PayoutAccountTargetType.DASHER
            if i % 2 == 0
            else payout_models.PayoutAccountTargetType.STORE,
            resolve_outstanding_balance_frequency="daily",
            payout_disabled=True,
            charges_enabled=True,
            old_account_id=None,
            upgraded_to_managed_account_at=datetime.now(timezone.utc),
            is_verified_with_stripe=True,
            transfers_enabled=True,
            statement_descriptor="test_statement_descriptor",
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        payment_account = await payment_account_repo.create_payment_account(data)
        assert payment_account.id, "id shouldn't be None"
        assert payment_account.created_at, "created_at shouldn't be None"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=payment_account.dict()
        )
        payout_account_list.append(payment_account)
    return payout_account_list


async def prepare_and_insert_stripe_managed_account(
    payment_account_repo: PaymentAccountRepository,
    stripe_id="stripe_id",
    country_shortname="US",
    bank_account_last_updated_at=datetime.now(timezone.utc),
) -> StripeManagedAccount:
    data = StripeManagedAccountCreate(
        stripe_id=stripe_id,
        country_shortname=country_shortname,
        stripe_last_updated_at=datetime.now(timezone.utc),
        bank_account_last_updated_at=bank_account_last_updated_at,
        fingerprint="fingerprint",
        default_bank_last_four="last4",
        default_bank_name="bank",
        verification_disabled_reason="no-reason",
        verification_due_by=datetime.now(timezone.utc),
        verification_fields_needed="a lot",
        verification_status="PENDING",
        verification_error_info="",
        verification_fields_needed_v1="{}",
    )

    assert len(data.__fields_set__) == len(data.__fields__), "all fields should be set"

    sma = await payment_account_repo.create_stripe_managed_account(data)
    assert sma.id, "account is created, assigned an ID"

    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=sma.dict()
    )
    return sma


async def prepare_and_insert_stripe_managed_account_transfer(
    sma: StripeManagedAccount,
    stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
):
    data = StripeManagedAccountTransferCreate(
        amount=100,
        from_stripe_account_id="dd_sma",
        to_stripe_account_id=sma.stripe_id,
        token=str(uuid.uuid4()),
    )

    sma_transfer = await stripe_managed_account_transfer_repo.create_stripe_managed_account_transfer(
        data
    )
    assert sma_transfer.id, "stripe managed account transfer is created, assigned an ID"

    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=sma_transfer.dict()
    )
    return sma_transfer


async def prepare_and_insert_payout_card(
    payout_method_repo: PayoutMethodRepository,
    payout_card_repo: PayoutCardRepository,
    payout_account_id: int,
    is_default: bool = True,
    created_at: datetime = datetime.utcnow(),
    updated_at: datetime = datetime.utcnow(),
    fingerprint: Optional[str] = "fingerprint",
):
    payout_method = await prepare_and_insert_payout_method(
        payout_method_repo, payout_account_id, is_default
    )

    data = PayoutCardCreate(
        id=payout_method.id,
        stripe_card_id=f"{payout_method.id}_card_test_payout_card",
        last4="1234",
        brand="Bear Bank",
        exp_month=12,
        exp_year=23,
        created_at=created_at,
        updated_at=updated_at,
        fingerprint=fingerprint,
    )

    payout_card = await payout_card_repo.create_payout_card(data)
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=payout_card.dict()
    )
    assert payout_card.id, "payout card is created, assigned an ID"
    return payout_card


async def prepare_and_insert_payout_method(
    payout_method_repo: PayoutMethodRepository,
    payout_account_id: int,
    is_default: bool = True,
):
    data = PayoutMethodCreate(
        type=payout_models.PayoutExternalAccountType.CARD.value,
        currency=Currency.USD.value,
        country=CountryCode.US.value,
        payment_account_id=payout_account_id,
        is_default=is_default,
        token=uuid.uuid4(),
    )

    payout_method = await payout_method_repo.create_payout_method(data)
    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=payout_method.dict()
    )
    assert payout_method.id, "payout method is created, assigned an ID"
    return payout_method


async def prepare_payout_card_list(
    payout_method_repo: PayoutMethodRepository,
    payout_card_repo: PayoutCardRepository,
    payout_account_id: int,
    count: int = 5,
):
    payout_card_list: List[PayoutCard] = []
    for i in range(0, count):
        # create a payout_method
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo,
            payout_account_id,
            is_default=True if (i + 1) == count else False,
        )

        data = PayoutCardCreate(
            id=payout_method.id,
            stripe_card_id=f"{payout_method.id}_card_test_payout_card{i}",
            last4="1234",
            brand="Bear Bank",
            exp_month=12,
            exp_year=23,
            fingerprint="fingerprint{}".format(i),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        payout_card = await payout_card_repo.create_payout_card(data)
        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=payout_card.dict()
        )
        assert payout_card.id, "payout card is created, assigned an ID"
        payout_card_list.insert(0, payout_card)
    return payout_card_list


async def prepare_payout_method_list(
    payout_method_repo: PayoutMethodRepository, payout_account_id: int, count: int = 5
):
    payout_method_list: List[PayoutMethod] = []
    for i in range(0, count):
        # create a payout_method
        data = PayoutMethodCreate(
            type=payout_models.PayoutExternalAccountType.CARD.value,
            currency=Currency.USD.value,
            country=CountryCode.US.value,
            payment_account_id=payout_account_id,
            is_default=False,
            token=uuid.uuid4(),
        )

        payout_method = await payout_method_repo.create_payout_method(data)
        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=payout_method.dict()
        )
        payout_method_list.insert(0, payout_method)
    return payout_method_list


async def prepare_and_insert_payment_account_edit_history(
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
    sma_id=1,
    payment_account_id=1,
    owner_type=None,
):
    data = PaymentAccountEditHistoryCreate(
        account_type=payout_models.AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
        account_id=sma_id,
        new_bank_name="new_bank_name",
        new_bank_last4="new_bank_last4",
        new_fingerprint="new_fingerprint",
        payment_account_id=payment_account_id,
        owner_type=owner_type,
        owner_id=None,
        old_bank_name="old_bank_name",
        old_bank_last4="old_bank_last4",
        old_fingerprint="old_fingerprint",
        login_as_user_id=None,
        user_id=None,
        device_id=None,
        ip=None,
    )
    created_record = await payment_account_edit_history_repo.record_bank_update(
        data=data
    )
    assert (
        created_record.id
    ), "payment account edit history record is created, assigned an ID"

    validate_expected_items_in_dict(
        expected=data.dict(skip_defaults=True), actual=created_record.dict()
    )
    return created_record


def mock_transfer() -> models.Transfer:
    mock_reversals = models.Transfer.Reversals(data=[], has_more=False, object="obj")
    mocked_transfer = models.Transfer(
        id=str(uuid.uuid4()),
        object="obj",
        amount=10,
        amount_reversed=0,
        balance_transaction="mock_balance_txn",
        created=datetime.utcnow(),
        currency="usd",
        description="description",
        destination="destination",
        destination_payment="destination_payment",
        livemode=True,
        metadata={},
        reversals=mock_reversals,
        reversed=False,
        source_transaction="source_transaction",
        source_type="source_type",
        transfer_group="transfer_group",
    )
    return mocked_transfer


def mock_payout(status="pending",) -> models.Payout:
    mocked_payout = models.Payout(
        id=str(uuid.uuid4()),
        object="obj",
        amount=10,
        arrival_date=datetime.utcnow(),
        automatic=False,
        balance_transaction="balance_transaction",
        created=datetime.utcnow(),
        currency="usd",
        description="description",
        destination="destination",
        failure_balance_transaction="failure_balance_transaction",
        failure_code="failure_code",
        failure_message="hey this is failed",
        livemode=True,
        metadata={},
        method="method",
        source_type="source_type",
        statement_descriptor="statement_descriptor",
        status=status,
        type="type",
    )
    return mocked_payout


def mock_balance() -> models.Balance:
    source_type = models.SourceTypes(bank_account=1, card=2)
    availables = models.Balance.Available(
        amount=20, currency="usd", source_types=source_type
    )
    connect_reserves = models.Balance.ConnectReserved(
        amount=20, currency="usd", source_types=source_type
    )
    pendings = models.Balance.Pending(
        amount=20, currency="usd", source_types=source_type
    )
    mocked_balance = models.Balance(
        object="obj",
        available=[availables],
        connect_reserved=[connect_reserves],
        livemode=True,
        pending=[pendings],
    )
    return mocked_balance


def mock_stripe_card() -> models.StripeCard:
    return models.StripeCard(
        id=str(uuid.uuid4()),
        account="ct_test_account_payment",
        object="card",
        address_city=None,
        address_country=None,
        address_line1=None,
        address_line1_check=None,
        address_line2=None,
        address_state=None,
        address_zip=None,
        address_zip_check=None,
        available_payout_methods=[],
        brand="Visa",
        country=CountryCode.US,
        currency=Currency.USD,
        customer=None,
        cvc_check=None,
        description="Visa Classic",
        dynamic_last4=None,
        exp_month=8,
        exp_year=2020,
        fingerprint="test_fingerprint",
        funding="credit",
        last4="4242",
        metadata={},
        name=None,
        tokenization_method=None,
    )


def mock_stripe_bank_account() -> models.StripeBankAccount:
    return models.StripeBankAccount(
        id=str(uuid.uuid4()),
        object="bank_account",
        account="ct_test_account_payment",
        account_holder_name=None,
        account_holder_type=None,
        bank_name="DoorDash Bank",
        country=CountryCode.US,
        currency=Currency.USD,
        customer=None,
        default_for_currency=True,
        fingerprint="test_fingerprint",
        last4="1234",
        metadata=None,
        routing_number=None,
        status=models.StripeBankAccount.BankAccountStatus.NEW,
    )


def mock_stripe_account(stripe_account_id: str = None) -> models.Account:
    return models.Account(
        id=stripe_account_id if stripe_account_id else "test_stripe_account_id",
        object="Account",
        business_type="individual",
        charges_enabled=True,
        country=CountryCode.US,
        default_currency=Currency.USD,
        company=None,
        individual=models.Person(
            id="person_test_verify_account",
            object="person",
            account=stripe_account_id,
            created=datetime.utcnow(),
            id_number_provided=False,
            ssn_last_4_provided=False,
            address=models.Address(
                city="Mountain View",
                country="US",
                line1="123 Castro St",
                line2="",
                postal_code="94041",
                state="CA",
            ),
            dob=models.DateOfBirth(day=1, month=4, year=1990),
            email=None,
            first_name="test",
            last_name="payout",
            id_number=None,
            phone=None,
            ssn_last_4=None,
            verification=None,
        ),
        details_submitted=False,
        email=None,
        created=datetime.utcnow(),
        payouts_enabled=False,
        type=CREATE_STRIPE_ACCOUNT_TYPE,
    )


def mock_updated_stripe_account(stripe_account_id: str = None) -> models.Account:
    return models.Account(
        id=stripe_account_id if stripe_account_id else "test_stripe_account_id",
        object="Account",
        business_type="individual",
        charges_enabled=True,
        country=CountryCode.US,
        default_currency=Currency.USD,
        company=None,
        individual=models.Person(
            id="person_test_verify_account",
            object="person",
            account=stripe_account_id,
            created=datetime.utcnow(),
            id_number_provided=False,
            ssn_last_4_provided=False,
            address=models.Address(
                city="Mountain View",
                country="US",
                line1="123 Castro St",
                line2="",
                postal_code="94041",
                state="CA",
            ),
            dob=models.DateOfBirth(day=5, month=5, year=1991),
            email=None,
            first_name="Frosty",
            last_name="Fish",
            id_number=None,
            phone=None,
            ssn_last_4=None,
            verification=None,
        ),
        details_submitted=False,
        email=None,
        created=datetime.utcnow(),
        payouts_enabled=False,
        type=CREATE_STRIPE_ACCOUNT_TYPE,
    )


def construct_stripe_error(code="error_code", error_type="error_type") -> StripeError:
    # code can be either StripeErrorCode or str if not given
    error = StripeError(
        json_body={"error": {"code": code, "message": "error_msg", "type": error_type}}
    )
    return error


def list_diff(list_before, list_after):
    diff = [item for item in list_after if item not in list_before]
    return diff
