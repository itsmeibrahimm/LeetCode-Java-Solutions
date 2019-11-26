import random
import uuid

import pytest
from datetime import datetime, timedelta

import pytz

from app.payout.core.instant_payout.models import (
    InstantPayoutStatusType,
    InstantPayoutDailyLimitCheckStatuses,
)
from app.payout.repository.bankdb.model.payout import PayoutUpdate
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.test_integration.utils import prepare_and_insert_payout


class TestPayoutRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_create_payout(self, payout_repo: PayoutRepository):
        # prepare and insert payout, then validate
        await prepare_and_insert_payout(payout_repo=payout_repo)

    async def test_create_get_payout(self, payout_repo: PayoutRepository):
        # prepare and insert payout, then validate
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        assert payout == await payout_repo.get_payout_by_id(
            payout.id
        ), "retrieved payout matches"

    async def test_update_payout_by_id(self, payout_repo: PayoutRepository):
        # prepare and insert payout, then validate
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        assert payout == await payout_repo.get_payout_by_id(
            payout.id
        ), "retrieved payout matches"

        timestamp = datetime.utcnow()
        new_data = PayoutUpdate(status="OK")
        updated = await payout_repo.update_payout_by_id(payout.id, new_data)
        assert updated, "updated"
        assert updated.status == "OK", "updated correctly"
        assert updated.updated_at >= timestamp, "updated correctly"

    async def test_list_payout_by_payout_account_id(
        self, payout_repo: PayoutRepository
    ):
        # Prepare and insert payout with all statuses
        payout_account_id = random.randint(1, 2147483647)
        statuses = [
            InstantPayoutStatusType.NEW,
            InstantPayoutStatusType.PENDING,
            InstantPayoutStatusType.PAID,
            InstantPayoutStatusType.FAILED,
            InstantPayoutStatusType.ERROR,
        ]
        inserted_payouts = []
        for status in statuses:
            payout = await prepare_and_insert_payout(
                payout_repo=payout_repo,
                ide_key="instant-payout-" + str(uuid.uuid4()),
                payout_account_id=payout_account_id,
                status=status,
            )
            inserted_payouts.append(payout)

        # Sort inserted payout by payout id desc
        inserted_payouts.sort(key=lambda payout: payout.id, reverse=True)

        # List all payout by payout ids
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0
        )
        # retrieved payouts already sorted by payout id desc
        assert retrieved_payouts == inserted_payouts

        # List payouts by payout account id with limit 2
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0, limit=2
        )
        # Should only return first 2
        assert retrieved_payouts == inserted_payouts[:2]

        # List Payout by payout account id with limit 2 offset 2
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id, offset=2, limit=2
        )
        # Should only return last 2
        assert retrieved_payouts == inserted_payouts[2:4]

        # List payouts by statuses
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id,
            offset=0,
            statuses=[InstantPayoutStatusType.NEW],
        )
        inserted_new_payout = list(
            filter(
                lambda payout: payout.status == InstantPayoutStatusType.NEW,
                inserted_payouts,
            )
        )
        assert retrieved_payouts == inserted_new_payout

        # List payouts by status with offset
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id,
            offset=1,
            statuses=[InstantPayoutStatusType.PAID],
        )
        assert retrieved_payouts == []

        # List payouts by start_time
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0, start_time=datetime.utcnow()
        )
        assert retrieved_payouts == []

        # List payout by end_time
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0, end_time=datetime.utcnow()
        )
        assert retrieved_payouts == inserted_payouts

        # List payouts by all params
        retrieved_payouts = await payout_repo.list_payout_by_payout_account_id(
            payout_account_id=payout_account_id,
            offset=1,
            statuses=InstantPayoutDailyLimitCheckStatuses,
            start_time=datetime.utcnow() - timedelta(minutes=30),
            end_time=datetime.utcnow(),
            limit=2,
        )

        results = list(
            filter(
                lambda payout: payout.status in InstantPayoutDailyLimitCheckStatuses,
                inserted_payouts,
            )
        )
        results.sort(key=lambda payout: payout.id, reverse=True)
        assert retrieved_payouts == results[1:3]

    async def test_list_payout_in_new_status(self, payout_repo: PayoutRepository):
        # Prepare and insert payout with all statuses
        payout_account_id = random.randint(1, 2147483647)
        inserted_payout = await prepare_and_insert_payout(
            payout_repo=payout_repo,
            ide_key="instant-payout-" + str(uuid.uuid4()),
            payout_account_id=payout_account_id,
            status=InstantPayoutStatusType.NEW.value,
        )
        current_time = datetime.utcnow().replace(tzinfo=pytz.utc)
        all_in_new = await payout_repo.list_payout_in_new_status(end_time=current_time)
        assert inserted_payout in all_in_new

        new_time = current_time - timedelta(hours=2)
        all_in_new = await payout_repo.list_payout_in_new_status(end_time=new_time)
        assert inserted_payout not in all_in_new
