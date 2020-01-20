import dataclasses
from datetime import datetime

from pytz import timezone

from app.commons.config.app_config import AppConfig
from app.commons.config.prod import create_app_config
from app.commons.config.utils import init_app_config_for_web


def test_cron_trigger_config():
    prod_app_config: AppConfig = create_app_config()
    cron_trigger = prod_app_config.CAPTURE_CRON_TRIGGER
    pacific_tz = timezone("US/Pacific")
    # make sure pacific time 16:00, 17:00, 18:00 is not triggered
    all_day_hours = [i for i in range(0, 24)]
    all_hour_minutes = [i for i in range(0, 59)]
    eligible_minutes = [0, 15, 30, 45]
    black_list_hours = [16, 17, 18]
    last_triggered_hour = None
    for hour in all_day_hours:
        for minute in all_hour_minutes:
            now = datetime.now(pacific_tz).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            next_trigger = cron_trigger.get_next_fire_time(last_triggered_hour, now)
            if hour in black_list_hours:
                assert next_trigger != now
            elif minute in eligible_minutes:
                assert next_trigger == now
                last_triggered_hour = now
            else:
                assert next_trigger != now


def test_delete_payer_cron_trigger_config():
    prod_app_config: AppConfig = create_app_config()
    cron_trigger = prod_app_config.DELETE_PAYER_CRON_TRIGGER
    pacific_tz = timezone("US/Pacific")
    # make sure pacific time 16:00, 17:00, 18:00 is not triggered
    all_day_hours = [i for i in range(0, 24)]
    all_hour_minutes = [i for i in range(0, 59)]
    eligible_minutes = [0]
    black_list_hours = [16, 17, 18]
    last_triggered_hour = None
    for hour in all_day_hours:
        for minute in all_hour_minutes:
            now = datetime.now(pacific_tz).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            next_trigger = cron_trigger.get_next_fire_time(last_triggered_hour, now)
            if hour in black_list_hours:
                assert next_trigger != now
            elif minute in eligible_minutes:
                assert next_trigger == now
                last_triggered_hour = now
            else:
                assert next_trigger != now


def test_appconfig_copy_override():
    # test dataclasses.replace actually works for override appconfig object
    web_config = init_app_config_for_web()
    updated_config = dataclasses.replace(
        web_config, STRIPE_MAX_WORKERS=web_config.STRIPE_MAX_WORKERS + 1
    )
    assert updated_config.STRIPE_MAX_WORKERS == web_config.STRIPE_MAX_WORKERS + 1
    assert web_config != updated_config
    assert web_config == dataclasses.replace(
        updated_config, STRIPE_MAX_WORKERS=web_config.STRIPE_MAX_WORKERS
    )
