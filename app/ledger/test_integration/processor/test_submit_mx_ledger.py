from app.commons.database.infra import DB
import uuid
from uuid import UUID
from datetime import datetime

import pytest
import pytest_mock
from asynctest import patch
from psycopg2._psycopg import DataError, OperationalError
from psycopg2.errorcodes import LOCK_NOT_AVAILABLE

from app.ledger.core.data_types import GetMxScheduledLedgerByAccountInput
from app.ledger.core.data_types import GetMxLedgerByIdInput
from app.ledger.core.exceptions import (
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerSubmissionError,
)
from app.ledger.core.mx_ledger.processors.submit_mx_ledger import (
    SubmitMxLedger,
    SubmitMxLedgerRequest,
)
from app.ledger.core.types import MxLedgerStateType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.ledger.test_integration.utils import (
    prepare_mx_ledger,
    prepare_mx_scheduled_ledger,
)


class TestSubmitMxLedger:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_transaction_repo: MxTransactionRepository,
    ):
        self.mx_transaction_repo = mx_transaction_repo
        self.mx_ledger_repository = mx_ledger_repository
        self.mocker = mocker

    @pytest.fixture
    def mx_transaction_repo(self, ledger_paymentdb: DB) -> MxTransactionRepository:
        return MxTransactionRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_ledger_repository(self, ledger_paymentdb: DB) -> MxLedgerRepository:
        return MxLedgerRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_scheduled_ledger_repository(
        self, ledger_paymentdb: DB
    ) -> MxScheduledLedgerRepository:
        return MxScheduledLedgerRepository(database=ledger_paymentdb)

    def _construct_submit_ledger_request(self, mx_ledger_id: UUID):
        request = SubmitMxLedger(
            mx_ledger_repo=self.mx_ledger_repository,
            mx_transaction_repo=self.mx_transaction_repo,
            logger=self.mocker.Mock(),
            request=SubmitMxLedgerRequest(mx_ledger_id=mx_ledger_id),
        )
        return request

    async def test_submit_ledger_not_found_raise_exception(self):
        submit_ledger_op = self._construct_submit_ledger_request(
            mx_ledger_id=uuid.uuid4()
        )
        with pytest.raises(MxLedgerReadError) as e:
            await submit_ledger_op._execute()
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_NOT_FOUND
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_NOT_FOUND.value]
        )

    async def test_submit_ledger_invalid_state_raise_exception(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        # prepare an open ledger
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)
        submit_ledger_op = self._construct_submit_ledger_request(mx_ledger_id=ledger_id)

        with pytest.raises(MxLedgerInvalidProcessStateError) as e:
            await submit_ledger_op._execute()
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE
        assert (
            e.value.error_message
            == ledger_error_message_maps[
                LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
            ]
        )

    async def test_submit_positive_balance_mx_ledger_success(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)
        submit_ledger_op = self._construct_submit_ledger_request(mx_ledger_id=ledger_id)
        mx_ledger = await submit_ledger_op._execute()

        assert mx_ledger
        assert mx_ledger.state == MxLedgerStateType.SUBMITTED
        assert mx_ledger.submitted_at is not None

    async def test_submit_zero_balance_mx_ledger_success(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=0,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        submit_ledger_op = self._construct_submit_ledger_request(mx_ledger_id=ledger_id)
        mx_ledger = await submit_ledger_op._execute()
        assert mx_ledger
        assert mx_ledger.id == ledger_id
        assert mx_ledger.state == MxLedgerStateType.PAID
        assert mx_ledger.finalized_at == mx_ledger.updated_at
        assert mx_ledger.amount_paid == 0
        assert mx_ledger.balance == 0

    @patch(
        "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.rollover_negative_balanced_ledger"
    )
    async def test_submit_negative_balance_retry_exceed_attempt_raise_exception(
        self, mock_submit_ledger, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        # todo: maybe need to fix this later
        class SubOE(OperationalError):
            pgcode = LOCK_NOT_AVAILABLE

        error = SubOE("Test lock not available error")
        mock_submit_ledger.side_effect = error
        submit_ledger_op = self._construct_submit_ledger_request(mx_ledger_id=ledger_id)
        with pytest.raises(MxLedgerSubmissionError) as e:
            await submit_ledger_op._execute()
        assert (
            e.value.error_code
            == LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR
        )
        assert (
            e.value.error_message
            == ledger_error_message_maps[
                LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
            ]
        )

    async def test_submit_negative_balance_data_error_raise_exception(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        error = DataError("Test data error.")
        self.mocker.patch(
            "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.rollover_negative_balanced_ledger",
            side_effect=error,
        )
        submit_ledger_op = self._construct_submit_ledger_request(
            mx_ledger_id=mx_ledger_id
        )
        with pytest.raises(MxLedgerSubmissionError) as e:
            await submit_ledger_op._execute()
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR.value]
        )

    async def test_submit_negative_balance_mx_ledger_to_open_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        # prepare pair of open ledger/scheduled_ledger
        open_ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        # when inserting txn for negative balance rollover, we use utcnow() as routing_key
        # this will cause the routing_key will always late than end_time of the found scheduled_ledger
        # so we use utcnow() when preparing scheduled_ledger to make sure we can fulfill the testing scenario
        # it might be flaky if we rollover negative balance between the switch of two periods, which is of low possibility
        routing_key = datetime.utcnow()
        open_mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=open_ledger_id,
            payment_account_id=payment_account_id,
            balance=2000,
        )
        await mx_ledger_repository.insert_mx_ledger(open_mx_ledger_to_insert)
        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=open_ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )
        submit_ledger_op = self._construct_submit_ledger_request(mx_ledger_id=ledger_id)
        rolled_ledger = await submit_ledger_op._execute()
        assert rolled_ledger
        assert rolled_ledger.id == ledger_id
        assert rolled_ledger.state == MxLedgerStateType.ROLLED
        assert rolled_ledger.finalized_at == rolled_ledger.updated_at
        assert rolled_ledger.amount_paid == 0
        assert rolled_ledger.balance == -1500
        assert rolled_ledger.rolled_to_ledger_id == open_ledger_id

        # retrieve and check the updated open ledger
        retrieve_ledger_request = GetMxLedgerByIdInput(id=open_ledger_id)
        updated_open_ledger = await mx_ledger_repository.get_ledger_by_id(
            retrieve_ledger_request
        )
        assert updated_open_ledger
        assert updated_open_ledger.state == MxLedgerStateType.OPEN
        assert updated_open_ledger.balance == 500
        assert updated_open_ledger.amount_paid is None

    async def test_submit_negative_balance_mx_ledger_to_new_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repo: MxTransactionRepository,
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        # retrieve and check the updated open ledger
        request = GetMxScheduledLedgerByAccountInput(
            payment_account_id=payment_account_id
        )
        async with mx_transaction_repo._database.master().connection() as connection:
            retrieved_scheduled_ledger = await mx_transaction_repo.get_open_mx_scheduled_ledger_for_payment_account_id(
                request, connection
            )
        assert retrieved_scheduled_ledger is None
        submit_ledger_op = self._construct_submit_ledger_request(mx_ledger_id=ledger_id)
        rolled_ledger = await submit_ledger_op._execute()
        assert rolled_ledger
        assert rolled_ledger.id == ledger_id
        assert rolled_ledger.state == MxLedgerStateType.ROLLED
        assert rolled_ledger.finalized_at == rolled_ledger.updated_at
        assert rolled_ledger.amount_paid == 0
        assert rolled_ledger.balance == -1500

        async with mx_transaction_repo._database.master().connection() as db_connection:
            # retrieve and check the updated open ledger
            retrieved_scheduled_ledger = await mx_transaction_repo.get_open_mx_scheduled_ledger_for_payment_account_id(
                request, db_connection
            )
        assert retrieved_scheduled_ledger
        retrieve_ledger_request = GetMxLedgerByIdInput(
            id=retrieved_scheduled_ledger.ledger_id
        )
        updated_open_ledger = await mx_ledger_repository.get_ledger_by_id(
            retrieve_ledger_request
        )

        assert updated_open_ledger
        assert updated_open_ledger.state == MxLedgerStateType.OPEN
        assert updated_open_ledger.balance == -1500
        assert updated_open_ledger.amount_paid is None
