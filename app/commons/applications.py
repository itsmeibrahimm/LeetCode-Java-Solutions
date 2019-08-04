from fastapi import FastAPI

__all__ = ["FastAPI"]


def monkeypatch_fastapi_router():
    from fastapi import applications
    from app.commons import routing

    # override FastAPI's routing imports to use our own router classes
    applications.routing = routing


monkeypatch_fastapi_router()
