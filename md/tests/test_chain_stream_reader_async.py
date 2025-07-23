import json
import zlib
from common.walrus_redis import *
from common.dt_helper import DTHelper
from datetime import datetime
import asyncio
from redis import asyncio as aioredis

StreamNamesLookupKey = "prod.daily.mdstreams.set.v1"

def get_stream_dict():
    wm = WalrusManager()
    wm_db = wm.get()
    if wm_db.hash_exists(StreamNamesLookupKey):
        h = wm_db.Hash(StreamNamesLookupKey)
        stream_dict = {ul.decode(): stream_name.decode()
                       for (ul, stream_name) in h}
        return stream_dict
    return None


stream_dict = get_stream_dict()
if not stream_dict:
    print(f"Stream Names in key {StreamNamesLookupKey} not configured yet!")
    exit(1)
print(f"Will read from the following stream dict:")
print(stream_dict)

stream_names = list(stream_dict.values())

"""
async loop for continuous processing of single stream
"""
async def process_stream(idx, reader: AsyncRedisStreamReader):
    print(f"Ready to read stream {reader.get_name()} idx:{idx}")
    while True:
        bdata = await reader.read()
        if not bdata:
            await asyncio.sleep(0.3)
            print(f"reader timeout for {reader.get_name()}... no bdata yet!")
            continue
        ts = bdata[b't'].decode()
        obj = json.loads(zlib.decompress(bdata[b'v']))
        print(f"{reader.get_name()} : {ts} -> {obj['ul']}")
        await asyncio.sleep(0.01)

"""
print to show that event loop is not blocked
"""
async def print_waiting():
    msg = "* Async Waiting for messages..."
    msgs = [f"{msg}\\", f"{msg}|", f"{msg}/", f"{msg}-"]
    while True:
        for s in msgs:
            print(s, end="\r")
            await asyncio.sleep(0.4)
"""
Create reader tasks
"""
async def start_async_readers(redis : aioredis.Redis):
    readers = []
    for idx, wstream in enumerate(stream_names):
        readers.append(AsyncRedisStreamReader(
            redis=redis, 
            stream_name=wstream, 
            start_from=WReaderType.Latest))
    try:
        async with asyncio.TaskGroup() as task_group:
            for idx, reader in enumerate(readers):
                task_group.create_task(process_stream(idx, reader))
            task_group.create_task(print_waiting())

    except* TypeError as te:
        for errors in te.exceptions:
            print(errors)
    except* Exception as ex:
        print(ex.exceptions)

"""
async start
"""
async def start():
    redis = aioredis.Redis()
    print(f"Async Connection successfull! {await redis.ping()}")
    await start_async_readers(redis)
    await redis.aclose()

asyncio.run(start())
