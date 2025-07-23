

from modelservice.smoothers import SmootherFactory
from modelservice.alpha_consts import SignalDirection
from dataclasses import dataclass

@dataclass
class MacdInfo:
    value : float = 0
    signal : float = 0
    dir : str = "NONE"


class MacdTema:
    def __init__(self, args) -> None:
        self.short_dur = int(args['dfast'])
        self.long_dur = int(args['dslow'])
        self.signal_dur = int(args['dsig'])
        
        self.short_tema = SmootherFactory.create({'type' : 'TEMA' , 'timeperiod' : self.short_dur})
        self.long_tema = SmootherFactory.create({'type' : 'TEMA' , 'timeperiod' : self.long_dur})
        self.signal_tema = SmootherFactory.create({'type' : 'TEMA' , 'timeperiod' : self.signal_dur})

        self.prev_diff = 0 # Optimization over None
        self.dir_zone = SignalDirection.NONE

    def gen_signal(self, sample: float) -> MacdInfo:
        self.short_tema.add_sample(sample)
        self.long_tema.add_sample(sample)
        #
        # MACD = EMA{short} - EMA{long}
        # MACD < 0 when short drops below long
        # MACD > 0 when short raises above upper
        #
        macd = self.short_tema.get_value() - self.long_tema.get_value()
        # signal
        self.signal_tema.add_sample(macd)
        signal = self.signal_tema.get_value()
        curr_diff = macd - signal
        # The MACD line crossing above the signal line is 
        # an indication to purchase #the security
        # while a cross below the signal lines indicates a selling opportunity
        if self.prev_diff < 0 and curr_diff > 0:
            self.dir_zone = SignalDirection.BUY
        if self.prev_diff > 0 and curr_diff < 0:
            self.dir_zone = SignalDirection.SELL
        self.prev_diff = curr_diff
        return MacdInfo(value=macd, signal=signal, dir=self.dir_zone.value)
