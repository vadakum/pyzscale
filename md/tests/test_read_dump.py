import zlib
import json
from common.bin_file_stream import BinFileStream

file_name = "/home/qoptrprod/pyzscale/dumps/20240319/CHAIN_MIDCPNIFTY_I_20240319.dat"
# reading and copying
read_stream = BinFileStream(file_name, "rb")
rec_read = 0
while True:
    tsbytes = read_stream.read()
    if not tsbytes:
        break
    payload = read_stream.read()
    if not payload:
        break
    localts = int(tsbytes)
    msg_obj = json.loads(zlib.decompress(payload))
    print(f"pubts:{msg_obj['pubts']}, ts:{localts} {msg_obj['ul']}")
    rec_read += 1
    if rec_read == 1024:
        print(msg_obj)
        break
read_stream.close()
print(f"records read = {rec_read}")

