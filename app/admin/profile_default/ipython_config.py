# lines of code to run at IPython startup.
c = get_config()  # noqa
c.InteractiveShellApp.exec_lines = [
    "import asyncio",
    "from datetime import *",
    "from app.commons.context.logger import get_logger",
    "from app.commons.jobs.startup_util import init_worker_resources",
    '(app_config, app_context, stripe_pool) = init_worker_resources(pool_name="stripe")',
    'logger = get_logger("admin")',
]
