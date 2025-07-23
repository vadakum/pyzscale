
from typing import Union
from enum import StrEnum
from walrus import Database
from redis import Redis, StrictRedis
from redis import asyncio as aioredis

"""
WalrusManager
"""


class WalrusManager:
    def __init__(self) -> None:
        self.walrus = Database()

    def get(self) -> Database:
        return self.walrus

    def clear_stream(self, stream_name):
        self.walrus.Stream(stream_name).clear()


"""
RedisManager
For raw usages
"""


class RedisManager:
    def __init__(self) -> None:
        self.redis = StrictRedis()

    def get(self) -> Redis:
        return self.redis


"""
Walrus stream reader
"""


class WReaderType(StrEnum):
    Begin = "0"
    Latest = "$"


class WStreamReader:
    def __init__(self,
                 wm: WalrusManager,
                 stream_name,
                 start_from: WReaderType = WReaderType.Latest) -> None:
        self._stream_name = stream_name
        self._stream = wm.get().Stream(stream_name)
        self._last_id = start_from.value
        self.block = 0
        if start_from == WReaderType.Begin:
            self.block = None

    def name(self):
        return self._stream_name

    def get_last_id(self):
        return self._last_id

    '''
    fetch one with almost no blocking
    '''

    def fetch_one_nb(self) -> Union[bytes | None]:
        '''
        Note:
            - Minimum Block of 1 millisecond has to be given if we want to start reading
              `only` from `Latest` message
            - Reading from `Begin` doesn't require the block i.e we can set it to None,
              but keeping 1 ms minimal block keeps it compatible with `Begin` and `Latest`
            - Usage: 
             `while True:
                ### Don't sleep within while else block after may go out of sync
                payload = stream.fetch_one()
                if not payload:
                    break
              `      
        '''
        mx_list = self._stream.read(
            count=1, last_id=self._last_id, block=1)
        if mx_list:
            self._last_id, payload = mx_list[0]
            return payload
        return None


    '''
    fetch one with almost no blocking
    '''

    def fetch_one_block(self) -> Union[bytes | None]:
        '''
        Note:
            - Minimum Block of 1 millisecond has to be given if we want to start reading
              `only` from `Latest` message
            - Reading from `Begin` doesn't require the block i.e we can set it to None,
              but keeping 1 ms minimal block keeps it compatible with `Begin` and `Latest`
            - Usage: 
             `while True:
                ### Don't sleep within while else block after may go out of sync
                payload = stream.fetch_one()
                if not payload:
                    break
              `      
        '''
        mx_list = self._stream.read(
            count=1, last_id=self._last_id, block=self.block)
        if mx_list:
            self._last_id, payload = mx_list[0]
            return payload
        return None

"""
Async Redis Stream Reader
"""


class AsyncRedisStreamReader:
    def __init__(self,
                 redis: aioredis.Redis,
                 stream_name : str,
                 start_from: WReaderType) -> None:
        self.redis = redis
        self.stream_name = stream_name
        self.last_id = start_from.value

    def get_name(self):
        return self.stream_name

    def get_last_id(self):
        return self.last_id

    async def read(self, block=0):
        """
        https://redis.io/docs/latest/develop/data-types/streams/
        Note:
            - Minimum Block of 1000 millisecond has to be given if we want to start reading
              `only` from `Latest=$` message
            - Reading from `Begin=0` doesn't require the block i.e we can set `block=None`.
            - As this is async xread and won't block the main event loop, we can ask xread
              to block indefinitely by passing `block=0`
              hence we can create
              tasks for each stream with the following usage
             `while True:
                bdata = await reader.read()
                if not bdata:
                    await asyncio.sleep(0.2)
              `      
        """
        payload = await self.redis.xread(
            streams={self.stream_name: self.last_id},
            count=1,
            block=block)
        if payload:
            self.last_id, bdata = payload[0][1][0]
            return bdata
        return None
