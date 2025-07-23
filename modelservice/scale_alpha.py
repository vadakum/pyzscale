

from md.instrument_manager import InstrumentType
from modelservice.alpha_consts import SignalDirection
from md.scale_option_chain import ScaleOptionChain
from modelservice.smoothers import SmootherFactory, ISmoother
from modelservice.opt_agg import OptionAggregator
from modelservice.macd_tema import MacdTema
from enum import StrEnum
from dataclasses import dataclass, field
import logging

class SAKeys(StrEnum):
    SigMult = 'sigmult'
    Smoother = 'smoother'
    Enabled = 'enabled'

@dataclass
class ScaleSignal:
    is_valid: bool = False
    ulexts: str = ""
    dir: str = SignalDirection.NONE.value
    val: float = 0
    ulpx: float = 0
    smooth_ulpx: float = 0
    atm: float = 0
    cpx: float = 0
    ppx: float = 0
    tema : float = 0
    macd_value : float = 0
    macd_signal : float = 0
    macd_dir: str = SignalDirection.NONE.value

    def __repr__(self) -> str:
        return (f"isvalid:{self.is_valid}, val:{self.val}, dir:{self.dir}, "
                f"ulpx:{self.ulpx}, atm:{self.atm}, cpx:{self.cpx}, "
                f"ppx:{self.ppx}, "
                f"ulexts:{self.ulexts}")

class ScaleAlpha:
    """ Scale Alpha """
    def __init__(self, args: dict) -> None:
        self.args = args
        self.sig_mult = args[SAKeys.SigMult.value] if SAKeys.SigMult.value in args else 0.5

        self.ts_smoother = None
        self.ul_smoother = None
        self.opt_aggregator = None
        self.macd_tema = None

        smoother_args = args[SAKeys.Smoother.value]
        ts_smoother_args = smoother_args['TS']
        ul_smoother_args = smoother_args['UL']
        cp_smoother_args = smoother_args['CP']
        
        if ts_smoother_args['enabled']:
            self.ts_smoother = SmootherFactory.create(ts_smoother_args)
        if ul_smoother_args['enabled']:
            self.ul_smoother = SmootherFactory.create(ul_smoother_args)
        if cp_smoother_args['enabled']:
            self.opt_aggregator = OptionAggregator(cp_smoother_args)
        if 'MACD' in smoother_args:
            macd_args = smoother_args['MACD']
            if macd_args['enabled']:
                self.macd_tema = MacdTema(macd_args)


    """
    get_sampled_underlying
    """
    @staticmethod
    def get_sampled_value(smoother: ISmoother, px) -> tuple[bool, float]:
        if not smoother:
            return (True, px)
        smoother.add_sample(px)
        return (smoother.is_ready(), smoother.get_value())

    """
    Signal generator
    """
    def process_update(self, up: ScaleOptionChain) -> ScaleSignal:
        ts = up.get_ul_exch_ts()
        ul_price = up.get_ul_price()
        signal = ScaleSignal(is_valid=False, ulexts=ts, ulpx=ul_price)

        if self.opt_aggregator:
            self.opt_aggregator.add_sample(up)

        (_, sampled_ulpx) = ScaleAlpha.get_sampled_value(self.ul_smoother, ul_price)

        if self.macd_tema:
            macd_info = self.macd_tema.gen_signal(ul_price)
            signal.macd_value = macd_info.value
            signal.macd_signal = macd_info.signal
            signal.macd_dir = macd_info.dir

        (is_ts_ready, is_time_over) = ScaleAlpha.get_sampled_value(
            self.ts_smoother, 1)
        if not is_ts_ready:
            return signal

        if self.ts_smoother and is_time_over:
            self.ts_smoother.reset()

        atm = up.calculate_atm(sampled_ulpx)
        if self.opt_aggregator:
            (call_px, put_px) = self.opt_aggregator.get_opt_avg_ltp(atm)
        else:
            call_px = up.get_opt_ltp(atm, InstrumentType.CE)
            put_px = up.get_opt_ltp(atm, InstrumentType.PE)

        if sampled_ulpx <= 0 or call_px <= 0 or put_px <= 0:
            return signal

        signal.is_valid = True

        thold = up.get_opt_strike_gap() * self.sig_mult
        cmp_px = round(call_px - put_px, 1)
        if cmp_px > thold:
            if not self.macd_tema:
                signal.dir = SignalDirection.BUY.value
            else:
                 # Check tema signal
                 if signal.macd_dir == SignalDirection.BUY:
                    signal.dir = SignalDirection.BUY.value
        elif cmp_px < -thold:
            if not self.macd_tema:
                signal.dir = SignalDirection.SELL.value
            else:
                # Check tema signal
                if signal.macd_dir == SignalDirection.SELL:
                    signal.dir = SignalDirection.SELL.value

        signal.smooth_ulpx = round(sampled_ulpx, 1)
        signal.atm = atm
        signal.cpx = round(call_px, 1)
        signal.ppx = round(put_px, 1)
        signal.val = cmp_px
        return signal
        

