

from kite_wrap.kite_connection import ClientConnection
from md.instrument_manager import InstrumentManager
from md.feed_process_manager import FeedProcessManager
from common.walrus_redis import WalrusManager

"""
Option Chain Specific Market Data processing
"""


class OCMarketData:
    def __init__(self,
                 conn: ClientConnection,
                 wm: WalrusManager,
                 inst_mgr: InstrumentManager,
                 oc_config_list: list[dict]) -> None:
        self.conn = conn
        self.inst_mgr = inst_mgr
        self.fpm = FeedProcessManager(conn=conn,
                                      wm=wm,
                                      inst_mgr=inst_mgr,
                                      oc_config_list=oc_config_list)

    def start(self):
        self.fpm.start()
