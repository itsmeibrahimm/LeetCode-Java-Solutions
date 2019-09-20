from datetime import timedelta
from typing import List

import pytest
from asynctest import patch
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer

from app.commons.context.app_context import AppContext
from app.commons.utils.testing import Stat
from app.payin.jobs import emit_problematic_capture_count


@pytest.mark.asyncio
@patch(
    "app.payin.repository.cart_payment_repo.CartPaymentRepository.count_payment_intents_that_require_capture",
    return_value=5,
)
async def test_emit_problematic_capture_count(
    mock_count_payment_intents_that_require_capture,
    app_context: AppContext,
    service_statsd_client: DoorStatsProxyMultiServer,
    get_mock_statsd_events,
):
    await emit_problematic_capture_count(
        app_context=app_context,
        statsd_client=service_statsd_client,
        problematic_threshold=timedelta(days=2),
    )
    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 1
    stat = events[0]
    assert stat.stat_name == "dd.pay.payment-service.capture.problematic_count"
    assert stat.stat_value == 5
    mock_count_payment_intents_that_require_capture.assert_called_once()
