# -*- coding: utf-8 -*-
from flask import Blueprint

# create our blueprint :)
bp = Blueprint('health', __name__, url_prefix="/health")


@bp.route("/")
def health() -> str:
    return "OK"
