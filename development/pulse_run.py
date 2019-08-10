import asyncio
import os
import requests
from time import sleep
from subprocess import Popen
from asyncio import create_subprocess_shell
from app.commons.config.utils import init_app_config

ENVIRONMENT_KEY = "ENVIRONMENT"


async def run_pulse_test():
    """
    Run local-server in subprocess and pulse env as well
    """
    # create payment service subprocess in background
    command_payment_service = "./development/start-local-server.sh -e testing -p 8000 &"
    process_payment = await create_subprocess_shell(
        command_payment_service,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Status
    print("Starting payment-service, pid=%s", process_payment.pid, flush=True)

    await process_payment.wait()
    # this is the number of retries to connect to payment-service. since the wait period is 1 min and wait duration is
    # 5 secs between every retry connect, the number is set to 12.
    retries = 12
    while True:
        retries -= 1
        try:
            requests.get(url="http://localhost:8000/health")
            command_runpulse = (
                'export SERVICE_NAME="payment-service"; '
                'export PULSE_VENV_PATH="/tmp/pulsevenv"; '
                "python3 -m venv ${PULSE_VENV_PATH}; "
                "source ${PULSE_VENV_PATH}/bin/activate; "
                'pip3 install --extra-index-url "https://pypi.fury.io/${FURY_TOKEN}/doordash/" --extra-index-url "https://${ARTIFACTORY_USERNAME/@/%40}:${ARTIFACTORY_PASSWORD}@ddartifacts.jfrog.io/ddartifacts/api/pypi/pypi-local/simple/" doordash-pulse; '
                "cd pulse; "
                "pulse --data-file=${PULSE_VENV_PATH}/infra/local/data.yaml --data-file=infra/local/data.yaml"
            )
            process_pulse = Popen(command_runpulse, shell=True, executable="/bin/bash")

            # Status
            print(
                "Started pulse-tests against payment-service, pid=%s",
                process_pulse.pid,
                flush=True,
            )
            process_pulse.communicate()
            process_pulse.kill()

            break
        except requests.exceptions.ConnectionError:
            sleep(5)  # waiting for 5 secs
            if retries < 0:
                print("Error connecting to Payment service from Pulse service")
                raise requests.exceptions.ConnectionError


async def main():
    init_app_config()
    await run_pulse_test()


if __name__ == "__main__":
    print("Waiting for dependencies until they are ready")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print(f"Dependencies are ready for ENVIRONMENT={os.getenv(ENVIRONMENT_KEY)}")
