import json
import zlib
from common.walrus_redis import *
from common.dt_helper import DTHelper
from datetime import datetime

StreamNamesLookupKey = "prod.daily.mdstreams.set.v1"

def get_stream_dict(wm : WalrusManager):
    wm_db = wm.get()
    if wm_db.hash_exists(StreamNamesLookupKey):
        h = wm_db.Hash(StreamNamesLookupKey)
        stream_dict = {ul.decode() : stream_name.decode() for (ul, stream_name) in h }
        return stream_dict
    return None

wm = WalrusManager()
stream_dict = get_stream_dict(wm)
if not stream_dict:
    print(f"Stream Names in key {StreamNamesLookupKey} not configured yet!")
    exit(1)
print(f"Configured daily stream dict:")
print(stream_dict)

stream_names = list(stream_dict.values())

net_streams : list[WStreamReader] = []
for stream_name in stream_names:
    net_streams.append(WStreamReader(wm, stream_name, WReaderType.Begin))

while True:
    for idx, wstream in enumerate(net_streams):
        payload = wstream.fetch_one_nb()
        if payload:
            last_stream_id = wstream.get_last_id().decode()
            localts = payload[b't'].decode()
            data : bytes = payload[b'v']
            obj = json.loads(zlib.decompress(data))

            exts = int(datetime.fromisoformat(obj['ul']['exts']).timestamp())
            
            curr_epoch = int(datetime.now().timestamp())
            exch_lag = curr_epoch - exts
            pub_lag = curr_epoch - int(localts)
            
            pub_ts = DTHelper.to_yyyy_mm_dd_hh_mm_ss(datetime.fromtimestamp(obj['pubts']))
            print(f"=> Stream Name: {stream_names[idx]} | "
                  f"last_stream_id: {last_stream_id} | "
                  f"lag: exch:{exch_lag}, pub:{pub_lag} | " 
                  f"pubts:{pub_ts} | "                  
                  f"size:{int(len(data) / 1024)} kb")
            #print(f"=== {obj['chain']}")

