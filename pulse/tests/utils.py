import logging
import os
import time
import subprocess
import importlib
from urllib.parse import unquote

SERVICE_URI = os.getenv("SERVICE_URI")

logger = logging.getLogger(__name__)


def current_time_ms():
    return time.time() * 1000


def decorate_api_call(func):
    def echo_func(*args, **kwargs):
        if "_return_http_data_only" not in kwargs:
            kwargs["_return_http_data_only"] = False

        if "_preload_content" not in kwargs:
            kwargs["_preload_content"] = True

        if "_request_timeout" not in kwargs:
            kwargs["_request_timeout"] = 10  # seconds

        logger.info(f"Calling [{func.__name__}] with arguments={kwargs}")

        start = current_time_ms()
        request_id = None
        try:
            result = func(*args, **kwargs)
            elapsed = current_time_ms() - start
            request_id = (
                result[2].get("x-payment-request-id", None)
                if len(result) >= 2
                else None
            )
            logger.info(f"RequestId={request_id} Execution completed in={elapsed}ms")
            return result
        except Exception:
            elapsed = current_time_ms() - start
            logger.info(f"RequestId={request_id} Failed in={elapsed}ms")
            raise

    return echo_func


def reload_pkg_version(pkg_dist_name, pkg_module_name, to_version):
    """
    To support testing multiple client versions
    We can potentially have many different client versions out in prod, and in pulse tests, we should cover them all
    This helper function will try to reload specific pkg (client) version in runtime, and use it for subsequent testing
    NOTE: it does not roll back version automatically, so make sure roll back manually if needed

    Example:
        p = reload_pkg_version('payout-v1-client', 'payout_v1_client', '0.0.8')
        print(p.__version__)  # now its 0.0.8
        p = reload_pkg_version('payout-v1-client', 'payout_v1_client', '0.0.9')
        print(p.__version__)  # now its 0.0.9

    :param pkg_dist_name:
    :param pkg_module_name:
    :param to_version:
    :return:
    """

    def install(package, version):
        artifactory_user = unquote(os.environ["ARTIFACTORY_USERNAME"])
        artifactory_pw = os.environ["ARTIFACTORY_PASSWORD"]

        subprocess.call(
            [
                "pip3",
                "install",
                f"{package}=={version}",
                "--force-reinstall",
                "--extra-index-url",
                f"https://{artifactory_user}:{artifactory_pw}@ddartifacts.jfrog.io/ddartifacts/api/pypi/pypi-local/simple/",
            ]
        )

    def uninstall(package):
        subprocess.call(["pip3", "uninstall", "--yes", package])

    assert to_version, "please specify version"
    logger.info(
        f"Switching {pkg_dist_name}, {pkg_module_name} to version {to_version}..."
    )
    try:
        curr_pkg = importlib.import_module(pkg_module_name)
    except ModuleNotFoundError:
        install(pkg_dist_name, to_version)
        curr_pkg = importlib.import_module(pkg_module_name)

    if curr_pkg.__version__ != to_version:
        uninstall(pkg_dist_name)
        install(pkg_dist_name, to_version)
        importlib.reload(curr_pkg)

    assert curr_pkg.__version__ == to_version, f"switched to version {to_version}"
    return curr_pkg
