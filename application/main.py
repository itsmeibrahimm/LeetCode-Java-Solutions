#!/usr/bin/python3

# standard library imports
import logging
import os
import sys

# related third party imports
from doordash_lib.runtime import Runtime
from flask import Flask
from ninox.interface.flask.secret_marker import NinoxLoader
from werkzeug.utils import find_modules, import_string

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("root")

runtime = Runtime(location="/srv/runtime/current", namespace="payment-service")


def create_app():
    app = Flask(__name__)

    environment = os.getenv("ENVIRONMENT", "").lower()
    if not environment:
        raise Exception("No ENVIRONMENT in env. Not Supported")

    # Configs should be in the "conf" folder, in files named after
    # the environment.
    #  The Class inside should be the environment name, capital-case
    app.config.from_object(
        f"application.conf.{environment}." f"{environment.capitalize()}"
    )

    app.ninox = None
    if app.config["NINOX_ENABLED"]:
        app.ninox = NinoxLoader(app=app, config_section=environment)

    app.logger.info(app.config)

    register_blueprints(app, module="application")
    register_cli(app)

    return app


def register_blueprints(
    app, module=None, blueprint_module="blueprints", blueprint_obj_name="bp"
):
    """Register all blueprint modules

    Reference: Armin Ronacher, "Flask for Fun and for Profit" PyBay 2016.
    """
    blueprint_path = (module or app.import_name) + "." + blueprint_module
    for name in find_modules(blueprint_path, True):
        mod = import_string(name)
        if hasattr(mod, blueprint_obj_name):
            app.register_blueprint(mod.bp)
    return None


def register_cli(app):
    @app.cli.command("version")
    def version_command():
        print("unknown")


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
