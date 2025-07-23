
from abc import ABCMeta, abstractmethod
from common.walrus_redis import *
from md.instrument_manager import InstrumentManager
from scale_bot.mp_sighandler import MultiProcSignalHandler
from md.instrument_manager import InstrumentManager
from redis import asyncio as aioredis
from kiteconnect import KiteConnect

class IEngine(object, metaclass=ABCMeta):
    def __init__(self,
                 instr_mgr: InstrumentManager,
                 kconn: KiteConnect,
                 sig_handler: MultiProcSignalHandler
                 ) -> None:
        self.instr_mgr = instr_mgr
        self.sig_handler = sig_handler
        self.kconn = kconn
        self.aioredis = aioredis.Redis()
        self.wm = WalrusManager()

    def get_aio_redis(self):
        return self.aioredis
    
    def get_instrument_mgr(self) -> InstrumentManager:
        return self.instr_mgr

    def get_kconn(self) -> KiteConnect:
        return self.kconn

    def get_signal_handler(self) -> MultiProcSignalHandler:
        return self.sig_handler

    def get_wm(self) -> WalrusManager:
        return self.wm
    
    @abstractmethod
    def start(self):
        pass
        
