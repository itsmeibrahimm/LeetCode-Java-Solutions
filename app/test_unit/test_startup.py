import pytest
import pexpect
import sys
import signal
from typing import List
from psutil import Process


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
                "uvicorn.workers.UvicornWorker",
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
