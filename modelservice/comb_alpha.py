

from md.instrument_manager import InstrumentType
from modelservice.alpha_consts import SignalDirection
from md.scale_option_chain import ScaleOptionChain
from modelservice.smoothers import SmootherFactory, ISmoother
from modelservice.opt_agg import OptionAggregator
from modelservice.macd_tema import MacdTema
from modelservice.supp_res import OptSuppRes

from dataclasses import dataclass, field
from enum import StrEnum
import logging


class CAKeys(StrEnum):
    SigMult = 'sigmult'
    Smoother = 'smoother'
    Enabled = 'enabled'


@dataclass
class CombSignal:
    """ 
    Here itm and otm are with respect to call
    We just want values one strike above atm and below atm
    """
    valid: bool = False
    ulexts: str = ""
    ulpx: float = 0
    atm: float = 0    
    scd: str = SignalDirection.NONE.value
    macd: str = SignalDirection.NONE.value
    supp_k: float = 0
    res_k: float = 0
    scv: float = 0
    cpx: float = 0
    ppx: float = 0
    macv: float = 0
    macs: float = 0
    supp_info: str = ""
    res_info: str = ""

class CombAlpha:
    """ Comb Alpha """

    def __init__(self, args: dict) -> None:
        self.args = args
        self.sig_mult = args[CAKeys.SigMult.value] if CAKeys.SigMult.value in args else 0.5

        self.ts_smoother = None
        self.ul_smoother = None
        self.opt_aggregator = None
        self.macd_ind = None

        smoother_args = args[CAKeys.Smoother.value]
        ul_smoother_args = smoother_args['UL']
        cp_smoother_args = smoother_args['CP']

        if ul_smoother_args['enabled']:
            self.ul_smoother = SmootherFactory.create(ul_smoother_args)
        if cp_smoother_args['enabled']:
            self.opt_aggregator = OptionAggregator(cp_smoother_args)
        if 'MACD' in smoother_args:
            macd_args = smoother_args['MACD']
            if macd_args['enabled']:
                self.macd_ind = MacdTema(macd_args)

    """
    get_sampled_value

    """
    @staticmethod
    def get_sampled_value(smoother: ISmoother, px) -> tuple[bool, float]:
        if not smoother:
            return (True, px)
        smoother.add_sample(px)
        return (smoother.is_ready(), smoother.get_value())

    """
    calc_scale_signal
    """
    def calc_scale_signal(self, 
                           up: ScaleOptionChain, 
                           call_px, 
                           put_px) -> tuple[str, float]:
        dir = SignalDirection.NONE.value
        thold = up.get_opt_strike_gap() * self.sig_mult
        sig_value = round(call_px - put_px, 1)
        if sig_value > thold:
            dir = SignalDirection.BUY.value
        elif sig_value < -thold:
            dir = SignalDirection.SELL.value
        return (dir, sig_value)

    """
    Signal generator
    """

    def process_update(self, up: ScaleOptionChain) -> CombSignal:
        ts : str = up.get_ul_exch_ts()
        tok = ts.split(' ')
        if len(tok) > 1:
            ts = tok[1]
        ul_price = up.get_ul_price()
        sig = CombSignal(valid=False, ulexts=ts, ulpx=int(ul_price))

        if self.opt_aggregator:
            self.opt_aggregator.add_sample(up)

        (_, sampled_ulpx) = CombAlpha.get_sampled_value(self.ul_smoother, ul_price)

        atm_strike = up.calculate_atm(sampled_ulpx)
        strike_gap = up.get_opt_strike_gap()
        if self.opt_aggregator:
            (call_px_atm, put_px_atm) = self.opt_aggregator.get_opt_avg_ltp(atm_strike)
        else:
            call_px_atm = up.get_opt_ltp(atm_strike, InstrumentType.CE)
            put_px_atm = up.get_opt_ltp(atm_strike, InstrumentType.PE)


        if sampled_ulpx <= 0 or call_px_atm <= 0 or put_px_atm <= 0:
            return sig

        sig.valid = True
        (sig.scd, sig.scv) = self.calc_scale_signal(up, call_px_atm, put_px_atm)

        sig.atm = atm_strike
        sig.cpx = round(call_px_atm)
        sig.ppx = round(put_px_atm)

        if self.macd_ind:
            macd_info = self.macd_ind.gen_signal(ul_price)
            sig.macv = round(macd_info.value, 2)
            sig.macs = round(macd_info.signal, 2)
            sig.macd = macd_info.dir

        #
        # Option chain resistance(call), support(put)
        #
        (res, supp) = OptSuppRes(up).process()
        sig.supp_k = supp.strike
        sig.supp_info = f"{supp.leader}-{supp.state}-{supp.h2k}"
        
        sig.res_k = res.strike
        sig.res_info = f"{res.leader}-{res.state}-{res.h2k}"
        
        return sig
