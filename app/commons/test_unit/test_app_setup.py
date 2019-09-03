from app.middleware.req_context import ReqContextMiddleware


def test_main_app_req_context_must_at_outer_most():
    """
    Unit test to make sure RequestContextMiddleware is always configured at outer most layer for main app.
    This is to make sure request specific contexts (e.g logger, req_id) are always properly set and can be used
    in exception handling chain
    """
    from app.main import app as main_app

    assert isinstance(main_app.error_middleware.app, ReqContextMiddleware)
