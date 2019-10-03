from datetime import datetime, timezone
import uuid

import pytest

from app.commons.database.infra import DB
from app.ledger.core.types import MxScheduledLedgerIntervalType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.test_integration.utils import (
    prepare_mx_ledger,
    prepare_mx_scheduled_ledger,
)


class TestMxLedgerRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def mx_ledger_repository(self, ledger_paymentdb: DB) -> MxLedgerRepository:
        return MxLedgerRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_scheduled_ledger_repository(
        self, ledger_paymentdb: DB
    ) -> MxScheduledLedgerRepository:
        return MxScheduledLedgerRepository(database=ledger_paymentdb)

    async def test_insert_mx_scheduled_ledger_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        mx_scheduled_ledger_id = uuid.uuid4()
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 7, tzinfo=timezone.utc)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        mx_scheduled_ledger = await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        assert mx_scheduled_ledger.id == mx_scheduled_ledger_id
        assert mx_scheduled_ledger.payment_account_id == payment_account_id
        assert mx_scheduled_ledger.ledger_id == ledger_id
        assert mx_scheduled_ledger.interval_type == MxScheduledLedgerIntervalType.WEEKLY
        assert mx_scheduled_ledger.start_time == datetime(
            2019, 8, 5, 7, tzinfo=timezone.utc
        )
        assert mx_scheduled_ledger.end_time == datetime(
            2019, 8, 12, 7, tzinfo=timezone.utc
        )
