from common.walrus_redis import WalrusManager
from dataclasses_json import dataclass_json
from dataclasses import dataclass
import json

SET_KEY = "TEST_SET_1"
HASH_KEY = "TEST_HASH_1"
LIST_KEY = "TEST_LIST_1"
"""
Walrus Set
"""
def set_add():
    wm = WalrusManager()
    wdb = wm.get()
    s = wdb.Set(SET_KEY)
    s.add("BANKNIFTY") #Adding first element creates the set, hash_exists will work if one element is added 
    s.add("NIFTY")
    s = wdb.Set(SET_KEY) # i.e recreating Set is not a problem

def set_get():
    wm = WalrusManager()
    wdb = wm.get()
    if wdb.hash_exists(SET_KEY):
        s = wdb.Set(SET_KEY)
        v =[v.decode() for v in s]
        print(f"set : fetched key {v}")
    else:
        print(f"{SET_KEY} does not exist")

def del_set_key():
    WalrusManager().get().delete(SET_KEY)

set_add()
set_get()
del_set_key()

"""
Walrus Hashes
"""
@dataclass_json
@dataclass
class OrderInfo:
    order_id : str = ""
    message : str = ""

def hash_add():
    wm = WalrusManager()
    wdb = wm.get()
    h = wdb.Hash(HASH_KEY)
    h.update({"BANKNIFTY_I" : "CHAIN_BANKNIFTY_I_20240328"})
    h.update({"NIFTY_I" : "CHAIN_NIFTY_I_20240328"})
    h = wdb.Hash(HASH_KEY) # i.e recreating Set is not a problem    
    h.update({
              1234.11 : 10001, 
              'composite' : json.dumps({'aa' : 101.99})
              })
    h.update({'orderid123' : json.dumps(None)})

    key = "orderid-json"
    oi = OrderInfo(key, "dataclass json")
    h.update({key : oi.to_json()})
    

def hash_get():
    wm = WalrusManager()
    wdb = wm.get()
    # iteration of key values
    if wdb.hash_exists(HASH_KEY):
        h = wdb.Hash(HASH_KEY)
        for k, v in h:
            print(f"hash : fetched key: {k.decode()} {type(k.decode())}, value: {v.decode()}")
    else:
        print(f"{HASH_KEY} does not exist")
    # lookup test for decimal key and composite value
    fkey = 1234.11        
    print(f"hash reading float key: {fkey}")
    bval = h.get(fkey)
    if bval:
        print(f"Key {fkey} found")
        val = float(bval)
        print(f"value is: {val} => of type: {type(val)}")
    else:
        print(f"key {fkey} not found!")

    fkey = 'composite'        
    print(f"hash reading composite (json) value for key: {fkey}")
    bval = h.get(fkey)
    val = json.loads(bval)
    print(f"value is: {val} => of type: {type(val)}")
    # lookup test for string key with None value, set value later
    print("lookup test for string key with None value, set value later")
    key = "orderid123"
    bval = h.get(key)
    if bval:
        val = json.loads(bval)
        print(f"value for key {key} is {val}, type is {type(val)}")
    else:
        print(f"value for key {key} not available")

    print("dataclass json deserial example")
    key = "orderid-json"
    bval = h.get(key)
    if bval:
        print(f"key {key} found!")
        oi = OrderInfo.from_json(bval)
        print(f"Deserial using dataclass_json = {oi}, {type(oi)}")

    bval = h.get(key)
    print(f"-Before Delete all keys: {wdb.hkeys(HASH_KEY)}")
    print(f"-Deleting key {key} of hash:{HASH_KEY}")
    h.__delitem__(key)
    print(f"-After Delete all keys: {wdb.hkeys(HASH_KEY)}")

    wdb.delete(HASH_KEY)
    

print("===== hash test ====")
hash_add()    
hash_get()

"""
Walrus List
"""
def test_list():
    print(f"===Testing list with key{LIST_KEY}===")
    wdb = WalrusManager().get()
    l = wdb.List(LIST_KEY)
    for i in range(1, 4):
        info = {'order_id' : f"orderid{i}", "strat_id" : 1 }
        l.append(json.dumps(info))

    t = wdb.List(LIST_KEY)
    print([json.loads(str_info) for str_info in t.as_list(decode=True)])
    wdb.delete(LIST_KEY)

test_list()    


