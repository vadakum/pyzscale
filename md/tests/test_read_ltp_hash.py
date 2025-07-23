from common.walrus_redis import *
from md.md_consts import MDLtpLookup

wdb = WalrusManager().get()
if not wdb.hash_exists(MDLtpLookup):
    print(f"LTP hash {MDLtpLookup} not created yet!")
    exit(1)

for k,v in wdb.Hash(MDLtpLookup):
    print(f"Key: {int(k)} => Value: {float(v)}")

