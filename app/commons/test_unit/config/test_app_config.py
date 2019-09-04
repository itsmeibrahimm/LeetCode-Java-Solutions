from app.commons.config.app_config import StatsDConfig, ApiStatsDConfig


def test_statsd():
    config = StatsDConfig()
    assert config.PREFIX == "dd.pay.payment-service"

    api_stats_config = ApiStatsDConfig()
    assert (
        api_stats_config.PREFIX == "dd.response"
    ), "api stats go to dd.response instead of the payment-service"
