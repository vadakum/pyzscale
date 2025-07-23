

import json
import time
from datetime import datetime
from common.walrus_redis import WStreamReader, WalrusManager, WReaderType
from multiprocessing import Process
import os

StreamName = 'TEST_STREAM_PUB_SUB_1'
LateStartReaderSec = 5
ReaderType = WReaderType.Latest

def reader():
    wm = WalrusManager()
    reader = WStreamReader(wm, StreamName, ReaderType)
    time.sleep(LateStartReaderSec)
    print(f"--> Reader Process Started delayed={LateStartReaderSec} sec with pid: {os.getpid()}")
    while True:
        payload = reader.fetch_one_nb()
        if payload:
            data: bytes = payload[b'v']
            msg = data.decode('utf-8')
            print(f"Reader: {msg}")
            if msg == "STOP":
                break

def writer():
    wm = WalrusManager()
    stream = wm.get().Stream(StreamName)
    print(f"--> Starting writer with pid: {os.getpid()}")
    for i in range(1, 11):
        stream.add({'v': f"Hello World {i} !"})
        time.sleep(1)
    stream.add({'v': f"STOP"})
    print("Writer finished!")


if __name__ == '__main__':
    wm = WalrusManager()
    
    procs = [Process(target=reader), Process(target=writer)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
        
    wm.clear_stream(StreamName)        
    