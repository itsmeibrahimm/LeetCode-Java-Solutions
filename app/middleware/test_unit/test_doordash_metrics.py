from app.middleware.doordash_metrics import normalize_path


def test_normalize_path():
    assert normalize_path("/api/v1/{id}") == "|api|v1|id"
