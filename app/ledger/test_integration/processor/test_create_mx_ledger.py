import uuid
import pytest
import pytest_mock
from psycopg2._psycopg import DataError
from app.commons.database.infra import DB
from app.commons.types import Currency
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerCreationError,
)
from app.ledger.core.mx_ledger.processors.create_mx_ledger import (
    CreateMxLedger,
    CreateMxLedgerRequest,
)
from app.ledger.core.types import MxLedgerType, MxLedgerStateType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository


class TestCreateMxLedger:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def mx_transaction_repo(self, ledger_paymentdb: DB) -> MxTransactionRepository:
        return MxTransactionRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_ledger_repo(self, ledger_paymentdb: DB) -> MxLedgerRepository:
        return MxLedgerRepository(database=ledger_paymentdb)

    async def test_create_mx_ledger_success(
        self,
        mocker: pytest_mock.MockFixture,
        mx_transaction_repo: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        create_mx_ledger_op = CreateMxLedger(
            mx_transaction_repo=mx_transaction_repo,
            logger=mocker.Mock(),
            request=CreateMxLedgerRequest(
                payment_account_id=payment_account_id,
                currency=Currency.USD.value,
                balance=2000,
                type=MxLedgerType.MICRO_DEPOSIT.value,
            ),
        )
        mx_ledger = await create_mx_ledger_op._execute()

        assert mx_ledger is not None
        assert mx_ledger.currency == Currency.USD
        assert mx_ledger.balance == 2000
        assert mx_ledger.state == MxLedgerStateType.PROCESSING
        assert mx_ledger.type == MxLedgerType.MICRO_DEPOSIT
        # todo: get mx txn and assert here after we have GET api!

    async def test_create_mx_ledger_data_error_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        mx_transaction_repo: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        error = DataError("Test data error.")
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.create_ledger_and_insert_mx_transaction",
            side_effect=error,
        )
        with pytest.raises(MxLedgerCreationError) as e:
            create_mx_ledger_op = CreateMxLedger(
                mx_transaction_repo=mx_transaction_repo,
                logger=mocker.Mock(),
                request=CreateMxLedgerRequest(
                    payment_account_id=payment_account_id,
                    currency=Currency.USD.value,
                    balance=2000,
                    type=MxLedgerType.MICRO_DEPOSIT.value,
                ),
            )
            await create_mx_ledger_op._execute()

        # todo: add logic to confirm the creation would be rolled back when exception caught

        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_CREATE_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_CREATE_ERROR.value]
        )
