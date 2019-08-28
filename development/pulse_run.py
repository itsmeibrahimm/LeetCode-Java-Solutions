import asyncio
from asyncio import create_subprocess_shell
from os import unlink
import requests
from subprocess import Popen
import sys
from time import sleep
from tempfile import NamedTemporaryFile


async def run_pulse_test():
    """
    Run local-server in subprocess and pulse env as well
    """
    # create payment service subprocess in background
    temp_output = NamedTemporaryFile(delete=False)
    try:
        requests.get(url="http://localhost:8082/health")
        print(
            "payment-service is running before already, no need to spawn up a new one"
        )
    except requests.exceptions.ConnectionError:
        print("Starting a new local-server for payment-service")
        command_payment_service = (
            "./development/start-local-server.sh -e testing -p 8082 &"
        )
        process_payment = await create_subprocess_shell(
            command_payment_service, stdout=temp_output, stderr=asyncio.subprocess.PIPE
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
            requests.get(url="http://localhost:8082/health")
            command_runpulse = (
                'export SERVICE_NAME="payment-service"; '
                'export PULSE_VENV_PATH="/tmp/pulsevenv"; '
                "python3 -m venv ${PULSE_VENV_PATH}; "
                "source ${PULSE_VENV_PATH}/bin/activate; "
                'pip3 install --extra-index-url "https://pypi.fury.io/${FURY_TOKEN}/doordash/" --extra-index-url "https://${ARTIFACTORY_USERNAME/@/%40}:${ARTIFACTORY_PASSWORD}@ddartifacts.jfrog.io/ddartifacts/api/pypi/pypi-local/simple/" doordash-pulse; '
                "cd pulse; "
                "pip3 install -r requirements.txt; "
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
            print("Pulse test execution completed")
            exit_status = process_pulse.returncode
            process_pulse.kill()

            temp_output.close()
            unlink(temp_output.name)

            print("exit_status is %s", exit_status)
            return exit_status
        except requests.exceptions.ConnectionError:
            # waiting for 5 secs
            sleep(5)
            if retries < 0:
                temp_output.close()
                unlink(temp_output.name)
                print("Error connecting to Payment service from Pulse service")
                raise requests.exceptions.ConnectionError


async def main():
    return await run_pulse_test()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    return_value = loop.run_until_complete(main())
    print("main return_value: %s", return_value)
    sys.exit(return_value)
