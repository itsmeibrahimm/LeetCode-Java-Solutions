import pytest
import json
from datetime import datetime

from app.commons.core.errors import DBIntegrityUniqueViolationError
from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestUpdate,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.test_integration.utils import (
    prepare_and_insert_payout,
    prepare_and_insert_stripe_payout_request,
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

    async def test_create_stripe_payout_request(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

    async def test_create_then_get_stripe_payout_request(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        stripe_payout_request = await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        assert (
            stripe_payout_request
            == await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                stripe_payout_request.payout_id
            )
        ), "retrieved stripe payout request matches"

        assert (
            stripe_payout_request
            == await stripe_payout_request_repo.get_stripe_payout_request_by_stripe_payout_id(
                stripe_payout_request.stripe_payout_id
            )
        ), "retrieved stripe payout request matches"

    async def test_create_thrown_unique_exception(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        # insert another stripe_payout_request with same payout id
        with pytest.raises(DBIntegrityUniqueViolationError) as e:
            await prepare_and_insert_stripe_payout_request(
                stripe_payout_request_repo=stripe_payout_request_repo,
                payout_id=payout.id,
            )
        err_msg = str(e.value)
        assert "unique violation error" in err_msg

    async def test_update_stripe_payout_request_by_id(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        stripe_payout_request = await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        timestamp = datetime.utcnow()
        new_data = StripePayoutRequestUpdate(
            status="OK", events=json.dumps([{"a": "b"}])
        )
        updated = await stripe_payout_request_repo.update_stripe_payout_request_by_id(
            stripe_payout_request.id, new_data
        )
        assert updated, "updated"
        assert updated.status == "OK", "updated correctly"
        assert updated.updated_at >= timestamp, "updated correctly"
