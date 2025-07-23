from typing import Final
from collections import namedtuple
from dataclasses import dataclass, asdict
from enum import StrEnum, IntEnum
from modelservice.scale_alpha import ScaleSignal
import tabulate

TCost = {
    'NK_O': 0.00091868,  # Per rupee
    'NK_F': 0.0000961,  # Per rupee
    'E': 0.00017953,  # Per rupee
}

PerOrderCost: Final = 23.6

class ExecInstType(StrEnum):
    NK_F  = "NK_F"
    NK_O = "NK_O"

class PriceType(StrEnum):
    LTP = "LTP"
    MID = "MID"
    BEST = "BEST"
    CROSS = "CROSS"    

class EntryType(IntEnum):
    Clear = 0
    Buy = 1
    Sell = 2

class Side(StrEnum):
    Buy = "BUY"
    Sell = "SELL"

class Tran(StrEnum):
    Open = "OPEN"
    Close = "CLOSE"

"""
NamedTuples
"""
CallPutPxNt = namedtuple("CallPutPxNt", ["call_px", "put_px"])
EntryNt = namedtuple(
    "EntryNt", ["fut_entry_px", "entry_strike", "call_entry_px", "put_entry_px", "entry_time"])
"""
TradeMarker
"""
'''
side = 'B' or 'S'
tran = 'O' (opening trade) or 'C' (closing trade)
price = trade price
profit = for Closing trades (gross profit)
cost = cost for the trade (perorder + turnouver)
'''
TradeNt = namedtuple(
    "TradeNt", ['time', 'inst', 'tran', 'side', 'price', 'profit', 'cost', 'to', 'hold',
                'sigval', 'cpx', 'ppx', 'ulpx', 'atm'])


@dataclass
class TradeSummary:
    num_trades: int = 0
    net_pnl: float = 0    
    tcost: float = 0    
    max_profit: float = 0
    max_loss: float = 0
    to: float = 0
    avg_entry_px: float = 0
    lot_size: int = 0
    quote_lots: int = 0
    max_hold_sec : int  = 0


@dataclass
class RangeSummary:
    num_trades: int = 0
    num_days: int = 0
    neg_days: int = 0
    max_profit: float = 0
    max_loss: float = 0
    tcost: float = 0
    brokerage: float = 0
    net_pnl: float = 0
    to: float = 0
    avg_entry_px: int = 0
    quote_lots: int = 0
    lot_size: int = 0


"""
DailyResult
"""


class DayResult:
    def __init__(self, 
                 underlying, 
                 trading_date, 
                 lot_size,
                 quote_lots) -> None:
        self.entry_date = trading_date
        self.underlying = underlying
        self.lot_size = lot_size
        self.quote_lots = quote_lots        
        self.trade_markers: list[TradeNt] = []

    def set_quote_lots(self, lots):
        self.quote_lots = lots

    def push_trades(self, tradent):
        self.trade_markers.append(tradent)

    def summarize(self) -> TradeSummary:
        summary = TradeSummary()
        summary.quote_lots = self.quote_lots
        summary.lot_size = self.lot_size
        totalPrice = 0
        for trd in self.trade_markers:
            totalPrice += trd.price
            summary.num_trades += 1
            summary.max_profit = max(summary.max_profit, trd.profit)
            summary.max_loss = min(summary.max_loss, trd.profit)
            summary.tcost += trd.cost
            summary.net_pnl += (trd.profit - trd.cost)
            summary.to += trd.to
            if trd.hold:
                summary.max_hold_sec = max(summary.max_hold_sec, int(trd.hold.total_seconds()))

        # round values
        if summary.num_trades > 0:
            summary.avg_entry_px = round(totalPrice / summary.num_trades)
        summary.tcost = round(summary.tcost, 1)
        summary.net_pnl = round(summary.net_pnl, 1)
        return summary

    def gen_result(self, show_trades=True):
        summary = self.summarize()
        result = {
            'underlying': self.underlying,
            'date': self.entry_date,
            'summary': asdict(summary),
            'trademarkers': [x._asdict() for x in self.trade_markers] if show_trades else [],
        }
        return result
    
    @staticmethod
    def print_result(result : dict):
        for k,v in result.items():
            if k == 'trademarkers':
                print(tabulate.tabulate(v, headers='keys', tablefmt="simple_grid"))        
            elif k == 'summary':    
                print(tabulate.tabulate([v], headers='keys', tablefmt="simple_grid"))        
            else:
                print(f"{k} => {v}")


