from asyncio import Semaphore
from asyncio.events import AbstractEventLoop
from typing import Optional


class ResizableSemaphore(Semaphore):
    def __init__(
        self, value: int = 1, *, loop: Optional[AbstractEventLoop] = None
    ) -> None:
        super().__init__(value, loop=loop)
        self._size = value

    def resize(self, target_size: int):
        """
        Resizes the size of the semaphore

        :param target_size:
        :return:
        """
        previous_size = self._size
        self._size = target_size
        self._value += target_size - previous_size  # type: ignore
        # if the size is now bigger, then more jobs can be handled
        # specifically "wake up" the semaphore to check jobs that were previously waiting
        if self._value > 0:  # type: ignore
            self._wake_up_next()  # type: ignore
