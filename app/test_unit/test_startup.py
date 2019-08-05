import pytest
import pexpect
import sys
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
        child = pexpect.spawn(
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
        child.logfile = sys.stdout  # log to stdout
        try:
            # see https://github.com/benoitc/gunicorn/blob/f38f717539b1b7296720805b8ae3969c3509b9c1/gunicorn/arbiter.py#L583
            child.expect(["Booting worker with pid:"], timeout=self.TIMEOUT_SECONDS)
            process = Process(child.pid)
            assert (
                process.num_threads() == self.EXPECTED_THREADS
            ), "master process does not have additional python threads"
        except pexpect.TIMEOUT:
            pytest.fail(
                "gunicorn process may not have started correctly, could not find expected output"
            )
        except pexpect.EOF:
            pytest.fail("gunicorn exited early during init; check logs for details")
        finally:
            child.close(force=True)
