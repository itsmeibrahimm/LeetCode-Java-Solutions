# -*- coding: utf-8 -*-

from flask import Blueprint, request

from application.blueprints.root.compute import compute_random_inclusive

bp = Blueprint('root', __name__, url_prefix='/')


@bp.route("/")
def hello_world() -> str:
    return "Hello, World!"


@bp.route("/random-inclusive", methods=["POST"])
def random_inclusive() -> str:
    # ideally here one would use WTForms and
    # Flask-Inputs to validate the request params
    low: int = request.json.get("low", 1)
    high: int = request.json.get("high", 100)

    random_inclusive_retval: int = compute_random_inclusive(low, high)
    return f"Here you go: {random_inclusive_retval}"
