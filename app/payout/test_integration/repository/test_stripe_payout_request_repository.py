import psycopg2
import pytest
import json
from datetime import datetime, timezone

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.payout import PayoutCreate
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
    StripePayoutRequestUpdate,
)
from app.payout.repository.bankdb.payout import PayoutRepository
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

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    async def test_create_then_get_stripe_payout_request(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        created = await payout_repo.create_payout(
            PayoutCreate(
                amount=1000,
                payment_account_id=123,
                status="failed",
                currency="USD",
                fee=199,
                type="instant",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                idempotency_key="payout-idempotency-key-001",
                payout_method_id=1,
                transaction_ids=[1, 2, 3],
                token="payout-test-token",
                fee_transaction_id=10,
                error=None,
            )
        )
        assert created.id, "payout is created, assigned an ID"

        sp_create = StripePayoutRequestCreate(
            payout_id=created.id,
            idempotency_key="stripe-payout-request-idempotency-key-001",
            payout_method_id=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="failed",
            stripe_payout_id=f"stripe_tr_xxx_{created.id}",
            stripe_account_id="cus_xxxx_1",
        )

        created_sp = await stripe_payout_request_repo.create_stripe_payout_request(
            sp_create
        )
        assert created_sp.id, "stripe payout request is created, assigned an ID"
        assert created_sp.stripe_payout_id, "stripe payout request has stripe payout id"

        assert (
            created_sp
            == await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                created_sp.payout_id
            )
        ), "retrieved stripe payout request matches"

        assert (
            created_sp
            == await stripe_payout_request_repo.get_stripe_payout_request_by_stripe_payout_id(
                created_sp.stripe_payout_id
            )
        ), "retrieved stripe payout request matches"

    async def test_create_thrown_unique_exception(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        payout = await payout_repo.create_payout(
            PayoutCreate(
                amount=1000,
                payment_account_id=123,
                status="failed",
                currency="USD",
                fee=199,
                type="instant",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                idempotency_key="payout-idempotency-key-001",
                payout_method_id=1,
                transaction_ids=[1, 2, 3],
                token="payout-test-token",
                fee_transaction_id=10,
                error=None,
            )
        )
        assert payout

        sp_create = StripePayoutRequestCreate(
            payout_id=payout.id,
            idempotency_key="stripe-payout-request-idempotency-key-001",
            payout_method_id=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="failed",
            stripe_payout_id="stripe_tr_xxx_1",
            stripe_account_id="cus_xxxx_1",
        )

        created_sp = await stripe_payout_request_repo.create_stripe_payout_request(
            sp_create
        )
        assert created_sp.id, "stripe payout request is created, assigned an ID"

        dup = StripePayoutRequestCreate(
            payout_id=payout.id,
            idempotency_key="stripe-payout-request-idempotency-key-002",
            payout_method_id=2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="failed",
            stripe_payout_id="stripe_tr_xxx_1",
            stripe_account_id="cus_xxxx_1",
        )

        with pytest.raises(psycopg2.IntegrityError) as e:
            await stripe_payout_request_repo.create_stripe_payout_request(dup)
        err_msg = str(e.value)

        assert (
            'duplicate key value violates unique constraint "stripe_payout_requests_payout_id_key"'
            in err_msg
        )

    async def test_update_stripe_payout_request_by_id(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        ts_utc = datetime.now(timezone.utc)

        payout = await payout_repo.create_payout(
            PayoutCreate(
                amount=1000,
                payment_account_id=123,
                status="failed",
                currency="USD",
                fee=199,
                type="instant",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                idempotency_key="payout-idempotency-key-001",
                payout_method_id=1,
                transaction_ids=[1, 2, 3],
                token="payout-test-token",
                fee_transaction_id=10,
                error=None,
            )
        )
        assert payout

        created = await stripe_payout_request_repo.create_stripe_payout_request(
            StripePayoutRequestCreate(
                payout_id=payout.id,
                idempotency_key="stripe-payout-request-idempotency-key-001",
                payout_method_id=1,
                created_at=ts_utc,
                updated_at=ts_utc,
                status="failed",
                stripe_payout_id="stripe_tr_xxx_1",
                stripe_account_id="cus_xxxx_1",
            )
        )
        assert created.id, "stripe payout request is created, assigned an ID"

        assert (
            created
            == await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                created.payout_id
            )
        ), "retrieved stripe payout request matches"

        timestamp = datetime.now(timezone.utc)

        new_data = StripePayoutRequestUpdate(
            status="OK", updated_at=timestamp, events=json.dumps([{"a": "b"}])
        )
        updated = await stripe_payout_request_repo.update_stripe_payout_request_by_id(
            created.id, new_data
        )
        assert updated, "updated"
        assert updated.status == "OK", "updated correctly"
        assert (
            updated.updated_at.timestamp() == timestamp.timestamp()
        ), "updated correctly"
