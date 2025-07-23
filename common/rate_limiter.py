
import time
import functools
import collections
import threading
import asyncio

"""
Sync Rate limiter - Blocking
"""
class RateLimiter:
    def __init__(self, max_calls, period=1.0):
        if period <= 0:
            raise ValueError('Rate limiting period should be > 0')
        if max_calls <= 0:
            raise ValueError('Rate limiting number of calls should be > 0')
        self.calls = collections.deque(maxlen=max_calls)
        self.period = period
        self.max_calls = max_calls
        self._lock = threading.Lock()
        self._alock = None

    """
    decorator support
    """
    def __call__(self, f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            with self:
                return f(*args, **kwargs)
        return wrapped

    """
    context manager support
    """
    def __enter__(self):
        with self._lock:
            if len(self.calls) == self.max_calls:
                wait = self.period - (time.time() - self.calls[0])
                if wait > 0:
                    print('--> sync ratelimiter wait', round(wait, 4))
                    time.sleep(wait)
            self.calls.append(time.time())
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

"""
AsyncRateLimiter
"""
class AsyncRateLimiter(RateLimiter):

    def _init_async_lock(self):
        with self._lock:
            if self._alock is None:
                self._alock = asyncio.Lock()

    """
    async decorator support
    """
    def __call__(self, f):
        @functools.wraps(f)
        async def wrapped(*args, **kwargs):
            async with self: # async context manager
                return await f(*args, **kwargs)
        return wrapped

    """
    async context manager support
    """
    async def __aenter__(self):
        if self._alock is None:
            self._init_async_lock()

        async with self._alock:
            if len(self.calls) == self.max_calls:
                wait = self.period - (time.time() - self.calls[0])
                if wait > 0:
                    #print('==> async ratelimiter wait', round(wait, 4))
                    await asyncio.sleep(wait)
            self.calls.append(time.time())
            return self

    async def __aexit__(self, *args):
        pass