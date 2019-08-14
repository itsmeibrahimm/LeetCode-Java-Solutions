import pytest
from datetime import datetime

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.payout import PayoutCreate
from app.payout.repository.bankdb.payout import PayoutRepository


class TestPayoutRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    async def test_create_get_payout(self, payout_repo: PayoutRepository):
        ts_utc = datetime.utcnow()
        data = PayoutCreate(
            amount=1000,
            payment_account_id=123,
            status="failed",
            currency="USD",
            fee=199,
            type="instant",
            created_at=ts_utc,
            updated_at=ts_utc,
            idempotency_key="payout-idempotency-key-001",
            payout_method_id=1,
            transaction_ids=[1, 2, 3],
            token="payout-test-token",
            fee_transaction_id=10,
            error=None,
        )

        created = await payout_repo.create_payout(data)
        assert created.id, "payout is created, assigned an ID"

        assert created == await payout_repo.get_payout_by_id(
            created.id
        ), "retrieved payout matches"
