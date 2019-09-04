from app.commons.config import local, prod


def test_api_stats_local():
    config = local.create_app_config()
    assert config.API_STATSD_CONFIG.PREFIX == "dd.response"


def test_api_stats_prod():
    config = prod.create_app_config()
    assert config.API_STATSD_CONFIG.PREFIX == "dd.response"
