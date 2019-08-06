import asyncio
import os
from asyncio import wait_for, create_subprocess_exec
from typing import Optional

from app.commons.config.app_config import AppConfig
from app.commons.config.utils import init_app_config
from app.commons.context.app_context import create_app_context, AppContext

ENVIRONMENT_KEY = "ENVIRONMENT"


async def check_dependency(config: AppConfig) -> AppContext:
    return await create_app_context(config)


async def run_alembic_command(db_url, config_name):
    """
    Run command in subprocess.
    """
    # Create subprocess
    command = [
        "env",
        db_url,
        "alembic",
        "--config",
        "migrations/alembic.ini",
        "--name",
        config_name,
        "upgrade",
        "head",
    ]
    process = await create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    # Status
    print("Started, pid=%s", process.pid, flush=True)

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()
    print(stdout.decode().strip())
    print(stderr.decode().strip())

    # Progress
    if process.returncode == 0:
        print("Done, pid=%s", process.pid)
        return True
    else:
        print("Failed, pid=%s", process.pid)
        raise Exception("Failed executing the command to update DB schema")


async def update_test_db_schema(app_config: AppConfig):
    # Function to migrate the db schema to latest version by alembic
    # Only migrate PAYIN_MAINDB_URL and LEDGER_MAINDB_URL for now
    ledger_db_url = "LEDGER_MAINDB_URL={}".format(app_config.LEDGER_MAINDB_URL.value)
    await run_alembic_command(ledger_db_url, "ledger")

    payin_db_url = "PAYIN_MAINDB_URL={}".format(app_config.PAYIN_MAINDB_URL.value)
    await run_alembic_command(payin_db_url, "payin")


async def main():
    app_config = init_app_config()

    retries = 20
    interval_sec = 5.0
    timeout = 5
    last_error = None
    app_context: Optional[AppContext] = None
    for i in range(retries, 0, -1):
        try:
            app_context = await wait_for(check_dependency(app_config), timeout=timeout)
            break
        except asyncio.TimeoutError as e:
            print(str(e))
            last_error = e
        except Exception as e:
            print(str(e))
            last_error = e
        await asyncio.sleep(interval_sec)
    else:
        # too many tries
        raise Exception("Failed checking connection to dependencies") from last_error
    if app_context:
        await update_test_db_schema(app_config)
        await app_context.close()


if __name__ == "__main__":
    print("Waiting for dependencies until they are ready")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(f"Dependencies are ready for ENVIRONMENT={os.getenv(ENVIRONMENT_KEY)}")
