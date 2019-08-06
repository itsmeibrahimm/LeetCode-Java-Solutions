import uuid
from datetime import datetime

import pytest
import pytest_mock
from asyncpg import UniqueViolationError

from app.commons.context.app_context import AppContext
from app.commons.database.model import Database
from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxLedgerType,
    MxLedgerStateType,
)
from app.ledger.repository.mx_ledger_repository import (
    MxLedgerRepository,
    InsertMxLedgerInput,
)
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepository,
    InsertMxTransactionInput,
)


class TestMxLedgerRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_insert_mx_transaction_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: Database
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
        )
        repo = MxTransactionRepository(context=app_context)
        ledger_repo = MxLedgerRepository(context=app_context)
        mx_ledger_id = uuid.uuid4()
        mx_transaction_id = uuid.uuid4()
        ide_key = str(uuid.uuid4())
        mx_ledger_to_insert = InsertMxLedgerInput(
            id=mx_ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id="pay_act_test_id",
        )

        mx_transaction_to_insert = InsertMxTransactionInput(
            id=mx_transaction_id,
            payment_account_id="pay_act_test_id",
            amount=2000,
            currency=CurrencyType.USD.value,
            ledger_id=mx_ledger_id,
            idempotency_key=ide_key,
            target_type=MxTransactionType.MERCHANT_DELIVERY.value,
            routing_key=datetime.utcnow(),
        )
        await ledger_repo.insert_mx_ledger(mx_ledger_to_insert)
        mx_transaction = await repo.insert_mx_transaction(mx_transaction_to_insert)
        assert mx_transaction.id == mx_transaction_id
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.ledger_id == mx_ledger_id
        assert mx_transaction.amount == 2000
        assert mx_transaction.payment_account_id == "pay_act_test_id"
        assert mx_transaction.idempotency_key == ide_key

    async def test_insert_mx_transaction_raise_exception(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: Database
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
        )
        repo = MxTransactionRepository(context=app_context)
        ledger_repo = MxLedgerRepository(context=app_context)
        mx_ledger_id = uuid.uuid4()
        mx_transaction_id = uuid.uuid4()
        ide_key = str(uuid.uuid4())
        mx_ledger_to_insert = InsertMxLedgerInput(
            id=mx_ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id="pay_act_test_id",
        )

        mx_transaction_to_insert = InsertMxTransactionInput(
            id=mx_transaction_id,
            payment_account_id="pay_act_test_id",
            amount=2000,
            currency=CurrencyType.USD.value,
            ledger_id=mx_ledger_id,
            idempotency_key=ide_key,
            target_type=MxTransactionType.MERCHANT_DELIVERY.value,
            routing_key=datetime.utcnow(),
        )
        await ledger_repo.insert_mx_ledger(mx_ledger_to_insert)
        await repo.insert_mx_transaction(mx_transaction_to_insert)

        with pytest.raises(UniqueViolationError):
            await repo.insert_mx_transaction(mx_transaction_to_insert)
