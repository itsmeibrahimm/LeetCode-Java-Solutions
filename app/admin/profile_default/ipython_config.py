# lines of code to run at IPython startup.
c = get_config()  # noqa
c.InteractiveShellApp.exec_lines = [
    "import asyncio",
    "from datetime import *",
    "from app.commons.context.logger import get_logger",
    "from app.commons.jobs.startup_util import init_worker_resources",
    "from app.commons.config.utils import init_app_config_for_payin_cron",
    "from app.commons.config.secrets import ninox_readiness_check",
    "ninox_readiness_check()",
    "app_config=init_app_config_for_payin_cron()",
    '(app_context, stripe_pool)=init_worker_resources(app_config=app_config,pool_name="admin",pool_size=app_config.PAYIN_CRON_JOB_POOL_DEFAULT_SIZE)',
    'logger = get_logger("admin")',
]
