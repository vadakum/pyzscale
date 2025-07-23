

from md.scale_option_chain import ScaleOptionChain, OptDfKeys

from enum import StrEnum, IntEnum, auto
from dataclasses import dataclass, field
from collections import namedtuple
from math import floor
from typing import Final

import pandas as pd
import logging

HighValInfo = namedtuple("HighValInfo",
                         ["h1k", "h2k", "h2h1p",
                          "h1d", "d", "s"]
                         )
Summary = namedtuple("Summary", ["leader", "state", "strike", "h2k"])

KeyLeaderOi: Final = 'OI'
KeyLeaderVol: Final = 'VOL'
ChainRowCountAroundAtm: Final = 10


class OptType(IntEnum):
    Call = 1
    Put = 2


class ChainState(StrEnum):
    UN = 'UND'
    XUP = 'XUP'
    XDW = 'XDW'
    STG = 'STG'


class OptSuppRes:
    def __init__(self, up: ScaleOptionChain) -> None:
        self.atm_k = up.calculate_atm()
        self.near2_k = up.get_2nd_nearest_strike()
        self.df = up.get_opt_dataframe()


    def calc_hvinfo(self, 
                    df: pd.DataFrame, 
                    opt_type: OptType, 
                    col: str) -> HighValInfo:
        """
        Column High Values Analysis
        """
        ''' 
        Filter for 1st highest value
          - For calls we scan down (towards higher strikes) starting from Atm-1 strike price 
          - For puts we scan up (towards lower strikes) starting from Atm strike price 
        '''
        lower_k = min(self.near2_k, self.atm_k)
        higher_k = max(self.near2_k, self.atm_k)
        if opt_type == OptType.Call:
            filtdf = df[df[OptDfKeys.strike] >= lower_k]
        else:
            filtdf = df[df[OptDfKeys.strike] <= higher_k]
        ''' 
        1st highest value
          - This is the highest value in the strike filtered rows
        '''
        high1_value_row_df = filtdf.nlargest(1, col)
        h1k = high1_value_row_df[OptDfKeys.strike.value].iloc[0]
        h1_value = high1_value_row_df[col].iloc[0]

        ''' 
        Filter for 2nd highest value
         - Can be anywhere in strike chain unlike the highest value
         - Should be less than 1st highest value but greater than its 75% value
        '''
        tdf = df[
            (df[col] < h1_value) &
            (df[col] >= h1_value * 0.75)
        ]
        '''
        2nd highest value
           - This is the highest value in the h1value filtered rows
           - Can be zero
        '''
        h2k = 0.0
        h2_value = 0.0
        h2h1p = 0.0
        if not tdf.empty:
            tdf = tdf.nlargest(1, col)
            h2k = tdf[OptDfKeys.strike.value].iloc[0]
            h2_value = tdf[col].iloc[0]
            h2h1p = floor((h2_value / h1_value) * 100)
        '''
        Calculate distances relative to atm
        '''
        h1d = abs(h1k - self.atm_k)
        d = h1d
        h2_dist = 0
        if h2k != 0:
            h2_dist = abs(h2k - self.atm_k)
            d = min(h1d, h2_dist)
        '''
        Set the chain state based on h1 and h2 strike relation
        '''
        state = ChainState.UN
        if h2k != 0:
            state = ChainState.XUP if h2k > h1k else ChainState.XDW
        else:
            state = ChainState.STG

        return HighValInfo(h1k=h1k,
                           h2k=h2k,
                           h2h1p=h2h1p,
                           h1d=h1d,
                           d=d,
                           s=state.value)
    """
    The state and of the chain is the state of the leader (from OI and Volume)
    Return the summary state of the leader
    """

    def calc_leader_summary(self, oi: HighValInfo, vol: HighValInfo) -> Summary:
        oi_as_leader = Summary(KeyLeaderOi, oi.s, oi.h1k, oi.h2k)
        vol_as_leader = Summary(KeyLeaderVol, vol.s, vol.h1k, vol.h2k)
        '''
        Lead column identifier logic
        '''
        if vol.h1d < oi.h1d:
            return vol_as_leader
        elif vol.h1d > oi.h1d:
            return oi_as_leader
        else:
            '''' 
            volume and oi max values are on same strike
            now leader depends on d (which is min of 'h1_dist' and 'h2_dist if !0') 
            effectively we are comparing h2_dist via d
            '''
            if vol.d <= oi.d:
                return vol_as_leader
            else:
                return oi_as_leader


    def process(self) -> tuple[Summary, Summary]:

        call_vol = self.calc_hvinfo(self.df, OptType.Call, OptDfKeys.c_vol)
        call_oi = self.calc_hvinfo(self.df, OptType.Call, OptDfKeys.c_oi)
        put_vol = self.calc_hvinfo(self.df,OptType.Put, OptDfKeys.p_vol)
        put_oi = self.calc_hvinfo(self.df, OptType.Put, OptDfKeys.p_oi)

        call_summary = self.calc_leader_summary(call_oi, call_vol)
        put_summary = self.calc_leader_summary(put_oi, put_vol)
        return (call_summary, put_summary)

