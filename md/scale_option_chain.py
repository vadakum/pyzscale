

from md.option_chain_pub import TickKeys
from md.instrument_manager import InstrumentManager, InstrumentType, InstField

from datetime import datetime
from enum import StrEnum, auto
import pandas as pd
import numpy as np

class OptDfKeys(StrEnum):
    strike = auto()
    c_px  = auto()
    p_px  = auto()
    c_vol = auto()
    p_vol = auto()
    c_oi = auto()
    p_oi = auto()


class ScaleOptionChain:
    def __init__(self,
                 msg: dict,
                 inst_mgr: InstrumentManager) -> None:
        ''' scalar fields'''
        self.atm = msg['atm']
        self.ul_symbol = msg['ul_sym']
        self.trd_symbol = msg['trd_sym']
        self.opt_symbol = msg['opt_sym']

        self.opt_exp_ind = msg['opt_exp_ind']
        self.opt_strike_gap = msg['opt_k_gap']
        self.chain_exch_ts = msg['chain_exts']
        self.pub_epoch = msg['pubts']
        ''' dicts '''
        self.ul = msg['ul']
        self.trd = msg['trd']
        self.trd_instid = self.trd['instid']

        self.chain = {}
        for strike_split in msg['chain']:
            strike = strike_split[0]
            cpinfo = strike_split[1]
            self.chain[strike] = cpinfo
        ''' instrument manager based, we can use instrument manager for validations'''
        self.inst_mgr = inst_mgr
        self.trd_lot_size = 1
        self.trd_instr_type = None
        trd_inst = inst_mgr.get_instrument_def_from_id(self.trd_instid)
        if trd_inst:
            self.trd_lot_size = trd_inst[InstField.LotSize]
            self.trd_instr_type = trd_inst[InstField.InstrumentType]

    """
    Generic
    """

    def get_pub_epoch(self):
        return self.pub_epoch

    def get_curr_md_time_lag(self):
        """ time lag from exchange timestamp """
        return int(datetime.now().timestamp()) - int(
            datetime.fromisoformat(self.get_ul_exch_ts()).timestamp())

    def get_opt_strike_gap(self):
        return self.opt_strike_gap

    def get_instr_mgr(self):
        return self.inst_mgr

    """
    Atm
    """

    def get_md_atm(self):
        return self.atm

    def calculate_atm(self, ulpx=None):
        if not ulpx:
            ulpx = self.get_ul_price()  # calculate atm on current underlying price
        return self.inst_mgr.calculate_atm(self.opt_symbol, ulpx, self.opt_exp_ind)

    """
    Underlying methods
    """

    def get_ul_dict(self):
        return self.ul

    def get_ul_symbol(self):
        return self.ul_symbol

    def get_ul_exch_ts(self):
        return self.ul[TickKeys.exts]

    def get_ul_price(self):
        return self.ul[TickKeys.ltp]

    """
    Tradable methods
    """

    def get_trd_lot_size(self):
        return self.trd_lot_size

    def get_trd_symbol(self):
        return self.trd_symbol

    def get_trd_instr_type(self):
        return self.trd_instr_type

    def get_trd_exch_ts(self):
        return self.trd[TickKeys.exts]

    def get_trd_ltp(self):
        return self.trd[TickKeys.ltp]

    def get_trd_top_buy_px(self):
        return self.trd[TickKeys.bk][TickKeys.buy][0][TickKeys.px]

    def get_trd_top_sell_px(self):
        return self.trd[TickKeys.bk][TickKeys.sell][0][TickKeys.px]

    def get_trd_midpx(self):
        return (self.get_trd_top_buy_px() + self.get_trd_top_sell_px()) * 0.5

    """
    Chain methods
    """

    def get_opt_symbol(self) -> str:
        return self.opt_symbol

    def get_opt_expiry_ind(self) -> int:
        return self.opt_exp_ind

    def get_chain_exch_ts(self):
        return self.chain_exch_ts

    def get_opt_ltp(self, strike, instr_type: InstrumentType):
        return self.chain[strike][instr_type][TickKeys.ltp]

    def get_opt_book(self, strike, instr_type: InstrumentType) -> dict:
        return self.chain[strike][instr_type][TickKeys.bk]

    def get_opt_top_buy_px(self, strike, instr_type: InstrumentType):
        return self.get_opt_book(strike, instr_type)[TickKeys.buy][0][TickKeys.px]

    def get_opt_top_sell_px(self, strike, instr_type: InstrumentType):
        return self.get_opt_book(strike, instr_type)[TickKeys.sell][0][TickKeys.px]

    def get_opt_midpx(self, strike, instr_type: InstrumentType):
        return (self.get_opt_top_buy_px(strike, instr_type) + self.get_opt_top_sell_px(strike, instr_type)) * 0.5

    def get_opt_oi(self, strike, instr_type: InstrumentType):
        return self.chain[strike][instr_type][TickKeys.oi]

    def get_opt_vol(self, strike, instr_type: InstrumentType):
        return self.chain[strike][instr_type][TickKeys.vol]

    def get_opt_strikes(self) -> list[float]:
        return list(self.chain.keys())

    def get_2nd_nearest_strike(self):
        strikes = np.array(self.get_opt_strikes())
        idxs = np.argsort(np.abs(strikes - self.get_ul_price()))
        return float(strikes[idxs[1]])  # .item also works

    def get_opt_dataframe(self) -> pd.DataFrame:
        strikes = self.get_opt_strikes()
        strikes.sort()
        d = [{
            OptDfKeys.strike.value: k,
            OptDfKeys.c_px.value : self.get_opt_ltp(k, InstrumentType.CE),
            OptDfKeys.p_px.value : self.get_opt_ltp(k, InstrumentType.PE),
            OptDfKeys.c_vol.value : self.get_opt_vol(k, InstrumentType.CE),
            OptDfKeys.p_vol.value : self.get_opt_vol(k, InstrumentType.PE),
            OptDfKeys.c_oi.value : self.get_opt_oi(k, InstrumentType.CE),
            OptDfKeys.p_oi.value : self.get_opt_oi(k, InstrumentType.PE)
        } for k in strikes
        ]
        return pd.DataFrame(d)

    """
    misc meth
    """

    def get_instrument_name(self, strike, instr_type: InstrumentType):
        return self.inst_mgr.get_option_def_for_expiry_ind(
            underlying=self.opt_symbol,
            instrument_type=instr_type,
            strike=strike)
