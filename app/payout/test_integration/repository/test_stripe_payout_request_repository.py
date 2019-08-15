import pytest
from datetime import datetime
from asyncpg import UniqueViolationError

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)


class TestPayoutRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def stripe_payout_request_repo(
        self, payout_bankdb: DB
    ) -> StripePayoutRequestRepository:
        return StripePayoutRequestRepository(database=payout_bankdb)

    async def test_create_then_get_stripe_payout_request(
        self, stripe_payout_request_repo: StripePayoutRequestRepository
    ):
        ts_utc = datetime.utcnow()
        data = StripePayoutRequestCreate(
            payout_id=123,
            idempotency_key="stripe-payout-request-idempotency-key-001",
            payout_method_id=1,
            created_at=ts_utc,
            updated_at=ts_utc,
            status="failed",
            stripe_payout_id="stripe_tr_xxx_1",
            stripe_account_id="cus_xxxx_1",
        )

        created = await stripe_payout_request_repo.create_stripe_payout_request(data)
        assert created.id, "stripe payout request is created, assigned an ID"

        assert (
            created
            == await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                created.payout_id
            )
        ), "retrieved stripe payout request matches"

    async def test_create_thrown_unique_exception(
        self, stripe_payout_request_repo: StripePayoutRequestRepository
    ):
        ts_utc = datetime.utcnow()
        data = StripePayoutRequestCreate(
            payout_id=123,
            idempotency_key="stripe-payout-request-idempotency-key-001",
            payout_method_id=1,
            created_at=ts_utc,
            updated_at=ts_utc,
            status="failed",
            stripe_payout_id="stripe_tr_xxx_1",
            stripe_account_id="cus_xxxx_1",
        )

        created = await stripe_payout_request_repo.create_stripe_payout_request(data)
        assert created.id, "stripe payout request is created, assigned an ID"

        dup = StripePayoutRequestCreate(
            payout_id=123,
            idempotency_key="stripe-payout-request-idempotency-key-002",
            payout_method_id=2,
            created_at=ts_utc,
            updated_at=ts_utc,
            status="failed",
            stripe_payout_id="stripe_tr_xxx_1",
            stripe_account_id="cus_xxxx_1",
        )

        with pytest.raises(UniqueViolationError) as e:
            await stripe_payout_request_repo.create_stripe_payout_request(dup)
        err_msg = str(e.value)

        assert (
            'duplicate key value violates unique constraint "stripe_payout_requests_payout_id_key"'
            in err_msg
        )
