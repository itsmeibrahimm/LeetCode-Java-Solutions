import pytest
import asyncio
from pytest_mock import MockFixture
from app.commons.instrumentation.monitor import MonitoringManager


@pytest.mark.asyncio
async def test_manager_loop(mocker: MockFixture):
    mock_processor = mocker.Mock()
    mock_new_processor = mocker.Mock()
    manager = MonitoringManager(
        stats_client=mocker.Mock(), logger=mocker.Mock(), processors=[mock_processor]
    )
    assert manager.start(0.1), "monitoring started"
    assert not manager.start(1), "monitoring already started"

    await asyncio.sleep(0.25)
    assert manager.stop(), "monitoring stopped"
    assert mock_processor.call_count == 2, "processors are called every 0.1s"
    assert not manager.stop(), "monitoring already stopped"
    assert mock_new_processor.call_count == 0

    mock_processor.reset_mock()
    assert mock_processor.call_count == 0

    manager.add(mock_new_processor)

    assert manager.start(0.1, call_immediately=True), "monitoring restarted"
    await asyncio.sleep(0.25)
    assert manager.stop(), "monitoring stopped"
    assert mock_processor.call_count == 3, "can immediately call processors"
    assert mock_new_processor.call_count == 3
