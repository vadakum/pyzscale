

from common.dt_helper import DTHelper
from common.walrus_redis import WalrusManager
from md.sub_unsub_const import SubUnsubKeys, SubUnsubMode
from md.md_consts import MDLtpLookup
from md.instrument_manager import (
    InstrumentManager, InstField, InstrumentType,
    OptionBaseMoneynessIndex
)

from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Final
from enum import StrEnum

import time
import json
import zlib
import logging


"""
Module constants
"""
OptSubMode: Final = SubUnsubMode.Full.value
AtmRecalcTimeInSec: Final = 60  # in seconds
PublishIntervalInSec: Final = 1  # in seconds

"""
OptChainConfigKeys
"""


class OptChainCfgKeys(StrEnum):
    OptUL: str = 'option_underlying'
    Options = 'options'
    Tradable = 'tradable'
    # Option specific
    Symbol = 'symbol'
    ExpiryInd = 'expiry_ind'
    NumStrikes = 'numstrikes'


EmptySubUnsub: Final = {
    SubUnsubKeys.Sub.value: {SubUnsubKeys.InstIds.value: [], SubUnsubKeys.Mode.value: None},
    SubUnsubKeys.Unsub.value: {SubUnsubKeys.InstIds.value: []},
}

"""
Instrument wrapper
"""


@dataclass
class InstWrap:
    canonical: str = ""
    id: int = 0
    name: str = ""
    itype: str = ""
    strike: float = 0


"""
Publish Info
"""


@dataclass
class PubInfo:
    ul: dict = field(default_factory=dict)
    trd: dict = field(default_factory=dict)
    ul_sym: str = ""
    trd_sym: str = ""
    opt_sym: str = ""
    opt_exp_ind: int = 0
    opt_k_gap: float = 0
    chain_exts: str = ""
    #
    # Following fields will be filled in dynamically
    # just before publishing:
    # -----------------------
    # atm : str
    # chain: []
    # pub_time : str
    #


"""
TickKeys
"""


class TickKeys(StrEnum):
    instid = 'instid'
    exts = 'exts'

    ltp = 'ltp'
    vol = 'vol'
    oi = 'oi'

    bk = 'bk'
    buy = 'b'
    sell = 's'
    qty = 'q'
    px = 'p'


"""
TickFiller helper
"""


class TickFiller:
    @staticmethod
    def fill_common(d, tick):
        d['instid'] = tick['instrument_token']
        d['exts'] = tick['exchange_timestamp']
        d['ltp'] = tick['last_price']

    @staticmethod
    def fill_depth(d, tick):
        d['bk'] = {}
        d['bk']['b'] = [{'q': i['quantity'], 'p': i['price']}
                        for i in tick['depth']['buy']]
        d['bk']['s'] = [{'q': i['quantity'], 'p': i['price']}
                        for i in tick['depth']['sell']]

    @staticmethod
    def fill_common_and_depth(d, tick):
        TickFiller.fill_common(d, tick)
        TickFiller.fill_depth(d, tick)
        #d['ltt'] = tick['last_trade_time']


"""
Market Option Chain
"""


class OptionChainPub:
    def __init__(self,
                 inst_mgr: InstrumentManager,
                 wm: WalrusManager,
                 config: dict) -> None:
        self.inst_mgr = inst_mgr
        self.chain = {}
        self.canonicals = {}
        self.pub_info = PubInfo()

        opts_cfg_key: Final = OptChainCfgKeys.Options.value
        ul_cfg_key: Final = OptChainCfgKeys.OptUL.value
        trd_cfg_key: Final = OptChainCfgKeys.Tradable.value

        ''' Generate option canonicals'''
        opt_symbol: str = config[opts_cfg_key][OptChainCfgKeys.Symbol]
        opt_expiry_ind: int = config[opts_cfg_key][OptChainCfgKeys.ExpiryInd]
        num_strikes: int = config[opts_cfg_key][OptChainCfgKeys.NumStrikes]
        self.canonicals[opts_cfg_key] = self._gen_option_canonicals_from_config(
            symbol=opt_symbol, expiry_ind=opt_expiry_ind, num_strikes=num_strikes)
        ''' Copy other canonicals from config'''
        for key in [ul_cfg_key, trd_cfg_key]:
            self.canonicals[key] = config[key]

        logging.info(f"Canonicals: {json.dumps(self.canonicals)}")

        # Configure Walrus stream and LTP hash
        self.stream_name = f"CHAIN_{self.canonicals[ul_cfg_key]}_{DTHelper.to_yyyymmdd(datetime.now())}"
        self.stream = wm.get().Stream(self.stream_name)
        self.ltp_hash = wm.get().Hash(MDLtpLookup)

        # Instrument defs
        self.iwrap_opt_map: dict[int, InstWrap] = {}
        self.iwrap_ul = self._resolve_non_option_canonical(
            self.canonicals[ul_cfg_key])
        self.iwrap_trd = self._resolve_non_option_canonical(
            self.canonicals[trd_cfg_key])

        # Fill static publishing info
        self.pub_info.ul_sym = self.iwrap_ul.name
        self.pub_info.trd_sym = self.iwrap_trd.name
        self.pub_info.opt_sym = opt_symbol
        self.pub_info.opt_exp_ind = opt_expiry_ind
        self.pub_info.opt_k_gap = inst_mgr.get_option_strike_gap(
            opt_symbol, opt_expiry_ind)

        # Other working caches
        self.atm = 0
        self.underlying_px = 0
        self.tradable_px = 0
        self.last_atm_calc_time = 0
        self.last_publish_time = 0

        logging.debug(f"--- Underlying: {self.iwrap_ul.name} ---")
        logging.debug(
            f"{OptChainCfgKeys.OptUL} {asdict(self.iwrap_ul)}")
        logging.debug(
            f"{OptChainCfgKeys.Tradable}: {asdict(self.iwrap_trd)}")

    def get_stream_ul_and_name(self) -> tuple[str, str]:
        return (self.pub_info.opt_sym, self.stream_name)

    def _gen_option_canonicals_from_config(self, symbol: str, expiry_ind: int,  num_strikes: int):
        num_itm_otm = int((num_strikes - 1) / 2)
        start_idx = OptionBaseMoneynessIndex - num_itm_otm
        end_idx = OptionBaseMoneynessIndex + num_itm_otm
        canonicals = []
        for idx in range(start_idx, end_idx + 1):
            for ty in ['C', 'P']:
                canonicals.append(f"{symbol.upper()}_{ty}_{expiry_ind}_{idx}")
        return canonicals

    def _resolve_non_option_canonical(self, canonical) -> InstWrap:
        iwrap = InstWrap()
        iwrap.canonical = canonical
        idef = self.inst_mgr.get_instrument_def(canonical)
        instrument_id = idef[InstField.InstrumentToken]
        iwrap.id = instrument_id
        iwrap.name = idef[InstField.TradingSymbol]
        iwrap.itype = idef[InstField.InstrumentType]
        return iwrap

    def _resolve_option_canonicals(self, ref_strike) -> dict[int, InstWrap]:
        iwrap_dict = {}
        for canonical in self.canonicals[OptChainCfgKeys.Options.value]:
            iwrap = InstWrap()
            iwrap.canonical = canonical
            idef = self.inst_mgr.get_instrument_def(canonical, ref_strike)
            iwrap.id = idef[InstField.InstrumentToken]
            iwrap.name = idef[InstField.TradingSymbol]
            iwrap.itype = idef[InstField.InstrumentType]
            iwrap.strike = idef[InstField.Strike]
            iwrap_dict[iwrap.id] = iwrap
        return iwrap_dict

    def get_interested_instruments(self) -> list[int]:
        return list(set([self.iwrap_ul.id, self.iwrap_trd.id]))

    def is_valid(self):
        return (self.atm > 0 and
                self.underlying_px > 0 and
                self.tradable_px > 0 and
                self.atm in self.chain and
                InstrumentType.CE.value in self.chain[self.atm] and
                InstrumentType.PE.value in self.chain[self.atm] and
                self.chain[self.atm][InstrumentType.CE.value][TickKeys.ltp.value] > 0 and
                self.chain[self.atm][InstrumentType.PE.value][TickKeys.ltp.value] > 0
                )
    """
    Rebuild chain
    """

    def _rebuild_chain_and_sun_dict(self, new_atm):
        sub_list = []
        unsub_list = []
        prev_subscription_set = set(self.iwrap_opt_map.keys())
        self.iwrap_opt_map = self._resolve_option_canonicals(new_atm)
        curr_subscription_set = set(self.iwrap_opt_map.keys())
        if prev_subscription_set:
            sub_list = list(curr_subscription_set -
                            prev_subscription_set)
            unsub_list = list(
                prev_subscription_set - curr_subscription_set)
        else:
            sub_list = list(curr_subscription_set)
        sun = {
            SubUnsubKeys.Sub.value: {
                SubUnsubKeys.InstIds.value: sub_list,
                SubUnsubKeys.Mode.value: OptSubMode
            },
            SubUnsubKeys.Unsub.value: {
                SubUnsubKeys.InstIds.value: unsub_list
            },
        }
        ''' Sync the chain '''
        temp_chain = {}
        for _, iwrap in self.iwrap_opt_map.items():
            temp_chain[iwrap.strike] = {
                InstrumentType.CE.value: {
                    TickKeys.ltp.value: 0,
                    TickKeys.vol.value: 0,
                    TickKeys.oi.value: 0,
                    TickKeys.bk.value: {}
                },
                InstrumentType.PE.value: {
                    TickKeys.ltp.value: 0,
                    TickKeys.vol.value: 0,
                    TickKeys.oi.value: 0,
                    TickKeys.bk.value: {}
                },
            }
        # Copy prices from current chain
        for strike in list(temp_chain.keys()):
            if strike in self.chain:
                temp_chain[strike] = self.chain[strike]
        self.chain = temp_chain
        return sun

    """
    Instrument specific update handling
    """

    def process_option_update(self, iwrap: InstWrap, tick):
        if iwrap.strike not in self.chain:
            return
        leaf = self.chain[iwrap.strike][iwrap.itype]
        leaf[TickKeys.ltp.value] = tick[InstField.LastPrice]
        leaf[TickKeys.vol.value] = tick['volume_traded']
        leaf[TickKeys.oi.value] = tick['oi']
        # Save book for each call/put instrument
        TickFiller.fill_depth(leaf, tick)
        # To know when was the chain generally updated last time
        self.pub_info.chain_exts = tick['exchange_timestamp']

    def _process_tradable_update(self, tick):
        self.tradable_px = tick[InstField.LastPrice]
        TickFiller.fill_common_and_depth(self.pub_info.trd, tick=tick)
        logging.debug(
            f"Tradable: {self.iwrap_trd.canonical} : {self.iwrap_trd.name} ltp:{self.tradable_px}")

    def _process_underlying_update(self, tick) -> dict[str, list[int]]:
        self.underlying_px = tick[InstField.LastPrice]
        TickFiller.fill_common(self.pub_info.ul, tick=tick)

        ''' Atm recalculatio logic'''
        sun = EmptySubUnsub
        time_elapsed = int(time.time() - self.last_atm_calc_time)
        if time_elapsed < AtmRecalcTimeInSec:
            return sun

        new_atm = self.inst_mgr.calculate_atm(
            underlying=self.iwrap_ul.name, underlying_price=self.underlying_px)
        if self.atm != new_atm:
            ''' Atm changed'''
            sun = self._rebuild_chain_and_sun_dict(new_atm)
            logging.info(
                f"-> Atm changed: {self.iwrap_ul.name}, ulpx:{self.underlying_px}, prev_atm={self.atm}, new_atm={new_atm}")
            logging.debug(
                f"-> Sub Unsub  : sub:{sun[SubUnsubKeys.Sub]}, unsub:{sun[SubUnsubKeys.Unsub]}")
        self.atm = new_atm
        self.last_atm_calc_time = time.time()
        logging.debug(
            f"-> Underlying: {self.iwrap_ul.name}, px:{self.underlying_px}, atm:{self.atm}")
        return sun

    """
    process_tick_update : main method
    """

    def process_tick_update(self, tick) -> dict:
        inst_id = tick[InstField.InstrumentToken]
        ltp = tick[InstField.LastPrice]
        
        ret_sun = EmptySubUnsub
        # First process the underlying
        if inst_id == self.iwrap_ul.id:
            ret_sun = self._process_underlying_update(tick=tick)

        # Process Tradeable (underlying and tradable can be same)
        # If they are same then, process non atm changes here
        if inst_id == self.iwrap_trd.id:
            self._process_tradable_update(tick=tick)

        elif inst_id in self.iwrap_opt_map:
            self.process_option_update(
                iwrap=self.iwrap_opt_map[inst_id], tick=tick)

        # Update ltp hash
        self.ltp_hash.update({inst_id : ltp})
        # Publish to stream
        if self.is_valid():
            elapsed_time = int(time.time() - self.last_publish_time)
            if elapsed_time >= PublishIntervalInSec:
                self._prepare_snapshot_and_publish()
                self.last_publish_time = time.time()
                logging.debug(f"Published to: {self.stream_name}")

        return ret_sun

    """
    publish protocol
    """

    def _prepare_snapshot_and_publish(self):
        pub_dict = asdict(self.pub_info)
        pub_dict['atm'] = self.atm
        pub_dict['chain'] = [kv for kv in self.chain.items()]
        pub_epoch = int(datetime.now().timestamp())
        pub_dict['pubts'] = pub_epoch
        bin_data = zlib.compress(json.dumps(
            pub_dict, default=str).encode('utf-8'))
        self.stream.add({'t': pub_epoch, 'v': bin_data})
