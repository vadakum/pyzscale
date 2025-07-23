

import logging
import json
import sys
import time
from kite_wrap.kite_connection import ClientConnection
from common.log_helper import LogHelper

LogHelper.configure_logging(verbose=True)

with open("./.creds.user.json") as cred_file:
    creds = json.load(cred_file)
    logging.debug(f"Creds: {creds}")

try:
    kconn = ClientConnection(creds=creds).get()
except ValueError as ex:
    logging.exception(ex)
    sys.exit(1)    

for i in range(1, 10):
    logging.debug(f"User Profile: {kconn.profile()}")
    logging.debug(f"LTP {kconn.ltp(['NSE:NIFTY MID SELECT'])}")
    time.sleep(5)



