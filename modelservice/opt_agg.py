

from md.instrument_manager import InstrumentType
from md.scale_option_chain import ScaleOptionChain
from modelservice.smoothers import SmootherFactory
from typing import Deque
from collections import deque


class OptionAggregator:
    def __init__(self, args) -> None:
        self.qlen = int(args['timeperiod'])
        self.md_deque: Deque[ScaleOptionChain] = deque([], maxlen=self.qlen)
        
        self.call_smoother = SmootherFactory.create(args)        
        self.put_smoother = SmootherFactory.create(args)        

    def add_sample(self, up: ScaleOptionChain):
        self.md_deque.append(up)

    def get_opt_avg_ltp(self, strike) -> tuple[float, float]:
        """ return tuple[callpx, putpx]"""
        for up in self.md_deque:
            self.call_smoother.add_sample(up.get_opt_ltp(strike, InstrumentType.CE))
            self.put_smoother.add_sample(up.get_opt_ltp(strike, InstrumentType.PE))
        return (self.call_smoother.get_value(), self.put_smoother.get_value())
        
