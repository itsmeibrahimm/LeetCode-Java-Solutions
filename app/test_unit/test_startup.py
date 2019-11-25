import os
import signal
import sys
from typing import List

import pexpect
import pytest
import requests
from fastapi import FastAPI
from psutil import Process

# Dummy app for testing
myapp = FastAPI()


@myapp.get("/")
async def ping():
    return "OK"


class TestStartup:
    TIMEOUT_SECONDS = 30.0
    EXPECTED_THREADS = 1

    def test_startup(self, unused_tcp_port: int):
        """
        Ensure that we only have a single Python thread in the main process (having other system threads is fine)

        Gunicorn forks worker processes after the code is loaded.
        With this model, it is NOT SAFE to spawn Python threads prior to forking, because we can encounter a GIL deadlock.
        Ensure that any ThreadPools are created in app startup handlers, which should be triggered post-fork
        (do not initialize thread pools as module import time).
        """
        gunicorn = pexpect.spawn(
            "gunicorn",
            [
                # run one worker with the main app to trigger the initialization code
                "--workers",
                "1",
                # ensure we use the uvicorn worker so the app init runs
                "--worker-class",
                "app.uvicorn_worker.UvicornWorker",
                # unused port
                "--bind",
                f"0.0.0.0:{unused_tcp_port}",
                # main app
                "app.main:app",
            ],
            # set char encoding for stdout output
            encoding="utf-8",
        )
        gunicorn.logfile = sys.stdout  # log to stdout
        workers: List[Process] = []
        try:
            # see https://github.com/benoitc/gunicorn/blob/f38f717539b1b7296720805b8ae3969c3509b9c1/gunicorn/arbiter.py#L583
            # gunicorn startup
            gunicorn.expect(["Started server process"], timeout=self.TIMEOUT_SECONDS)
            process = Process(gunicorn.pid)
            workers = process.children(True)
            print("worker pids: {}".format([w.pid for w in workers]))

            assert (
                process.num_threads() == self.EXPECTED_THREADS
            ), "master process does not have additional python threads"

            # properly clean up
            gunicorn.kill(signal.SIGINT)
            # gunicorn.expect(["Shutting down: Master"], timeout=self.TIMEOUT_SECONDS)
        except pexpect.TIMEOUT:
            pytest.fail(
                "gunicorn process may not have started correctly, could not find expected output"
            )
        except pexpect.EOF:
            pytest.fail("gunicorn exited early during init; check logs for details")
        finally:
            # force cleanup of master process and children
            gunicorn.kill(signal.SIGKILL)
            for worker in workers:
                worker.kill()
            gunicorn.close(force=True)

    @pytest.mark.timeout(TIMEOUT_SECONDS)
    def test_uvicorn_worker_max_requests(self, unused_tcp_port: int):

        """
        Ensure that max_requests and max_requests_jitter settings are wired
        into our own uvicorn worker instance through gunicorn
        """

        max_requests = 5
        max_requests_jitter = 1
        one_worker = 1
        server_url = f"0.0.0.0:{unused_tcp_port}"

        gunicorn = pexpect.spawn(
            "gunicorn",
            [
                # run one worker with the main app to trigger the initialization code
                "--workers",
                f"{one_worker}",
                # ensure we use the uvicorn worker so the app init runs
                "--worker-class",
                "app.uvicorn_worker.UvicornWorker",
                # unused port
                "--bind",
                f"{server_url}",
                "--max-requests",
                f"{max_requests}",
                "--max-requests-jitter",
                f"{max_requests_jitter}",
                # main app
                "app.test_unit.test_startup:myapp",
            ],
            # set char encoding for stdout output
            encoding="utf-8",
        )
        gunicorn.logfile = sys.stdout  # log to stdout
        workers: List[Process] = []

        try:
            # gunicorn startup, try to capture our own log line defined in app/uvicorn_worker.py

            # because of jitter, actual result max_requests can be within [max_request-jitter ... max_request+jitter]
            expected_max_requests = [
                max_requests + delta
                for delta in range(-max_requests_jitter, max_requests_jitter + 1)
            ]
            expected_log_lines = [
                f"\[UvicornWorker\] configure uvicorn worker limit_max_requests={expected_max_request}"
                for expected_max_request in expected_max_requests
            ]
            gunicorn.expect(expected_log_lines, timeout=self.TIMEOUT_SECONDS)

            # see https://github.com/benoitc/gunicorn/blob/f38f717539b1b7296720805b8ae3969c3509b9c1/gunicorn/arbiter.py#L583
            gunicorn.expect(["Started server process"], timeout=self.TIMEOUT_SECONDS)

            process = Process(gunicorn.pid)
            workers = process.children(True)
            assert len(workers) == one_worker, f"expect {one_worker} workers"
            worker = workers[0]
            print(f"worker pid: {worker.pid}")

            success_requests = 0
            while True:  # guarded by pytest.mark.timeout
                try:
                    requests.get(f"http://{server_url}/", timeout=1).close()
                    success_requests += 1
                except BaseException as e:
                    print(
                        f"{success_requests}th request failed! current worker pid={worker.pid} may be closed: {str(e)}"
                    )
                    break

            # see https://github.com/benoitc/gunicorn/blob/f38f717539b1b7296720805b8ae3969c3509b9c1/gunicorn/arbiter.py#L581
            # current worker should shut down
            gunicorn.expect(
                [f"Worker exiting \\(pid: {worker.pid}\\)"],
                timeout=self.TIMEOUT_SECONDS,  # noqa W605
            )

            # a new worker is coming up
            gunicorn.expect([f"Booting worker with pid"], timeout=self.TIMEOUT_SECONDS)

        except pexpect.TIMEOUT:
            pytest.fail(
                "gunicorn process may not have started correctly, could not find expected output"
            )
        except pexpect.EOF:
            pytest.fail("gunicorn exited early during init; check logs for details")
        finally:

            # force cleanup of master process and children
            gunicorn.kill(signal.SIGKILL)
            for worker in workers:
                if worker.is_running():
                    worker.kill()
            gunicorn.close(force=True)

    @pytest.mark.timeout(TIMEOUT_SECONDS)
    def test_uvicorn_worker_handle_sigabrt_gracefully(self, unused_tcp_port: int):

        """
        Ensure that max_requests and max_requests_jitter settings are wired
        into our own uvicorn worker instance through gunicorn
        """

        one_worker = 1
        server_url = f"0.0.0.0:{unused_tcp_port}"

        gunicorn = pexpect.spawn(
            "gunicorn",
            [
                # run one worker with the main app to trigger the initialization code
                "--workers",
                f"{one_worker}",
                # ensure we use the uvicorn worker so the app init runs
                "--worker-class",
                "app.uvicorn_worker.UvicornWorker",
                # unused port
                "--bind",
                f"{server_url}",
                # main app
                "app.test_unit.test_startup:myapp",
            ],
            # set char encoding for stdout output
            encoding="utf-8",
        )
        gunicorn.logfile = sys.stdout  # log to stdout
        workers: List[Process] = []
        try:
            # see https://github.com/benoitc/gunicorn/blob/f38f717539b1b7296720805b8ae3969c3509b9c1/gunicorn/arbiter.py#L583
            gunicorn.expect(["Started server process"], timeout=self.TIMEOUT_SECONDS)

            process = Process(gunicorn.pid)
            workers = process.children(True)
            assert len(workers) == one_worker, f"expect {one_worker} workers"
            worker = workers[0]
            print(f"worker pid: {worker.pid}")

            # send SIGABRT to worker process
            os.kill(worker.pid, signal.SIGABRT)

            gunicorn.expect(
                ["Shutting down"], timeout=self.TIMEOUT_SECONDS  # noqa W605
            )

            gunicorn.expect(
                ["Waiting for application shutdown."],
                timeout=self.TIMEOUT_SECONDS,  # noqa W605
            )

            # see https://github.com/benoitc/gunicorn/blob/f38f717539b1b7296720805b8ae3969c3509b9c1/gunicorn/arbiter.py#L581
            # current worker should shut down
            gunicorn.expect(
                [f"Worker exiting \\(pid: {worker.pid}\\)"],
                timeout=self.TIMEOUT_SECONDS,  # noqa W605
            )

            # a new worker is coming up
            gunicorn.expect([f"Booting worker with pid"], timeout=self.TIMEOUT_SECONDS)

        except pexpect.TIMEOUT:
            pytest.fail(
                "gunicorn process may not have started correctly, could not find expected output"
            )
        except pexpect.EOF:
            pytest.fail("gunicorn exited early during init; check logs for details")
        finally:

            # force cleanup of master process and children
            gunicorn.kill(signal.SIGKILL)
            for worker in workers:
                if worker.is_running():
                    worker.kill()
            gunicorn.close(force=True)
