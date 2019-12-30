from datetime import timedelta
from typing import List

import pytest
from asynctest import patch, Mock
from doordash_python_stats.ddstats import DoorStatsProxyMultiServer

from app.commons.utils.testing import Stat
from app.payin.jobs.payin_jobs import EmitProblematicCaptureCount


@pytest.mark.asyncio
@patch(
    "app.payin.repository.cart_payment_repo.CartPaymentRepository.count_payment_intents_in_problematic_states",
    return_value=5,
)
async def test_emit_problematic_capture_count(
    mock_count_payment_intents_in_problematic_states,
    service_statsd_client: DoorStatsProxyMultiServer,
    get_mock_statsd_events,
):
    job_instance = EmitProblematicCaptureCount(
        app_context=Mock(),
        job_pool=Mock(),
        statsd_client=service_statsd_client,
        problematic_threshold=timedelta(days=2),
    )
    await job_instance.run()
    events: List[Stat] = get_mock_statsd_events()
    assert len(events) == 3
    stat = events[1]
    assert (
        stat.stat_name
        == "dd.pay.payment-service.payment-intent-problematic-state.count"
    )
    assert stat.stat_value == 5
    mock_count_payment_intents_in_problematic_states.assert_called_once()
