import logging
from kiteconnect import KiteTicker
from dataclasses import dataclass

@dataclass
class WebsockConfig:
    api_key : str = ""
    access_token : str = ""

class WebsocketClient:
    def __init__(self, config : WebsockConfig, handler):
        self.ws = KiteTicker(config.api_key, config.access_token, debug=True)
        self.ws.on_connect = handler.on_connect
        self.ws.on_close = handler.on_close
        self.ws.on_error = handler.on_error
        self.ws.on_ticks = handler.on_ticks
        logging.debug("Created KiteTicker object...")
    
    def start(self):
        #logging.debug("Starting websocket connection!")
        self.ws.connect(threaded=False)
        
