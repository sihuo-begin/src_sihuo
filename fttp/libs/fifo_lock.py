import threading
import queue
from contextlib import contextmanager


class FIFOLock:
    def __init__(self):
        self._lock = threading.Lock()
        self._waiters = queue.Queue()
        self._waiters_mutex = threading.Lock()

    def acquire(self, blocking=True, timeout=None):
        if not blocking and timeout is not None:
            raise ValueError("can't specify a timeout for a non-blocking call")
        me = threading.Event()
        with self._waiters_mutex:
            self._waiters.put(me)
        got_lock = False
        if timeout is not None:
            import time

            start_time = time.monotonic()
        while True:
            with self._waiters_mutex:
                is_head = self._waiters.queue[0] is me
            if is_head and self._lock.acquire(blocking=False):
                got_lock = True
                break
            if not blocking:
                break
            if timeout is not None:
                import time

                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    break
                me.wait(timeout - elapsed if timeout - elapsed > 0 else 0)
            else:
                me.wait(0.05)
        with self._waiters_mutex:
            if not got_lock:
                try:
                    items = list(self._waiters.queue)
                    items.remove(me)
                    self._waiters = queue.Queue()
                    for it in items:
                        self._waiters.put(it)
                except ValueError:
                    pass
            else:
                self._waiters.get()
        return got_lock

    def release(self):
        self._lock.release()
        with self._waiters_mutex:
            if not self._waiters.empty():
                self._waiters.queue[0].set()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class LockManagerClass:
    """
    用于管理所有FIFO锁，全局唯一。
    LockManager(lock_name, timeout) 返回一个上下文支持的锁对象。
    """

    def __init__(self):
        self._locks = {}
        self._locks_mutex = threading.Lock()

    def __call__(self, lock_name, timeout=None):
        with self._locks_mutex:
            if lock_name not in self._locks:
                self._locks[lock_name] = FIFOLock()
            lock = self._locks[lock_name]
        return LockContext(lock, timeout)


class LockContext:
    def __init__(self, lock, timeout):
        self.lock = lock
        self.timeout = timeout

    def __enter__(self):
        ok = self.lock.acquire(timeout=self.timeout)
        if not ok:
            raise TimeoutError(f"Timeout waiting for FIFO lock")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()


LockManager = LockManagerClass()
