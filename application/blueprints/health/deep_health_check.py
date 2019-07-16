from flask import current_app


def deep_health_check() -> bool:
    return _ping_secret()


def _ping_secret() -> bool:

    if "TEST_SECRET" in current_app.config:
        return True
    else:
        current_app.logger.warning("TEST_SECRET is not found in app config")
        return False
