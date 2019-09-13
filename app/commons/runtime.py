from doordash_lib.runtime import Runtime
import os


def _get_runtime_namespace() -> str:
    # FIXME: better to define separate env var for runtime namespace through helm.
    return (
        "payment-service"
        if os.getenv("ENVIRONMENT", "local") == "prod"
        else "staging-payment-service"
    )


runtime = Runtime(namespace=_get_runtime_namespace(), location="/srv/runtime/current")
