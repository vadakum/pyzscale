

import logging
from md.sub_unsub_const import SubUnsubKeys
from kite_wrap.websock_client import WebsocketClient, WebsockConfig
from kiteconnect import KiteTicker
import multiprocessing
import queue
import os

class FeedContainer(multiprocessing.Process):
    def __init__(self,
                 tick_q: multiprocessing.Queue,
                 su_q: multiprocessing.Queue,
                 instrument_ids: list[int],
                 ws_config: WebsockConfig) -> None:

        super().__init__()
        self.tick_q = tick_q
        self.sub_q = su_q
        self.token_set = set(instrument_ids)
        self.log_q_full_error_once = True
        self.wsc = WebsocketClient(config=ws_config, handler=self)

    def run(self) -> None:
        logging.debug("Starting feed container...")
        self.wsc.start()  # Blocking call

    def on_connect(self, ws: KiteTicker, response):
        sub_list = list(self.token_set)
        ws.subscribe(sub_list)
        ws.set_mode(ws.MODE_FULL, sub_list)
        logging.debug(f"Initial ws subscription: {sub_list}")

    """
    on_ticks wsocket callback
    """

    def on_ticks(self, ws: KiteTicker, ticks):
        try:
            self.tick_q.put_nowait(ticks)
            logging.debug(f"-> PID {os.getpid()} received {len(ticks)} ticks")
        except queue.Full:
            if self.log_q_full_error_once:
                logging.error("Consumer seems slow ! messages will be lost")
                self.log_q_full_error_once = False

        sun = None
        try:
            sun = self.sub_q.get_nowait()
        except queue.Empty:
            pass
        if sun:
            sub_list = sun[SubUnsubKeys.Sub][SubUnsubKeys.InstIds]  
            sub_mode = sun[SubUnsubKeys.Sub][SubUnsubKeys.Mode]            
            unsub_list = sun[SubUnsubKeys.Unsub][SubUnsubKeys.InstIds]
            if unsub_list:
                ws.unsubscribe(unsub_list)
                logging.debug(f"Unsubscripton request sent: {unsub_list}")
            if sub_list:
                ws.subscribe(sub_list)
                ws.set_mode(sub_mode, sub_list)
                logging.debug(f"Subscription request sent: {sub_list}")

    def on_close(self, ws, code, reason):
        logging.error(f"Connection closed on close: {code} {reason}")

    def on_error(self, ws, code, reason):
        logging.error(f"Connection closed on error: {code} {reason}")

    def on_noreconnect(self, ws):
        logging.error("Reconnecting the websocket failed")

    def on_reconnect(self, ws, attempt_count):
        logging.debug(f"Reconnecting the websocket: {attempt_count}")
