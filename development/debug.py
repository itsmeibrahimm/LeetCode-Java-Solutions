import os


def bootstrap_debugger():
    """
    Utility to bootstrap debugger
    """
    import pydevd

    debug_port = int(os.getenv("DEBUG_PORT_NUMBER", 9001))
    debug_host = os.getenv("DEBUG_HOST", "127.0.0.1")
    print(
        "Attempting live remote debugging connection to {}:{}".format(
            debug_host, debug_port
        )
    )
    pydevd.settrace(
        debug_host,
        port=int(debug_port),
        stdoutToServer=True,
        stderrToServer=True,
        suspend=False,
    )
