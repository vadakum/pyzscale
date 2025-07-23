

from enum import StrEnum, IntEnum
from typing import Final
from bisect import bisect_left
from datetime import datetime
from common.dt_helper import DTHelper
from md.indices_helper import IndicesHelper

import json
import logging
import math


"""
Built on Instrument File format:
{
    "instrument_token": 13358338, "exchange_token": "52181", 
    "tradingsymbol": "BANKNIFTY24MAR34500CE", "name": "BANKNIFTY", 
    "last_price": 0.0, "expiry": "2024-03-27", "strike": 34500.0, "tick_size": 0.05, 
    "lot_size": 15, "instrument_type": "CE", "segment": "NFO-OPT", "exchange": "NFO"
}

where:
 exchange: BCD, BFO, BSE, CDS, MCX, NFO, NSE, NSEIX
 segment: BCD-FUT, BCD-OPT, BFO-FUT, BFO-OPT, BSE, CDS-FUT, CDS-OPT, INDICES, MCX-FUT, MCX-OPT, NFO-FUT, NFO-OPT, NSE
 instrument_type: CE, EQ, FUT, PE

Doc:
 - if segment = INDICES then exchange found were: BSE,CDS,MCX,NSE,NSEIX
   grep 'INDICES' instrument-20240307.dat | jq -c '.exchange' | sort | uniq | tr -d '"' | tr '\n' ','

Instrument Field Names
"""


class InstField(StrEnum):
    InstrumentToken = 'instrument_token'
    ExchangeToken = 'exchange_token'
    TradingSymbol = 'tradingsymbol'
    Name = 'name'
    LastPrice = 'last_price'
    Expiry = 'expiry'
    Strike = 'strike'
    TickSize = 'tick_size'
    LotSize = 'lot_size'
    InstrumentType = 'instrument_type'  # see InstrumentType enum
    Segment = 'segment'
    Exchange = 'exchange'
    # Custom - internal fields
    IndexName = 'index_name'


"""
Constants
"""
OptionBaseMoneynessIndex: Final = 100


class OptionCacheKeys(StrEnum):
    StrikeGap = 'strike_gap'
    SortedExpiries = 'sorted_expiries'
    SortedStrikes = 'sorted_strikes'


"""
Instrument Type
"""


class InstrumentType(StrEnum):
    INDEX = "INDICES"
    EQ = "EQ"
    FUT = "FUT"
    CE = "CE"
    PE = "PE"


"""
ExpiryInd
"""


class ExpiryInd(IntEnum):
    Current = 0
    Next = 1
    Far = 2


"""
PerfCache
"""


class PerfCache:
    FutExpiryDates: Final = "fut_expiry_dates"

    def __init__(self) -> None:
        self._cache = {
            PerfCache.FutExpiryDates: {},
        }

    '''
    Expiry date list cache for future, to avoid sorting during
    continuous lookups
    '''

    def get_future_expiry_dates(self, symbol: str):
        if symbol in self._cache[PerfCache.FutExpiryDates]:
            return self._cache[PerfCache.FutExpiryDates][symbol]
        return None

    def set_future_expiry_dates(self, symbol: str, expiry_dates: list):
        self._cache[PerfCache.FutExpiryDates][symbol] = expiry_dates


"""
InstrumentManager
"""


class InstrumentManager:

    """
    Build cache of Non Expired Instrument
        exchanges: BCD, BFO, BSE, CDS, MCX, NFO, NSE, NSEIX
        Note: 
            Always provide Main Exchange (e.g NSE with NFO) else 
            index won't be availabe.
    """

    def __init__(self,
                 inst_file: str,
                 trading_date: str = DTHelper.to_yyyy_mm_dd(datetime.now()),
                 exchanges=['NSE', 'NFO']):

        self.trading_date_dashfmt = None
        if "-" not in trading_date:
            self.trading_date_dashfmt = DTHelper.from_yyyymmdd_to_yyyy_mm_dd(
                trading_date)
        else:
            self.trading_date_dashfmt = trading_date
        self.perf_cache = PerfCache()
        self.indices_mapping = IndicesHelper(
            exchanges=exchanges).get_indices_mapping()

        with open(inst_file, 'r') as stream:
            lines = stream.readlines()

        inst_dicts = [json.loads(line) for line in lines if line]
        inst_rows = [
            inst for inst in inst_dicts if (
                inst[InstField.Exchange] in exchanges and
                (inst[InstField.Expiry] == "" or not InstrumentManager.is_expired(
                    inst[InstField.Expiry], self.trading_date_dashfmt))
            )
        ]
        # For Faster intrument_token based lookup
        self.instrument_id_cache = {}
        # Future Tree => underlying -> expiry -> {future def}
        self.future_tree = {}
        # Option Tree => see _build_options_tree documentation
        self.option_tree = {}
        self.option_cache = {}
        # Index Tree => underlying -> {index def}
        self.indices_tree = {}
        # Equity Tree => tradingsymbol -> {index def}
        self.equity_tree = {}
        # Build trees and caches for faster lookups
        self._build_futures_tree(inst_rows)
        self._build_options_tree_and_cache(inst_rows)
        self._build_indices_tree(inst_rows)
        self._build_equity_tree(inst_rows)

    """
    helpers to identify main types
    """
    @staticmethod
    def is_options(inst: dict):
        return inst[InstField.InstrumentType] in [InstrumentType.CE, InstrumentType.PE]

    @staticmethod
    def is_futures(inst: dict):
        return inst[InstField.InstrumentType] == InstrumentType.FUT
    
    @staticmethod
    def is_equity(inst: dict):
        return ("-" not in inst[InstField.TradingSymbol] and
                inst[InstField.Segment] != InstrumentType.INDEX and
                inst[InstField.InstrumentType] == InstrumentType.EQ
                )
    """
    Equity tree
    """

    def _build_equity_tree(self, inst_rows):
        equities = [inst for inst in inst_rows if InstrumentManager.is_equity(inst)]
        for inst in equities:
            symbol = inst[InstField.TradingSymbol]
            ''' tree leaf node and id cache'''
            self.equity_tree[symbol] = inst
            self.instrument_id_cache[inst[InstField.InstrumentToken]] = inst

    """
    Indexes tree
    """

    def _build_indices_tree(self, inst_rows):
        known_indices_mapping = list(self.indices_mapping.keys())
        indices = [
            inst for inst in inst_rows if (
                inst[InstField.Segment] == InstrumentType.INDEX and
                inst[InstField.TradingSymbol] in known_indices_mapping
            )
        ]
        for inst in indices:
            enrich_inst = inst
            detailed_name = inst[InstField.TradingSymbol]
            known_name = self.indices_mapping[detailed_name]
            # overwrite trading symbol
            enrich_inst[InstField.TradingSymbol] = known_name
            # save the detailed name in index_name
            enrich_inst[InstField.IndexName.value] = detailed_name
            ''' tree leaf node and id cache'''
            self.indices_tree[known_name] = enrich_inst
            self.instrument_id_cache[inst[InstField.InstrumentToken]
                                     ] = enrich_inst

    """
    Futures tree
    """

    def _build_futures_tree(self, inst_rows):
        futures = [inst for inst in inst_rows if InstrumentManager.is_futures(inst)]
        for inst in futures:
            underlying = inst[InstField.Name]
            expiry = inst[InstField.Expiry]
            if underlying not in self.future_tree:
                self.future_tree[underlying] = {}
            ul_map = self.future_tree[underlying]
            ''' tree leaf node and id cache'''
            ul_map[expiry] = inst
            self.instrument_id_cache[inst[InstField.InstrumentToken]] = inst

    """
    Option Tree  => underlying |->expiry |->type |->strike -> {option def}

    Option Cache => underlying |->expiry |
                               |         |-> StrikeGap -> value         
                               |         |-> SortedStrikes ->[]        
                               |->SortedExpiries -> []        
    """

    def _build_options_tree_and_cache(self, inst_rows):
        options = [
            inst for inst in inst_rows if InstrumentManager.is_options(inst)]
        for inst in options:
            underlying = inst[InstField.Name]
            expiry = inst[InstField.Expiry]
            instrument_type = inst[InstField.InstrumentType]
            strike = inst[InstField.Strike]

            if underlying not in self.option_tree:
                self.option_tree[underlying] = {}
            ul_map = self.option_tree[underlying]
            if expiry not in ul_map:
                ul_map[expiry] = {}
            exp_map = ul_map[expiry]
            if instrument_type not in exp_map:
                exp_map[instrument_type] = {}
            type_map = exp_map[instrument_type]
            ''' tree leaf node and id cache'''
            type_map[strike] = inst
            self.instrument_id_cache[inst[InstField.InstrumentToken]] = inst

        # Build additional cache Info for options
        underlyings = list(self.option_tree.keys())
        for underlying in underlyings:
            expiry_dates = list(self.option_tree[underlying].keys())
            expiry_dates.sort()
            if underlying not in self.option_cache:
                self.option_cache[underlying] = {}
            self.option_cache[underlying][OptionCacheKeys.SortedExpiries] = expiry_dates

            for expiry_date in expiry_dates:
                strikes = list(
                    self.option_tree[underlying][expiry_date][InstrumentType.CE].keys())
                strikes.sort()
                strike_gap = 0
                num_strikes = len(strikes)
                if (num_strikes >= 2):
                    mid = math.trunc(num_strikes / 2)
                    strike_gap = abs(strikes[mid] - strikes[mid - 1])
                else:
                    logging.error(
                        f"Option tree: {underlying} {expiry_date} has only {num_strikes}, setting strike gap to 0")
                if expiry_date not in self.option_cache[underlying]:
                    self.option_cache[underlying][expiry_date] = {}
                self.option_cache[underlying][expiry_date][OptionCacheKeys.SortedStrikes] = strikes
                self.option_cache[underlying][expiry_date][OptionCacheKeys.StrikeGap] = strike_gap

    @staticmethod
    def is_expired(expiry_date: str, today: str):
        return (DTHelper.diff_days_yyyymmdd_dash(expiry_date, today) < 0)

    """
    Token Fetch Methods
    """

    def get_instrument_def_from_id(self, instrument_token):
        if instrument_token in self.instrument_id_cache:
            return self.instrument_id_cache[instrument_token]
        return None

    """
    Index Methods
    """

    def get_all_indices(self) -> list:
        indices = [
            v for _, v in self.instrument_id_cache.items()
            if v[InstField.Segment] == InstrumentType.INDEX
        ]
        return indices

    def get_active_indices(self) -> list:
        return list(self.indices_tree.values())

    def get_index_def(self, underlying):
        if underlying in self.indices_tree:
            return self.indices_tree[underlying]
        return None

    def is_index(self, instrument_token):
        for k in self.indices_tree.keys():
            if self.indices_tree[k][InstField.InstrumentToken] == instrument_token:
                return True
        return False

    """
    Get expiry date for future and options
    """

    def get_future_expiry_dates(self, underlying):
        expiry_dates = list(self.future_tree[underlying].keys())
        expiry_dates.sort()
        return expiry_dates

    def get_option_expiry_dates(self, underlying):
        return self.option_cache[underlying][OptionCacheKeys.SortedExpiries]

    """
    Future Methods
    """

    def get_future_def(self, underlying: str, expiry: str):
        return self.future_tree[underlying][expiry]

    """
    Equity Methods
    """

    def get_equity_def(self, symbol):
        return self.equity_tree[symbol]

    """
    Option Methods
    """

    def get_option_def_for_expiry_dt(self, underlying: str, instrument_type: InstrumentType, expiry: str, strike: float):
        return self.option_tree[underlying][expiry][instrument_type][strike]

    def get_option_def_for_expiry_ind(self, underlying: str,
                                      instrument_type: InstrumentType,
                                      strike: float,
                                      expiry_index: ExpiryInd = ExpiryInd.Current,):
        expiry_dates = self.get_option_expiry_dates(underlying)
        expiry = expiry_dates[expiry_index]
        return self.get_option_def_for_expiry_dt(underlying, instrument_type, expiry=expiry, strike=strike)

    def get_option_strikes(self, underlying: str, expiry: str):
        return self.option_cache[underlying][expiry][OptionCacheKeys.SortedStrikes]

    def get_option_strike_gap(self, underlying: str, expiry_index: ExpiryInd = ExpiryInd.Current):
        expiry_dates = self.get_option_expiry_dates(underlying=underlying)
        expiry_date = expiry_dates[expiry_index]
        return self.option_cache[underlying][expiry_date][OptionCacheKeys.StrikeGap]

    def get_all_option_underlyings(self):
        underlyings = list(self.option_tree.keys())
        underlyings.sort()
        return underlyings

    def get_opt_lot_size(self, underlying: str, expiry_index: ExpiryInd = ExpiryInd.Current):
        expiry_dates = self.get_option_expiry_dates(underlying)
        expiry = expiry_dates[expiry_index]
        strikes = self.get_option_strikes(underlying, expiry=expiry)
        return self.get_option_def_for_expiry_dt(underlying, InstrumentType.CE, expiry=expiry, strike=strikes[0])[InstField.LotSize]

    """
    Figure out the ATM in the strike chain
    """
    # import numpy as np
    # @staticmethod
    # def get_atm(strikes, underlying_price):
    #     idx = (np.abs(np.array(strikes) - underlying_price)).argmin()
    #     return strikes[idx]

    @staticmethod
    def get_atm(strikes, underlying_price):
        pos = bisect_left(strikes, underlying_price)
        if pos == 0:
            return strikes[0]
        if pos == len(strikes):
            return strikes[-1]
        before = strikes[pos - 1]
        after = strikes[pos]
        if after - underlying_price < underlying_price - before:
            return after
        else:
            return before

    def calculate_atm(self, underlying, underlying_price, expiry_index: ExpiryInd = ExpiryInd.Current):
        expiry_dates = self.get_option_expiry_dates(underlying)
        strikes = self.get_option_strikes(
            underlying, expiry_dates[expiry_index])
        return InstrumentManager.get_atm(strikes, underlying_price)

    """
    This will be the most used method:
        qg_instr format: <Exchange>_<Underlying>_<InstrumentType>_[<ExpiryIndex>]_[<Moneyness>]
        Index:  BANKNIFTY_I
        Equity: BANKNIFTY_EQ
        Future: BANKNIFTY_F_0
        Option: (qg instrument + ref_strike arg for moneyness resolution )
            BANKNIFTY_C_0_99  
            BANKNIFTY_C_0_100  
            BANKNIFTY_C_0_101
    """

    def get_instrument_def(self, qg_instr: str, ref_strike: float = None) -> dict:
        logging.debug(f"Parsing: qg_instr: {qg_instr}")

        tokens = qg_instr.upper().split('_')
        token_len = len(tokens)
        #
        # Index / Equity parsing
        #
        if token_len < 2:
            logging.error(f"Parsing error: Invalid qg_instr:{qg_instr}")
            return None
        symbol = tokens[0]
        instype = tokens[1]

        if instype == 'I':
            return self.get_index_def(symbol)

        if instype == 'EQ':
            return self.get_equity_def(symbol=symbol)

        #
        # Future Parsing
        #
        if token_len < 3:
            logging.error(
                f"Parsing error: Invalid symbol for fut/option: {qg_instr}")
            return None

        expiry_index = int(tokens[2])

        if instype == 'F':
            expiry_dates = self.perf_cache.get_future_expiry_dates(
                symbol=symbol)
            if not expiry_dates:
                expiry_dates = self.get_future_expiry_dates(underlying=symbol)
                self.perf_cache.set_future_expiry_dates(
                    symbol=symbol, expiry_dates=expiry_dates)
            if expiry_dates and expiry_index >= 0 and len(expiry_dates) > expiry_index:
                expiry_date = expiry_dates[expiry_index]
                return self.get_future_def(underlying=symbol, expiry=expiry_date)
            else:
                logging.error(
                    f"Unable to fetch futures:{qg_instr}, expiry_dates={expiry_dates}")
                return None

        #
        # Option parsing
        #
        if not ref_strike:
            logging.error(
                f"Reference strike missing for calculating option moneyness for:{qg_instr}")
            return None
        instrument_type = None
        moneyness_dir = None
        if instype == 'C':
            instrument_type = InstrumentType.CE
            moneyness_dir = 1
        elif instype == 'P':
            instrument_type = InstrumentType.PE
            moneyness_dir = -1

        if not instrument_type or not moneyness_dir:
            logging.error(
                f"Parsing error:Invalid option instrument type:{qg_instr}")
            return None

        expiry_dates = self.get_option_expiry_dates(underlying=symbol)
        expiry_date = expiry_dates[expiry_index]
        if token_len < 4:
            logging.error(
                f"Parsing error: Invalid symbol for option:{qg_instr}")
            return None

        moneyness = int(tokens[3]) - OptionBaseMoneynessIndex
        sorted_strikes = self.get_option_strikes(
            underlying=symbol, expiry=expiry_date)

        try:
            ref_strike_index = sorted_strikes.index(ref_strike)
        except ValueError as ex:
            logging.error(
                f"Failed to get ref_strike: {ref_strike} in strike list of: {qg_instr}")
            return None
        moneyness_index = ref_strike_index + (moneyness * moneyness_dir)
        if moneyness_index < 0 or moneyness_index >= len(sorted_strikes):
            logging.error(
                f"Moneyness index {moneyness_index} is out of bounds, ref_strike_index={ref_strike_index}, all_strikes={sorted_strikes}")
            return None

        logging.debug(
            f"Ref strike index = {ref_strike_index}, Moneyness index = {moneyness_index}")
        moneyness_strike = sorted_strikes[moneyness_index]
        return self.get_option_def_for_expiry_dt(underlying=symbol,
                                                 instrument_type=instrument_type,
                                                 expiry=expiry_date,
                                                 strike=moneyness_strike)
