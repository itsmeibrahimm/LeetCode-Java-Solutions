import asyncio
import os
from asyncio import wait_for

from app.commons.config.app_config import AppConfig
from app.commons.config.utils import init_app_config
from app.commons.context.app_context import create_app_context

ENVIRONMENT_KEY = "ENVIRONMENT"


async def check_dependency(config: AppConfig):
    await create_app_context(config)


async def main():
    app_config = init_app_config()

    retries = 20
    interval_sec = 5.0
    timeout = 5
    last_error = None
    for i in range(retries, 0, -1):
        try:
            await wait_for(check_dependency(app_config), timeout=timeout)
            break  # startup successful
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


if __name__ == "__main__":
    print("Waiting for dependencies until they are ready")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(f"Dependencies are ready for ENVIRONMENT={os.getenv(ENVIRONMENT_KEY)}")
