import pytest
import pytest_mock
import pydantic
from uuid import uuid4
import json

from app.commons.database.infra import DB
from app.payout.core.transaction.processors.create_transaction import (
    CreateTransactionRequest,
    CreateTransaction,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import prepare_and_insert_payment_account


class TestCreateTransaction:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    async def test_create_transaction(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        create_transaction_req = CreateTransactionRequest(
            amount=10,
            amount_paid=0,
            payment_account_id=payout_account.id,
            idempotency_key=f"test_create_transaction_{uuid4()}_{payout_account.id}",
            target_id=1,
            target_type="test_type",
            currency="usd",
        )

        create_transaction_op = CreateTransaction(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=create_transaction_req,
        )

        transaction_created = await create_transaction_op._execute()
        assert transaction_created.id, "transaction created by processor"
        assert (
            transaction_created.amount == create_transaction_req.amount
        ), "transaction amount ok"
        assert (
            transaction_created.amount_paid == create_transaction_req.amount_paid
        ), "transaction amount_paid ok"
        assert (
            transaction_created.payout_account_id
            == create_transaction_req.payment_account_id
        ), "payment account id ok"
        assert (
            transaction_created.idempotency_key
            == create_transaction_req.idempotency_key
        ), "transaction idempotency key ok"
        assert (
            transaction_created.target_type == create_transaction_req.target_type
        ), "transaction target_type ok"
        assert (
            transaction_created.target_id == create_transaction_req.target_id
        ), "transaction target_id ok"
        assert (
            transaction_created.currency == create_transaction_req.currency
        ), "transaction currency ok"

    async def test_create_transaction_required_param(self,):
        with pytest.raises(pydantic.ValidationError) as e:
            CreateTransactionRequest()

        actual_required_fields = json.loads(e.value.json())
        actual_required_fields.sort(key=lambda r: r["loc"])
        expected_required_fields = [
            {"loc": ["amount"], "msg": "field required", "type": "value_error.missing"},
            {
                "loc": ["target_type"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["target_id"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["payment_account_id"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["idempotency_key"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["currency"],
                "msg": "field required",
                "type": "value_error.missing",
            },
        ]
        expected_required_fields.sort(key=lambda r: r["loc"])
        assert actual_required_fields == expected_required_fields
