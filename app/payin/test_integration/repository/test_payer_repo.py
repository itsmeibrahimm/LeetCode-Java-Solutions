from datetime import datetime
from uuid import uuid4

import pytest
from pytz import timezone

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType
from app.payin.repository.payer_repo import (
    PayerRepository,
    InsertPayerInput,
    GetPayerByIdInput,
)


class TestPayerRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_payer_timestamp_timezone(self, payer_repository: PayerRepository):
        created_at = datetime.now(timezone("Europe/Amsterdam"))
        insert_payer_input = InsertPayerInput(
            id=uuid4(),
            payer_type=PayerType.STORE,
            country=CountryCode.US,
            created_at=created_at,
        )
        payer = await payer_repository.insert_payer(insert_payer_input)
        get_payer = await payer_repository.get_payer_by_id(
            GetPayerByIdInput(id=payer.id)
        )

        assert payer is not None
        assert get_payer is not None
        assert payer == get_payer
        assert get_payer.created_at is not None
        assert created_at.timestamp() == get_payer.created_at.timestamp()
