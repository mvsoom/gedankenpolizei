from queue import Empty, Queue
from threading import Lock
from time import time


class Slot(Queue):
    """A single-slot replacing queue"""

    def __init__(self):
        super().__init__(maxsize=1)
        self.lock = Lock()

    def put(self, item, **kwargs):
        with self.lock:
            if self.full():
                self.get_nowait()  # Remove the existing item
            super().put(item, **kwargs)

    def peek(self, block=True, timeout=None):
        """Return first item from queue without consuming it

        Code modified from Queue.get() -- see also https://stackoverflow.com/a/35578295/6783015
        """
        with self.not_empty:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time() + timeout
                while not self._qsize():
                    remaining = endtime - time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self.queue[0]
            return item

    def slumber(self, seconds):
        """Sleep until the queue is empty or wake up when an item is put"""
        try:
            self.peek(block=True, timeout=seconds)
        except Empty:
            pass


class BidirectionalSlot:
    """Enable "vertical" bidirectional Slot() communication from an upper thread to a lower thread"""

    def __init__(self):
        self.up = Slot()
        self.down = Slot()

    def put_upwards(self, item, **kwargs):
        self.up.put(item, **kwargs)

    def get_from_below(self, **kwargs):
        return self.up.get(**kwargs)

    def put_downwards(self, item, **kwargs):
        self.down.put(item, **kwargs)

    def get_from_above(self, **kwargs):
        return self.down.get(**kwargs)
