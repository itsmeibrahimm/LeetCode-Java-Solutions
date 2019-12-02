import pytest
import json
from datetime import datetime

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

    async def test_get_stripe_payout_request_by_payout_id(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        stripe_payout_request_1 = await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        assert (
            stripe_payout_request_1
            == await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                payout.id
            )
        ), "retrieved first stripe payout request matches"

        # Insert another stripe_payout_request with the same payout id
        stripe_payout_request_2 = await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        # when retrieve stripe_payout_request by payout_id, should return stripe_payout_request_2
        assert (
            await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
                payout.id
            )
            == stripe_payout_request_2
        )

    async def test_list_stripe_payout_requests_by_payout_ids(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        inserted_payout_ids = []
        for i in range(3):
            payout = await prepare_and_insert_payout(payout_repo)
            inserted_payout_ids.append(payout.id)

        # prepare stripe_payout_request
        payout_ids = inserted_payout_ids + [inserted_payout_ids[0]] * 3
        inserted_stripe_payout_requests = []
        for payout_id in payout_ids:
            stripe_payout_request_i = await prepare_and_insert_stripe_payout_request(
                stripe_payout_request_repo=stripe_payout_request_repo,
                payout_id=payout_id,
            )
            inserted_stripe_payout_requests.append(stripe_payout_request_i)

        # retrieve all stripe payout requests, already sorted by id desc
        retrieved_stripe_payout_requests = await stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids(
            payout_ids=inserted_payout_ids
        )
        assert len(retrieved_stripe_payout_requests) == len(
            inserted_stripe_payout_requests
        )
        assert retrieved_stripe_payout_requests == sorted(
            inserted_stripe_payout_requests,
            key=lambda stripe_payout_request: -stripe_payout_request.id,
        )

        # retrieve stripe payout request for inserted_payout_ids[0]
        retrieved_stripe_payout_requests = await stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids(
            payout_ids=[inserted_payout_ids[0]]
        )
        expected = [
            item
            for item in inserted_stripe_payout_requests
            if item.payout_id == inserted_payout_ids[0]
        ]
        assert retrieved_stripe_payout_requests == sorted(
            expected, key=lambda stripe_payout_request: -stripe_payout_request.id
        )

        # list none-existing payout id should return empty list
        assert (
            await stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids(
                payout_ids=[-1]
            )
            == []
        )
