from datetime import datetime

from pytz import timezone

from app.commons.config.app_config import AppConfig
from app.commons.config.prod import create_app_config


def test_cron_trigger_config():
    prod_app_config: AppConfig = create_app_config()
    cron_trigger = prod_app_config.CAPTURE_CRON_TRIGGER
    pacific_tz = timezone("US/Pacific")
    # make sure pacific time 16:00, 17:00, 18:00 is not triggered
    all_day_hours = [i for i in range(0, 24)]
    black_list_hours = [16, 17, 18]
    last_triggered_hour = None
    for hour in all_day_hours:
        now = datetime.now(pacific_tz).replace(
            hour=hour, minute=0, second=0, microsecond=0
        )
        if hour in black_list_hours:
            next_trigger = cron_trigger.get_next_fire_time(last_triggered_hour, now)
            assert next_trigger != now
            assert next_trigger not in black_list_hours
        else:
            assert cron_trigger.get_next_fire_time(last_triggered_hour, now) == now
            last_triggered_hour = now
