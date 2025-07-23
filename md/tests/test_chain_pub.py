from md.tests.test_chain_buffer import TestJson
from common.walrus_redis import WalrusManager
from common.dt_helper import DTHelper
from datetime import datetime
import json
import zlib
import time

StreamNamesLookupKey = "dev.daily.mdstreams.set.v1"
chain_streams = ['test_stream_1', 'test_stream_2']

wm = WalrusManager()
stream_hash = wm.get().Hash(StreamNamesLookupKey)
net_streams = []
for idx, chain_stream in enumerate(chain_streams):
    stream_hash.update({f"UL_{idx}" : chain_stream})
    net_streams.append(wm.get().Stream(chain_stream))

pub_dict = json.loads(TestJson)
for i in range(1, 100):
    for idx, net_stream in enumerate(net_streams):
        pub_dict['pubts'] = DTHelper.to_yyyy_mm_dd_hh_mm_ss(datetime.now())
        pub_dict['sequence'] = i
        bin_data = zlib.compress(json.dumps(pub_dict, default=str).encode('utf-8'))
        net_stream.add({'t': int(datetime.now().timestamp()), 'v': bin_data})
        print(f"Publishing to {StreamNamesLookupKey} -> {chain_streams[idx]} @ {pub_dict['pubts']} @ seq:{i}")
    time.sleep(0.1)
print("Writer finished!")
