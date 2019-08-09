import asyncio
import os
from asyncio import create_subprocess_exec

from app.commons.config.app_config import AppConfig
from app.commons.config.utils import init_app_config

ENVIRONMENT_KEY = "ENVIRONMENT"


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
    # Only migrate PAYIN_PAYMENTDB and LEDGER_PAYMENTDB for now
    ledger_db_url = "LEDGER_PAYMENTDB_URL={}".format(
        app_config.LEDGER_PAYMENTDB_URL.value
    )
    await run_alembic_command(ledger_db_url, "ledger")

    payin_db_url = "PAYIN_PAYMENTDB_URL={}".format(app_config.PAYIN_PAYMENTDB_URL.value)
    await run_alembic_command(payin_db_url, "payin")


async def main():
    app_config = init_app_config()
    await update_test_db_schema(app_config)


if __name__ == "__main__":
    print("Updating schemas")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(f"Schemas are ready for ENVIRONMENT={os.getenv(ENVIRONMENT_KEY)}")
