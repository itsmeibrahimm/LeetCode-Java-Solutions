# -*- coding: utf-8 -*-
from flask import Blueprint, Response

# create our blueprint :)
from .deep_health_check import deep_health_check

bp = Blueprint("health", __name__, url_prefix="/health")


@bp.route("/")
def health() -> str:
    return "OK"


@bp.route("/deep-ping")
def deep_ping() -> Response:
    """
    A temporary endpoint to check whether service dependencies are correctly connected and up.
    Should only be called by ad-hoc testing or pulse and will be removed once we have concrete e2e features implemented.
    :return: 200 when dependencies are ready / available.
    :return: 404 when dependencies are not ready yet.
    """
    if deep_health_check():
        return Response("OK", status=200)
    else:
        return Response("DEPENDENCIES NOT READY", status=404)
