

from md.md_consts import MDLtpLookup

from typing import Final
from enum import StrEnum, IntEnum, auto
from collections import namedtuple
from dataclasses import dataclass
from dataclasses_json import dataclass_json

TCost: Final = {
    'NK_O': 0.00091868,  # Per rupee
    'NK_F': 0.0000961,   # Per rupee
    'NK_E': 0.00017953,  # Per rupee
}

PerOrderCost: Final = 23.6

MaxRejectionCount = 25
MaxOrderPosSyncTimeSec = 3 * 60

class ExecInstType(StrEnum):
    NK_F = "NK_F"
    NK_O = "NK_O"
    NK_E = "NK_E"

class Exchange(StrEnum):
    NSE = "NSE"
    NFO = "NFO"


class ProductType(StrEnum):
    MIS = "MIS"
    NRML = "NRML"
    CNC = "CNC"


class OrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    SL_MARKET = "SL-M"
    SL_LIMIT = "SL"


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

"""
Strategy Types copied from backtest
"""
class EntryType(IntEnum):
    Clear = 0
    Buy = 1
    Sell = 2

class Tran(StrEnum):
    Open = "OPEN"
    Close = "CLOSE"

TradeNt = namedtuple(
    "TradeNt", ['time', 'inst', 'tran', 'side', 'price', 'profit', 'cost', 'to', 'hold',
                'sigval', 'cpx', 'ppx', 'ulpx', 'atm'])

class BotKeys(StrEnum):
    """
    Key names for Scale Bot args, some taken from SBKeys
    """
    botuuid = auto()
    slist = auto()
    ''' The main section'''
    common = auto()
    alpha = auto()
    execution = auto()
    ''' common : keys '''
    start_time = auto()
    end_time = auto()
    underlying = auto()
    ''' execution keys '''
    strategy_name = auto()
    strategy_id = auto()
    exchange = auto()
    product_type = auto()
    order_type = auto()
    opt_trd_offset = auto()
    quote_lots = auto()
    max_pos = auto()
    stop_loss = auto()
    profit_target = auto()

class BotStatusKeys(StrEnum):
    status = auto()
    underlying = auto()
    # params copied from CtrlKeys.params.value

class CtrlKeys(StrEnum):
    strat_id = auto()
    msg = auto()
    action = auto()
    params = auto()
    # Actions
    start = auto()
    stop = auto()
    update=auto()


class OrderStatus(StrEnum):
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    # An order can traverse through several interim and temporary statuses
    # like "VALIDATION PENDING", "OPEN PENDING", CANCEL PENDING etc


@dataclass_json
@dataclass
class OrderInfo:
    """
    OrderInfo
    """
    order_id: str = ""  # The order id received from broker after placing the order
    strat_id: str = ""  # Internal strategy id, filled by pos pnl manager
    tradingsymbol: str = ""
    exchange: str = ""
    instrument_token: int = 0
    transaction_type: str = ""
    order_type: str = ""
    order_status: str = ""
    price: float = 0
    quantity: int = 0
    average_price: float = 0 # Average price at which the order was executed (only for COMPLETE orders)
    pending_quantity: int = 0  # Pending quantity to be filled
    filled_quantity: int = 0  # Filled quantity
    cancelled_quantity : int = 0 # Cancelled quantity
    order_timestamp: str = ""  # Timestamp at which the order was registered by the API
    exchange_timestamp: str = ""
    message: str = ""  # error message from the broker


"""
TradeInfo
"""


@dataclass_json
@dataclass
class TradeInfo:
    order_id: str = ""
    strat_id: str = ""
    trade_id: str = ""
    exchange_order_id: str = ""
    tradingsymbol: str = ""
    exchange: str = ""
    instrument_token: int = 0
    transaction_type: str = ""
    price: float = 0  # average_price in kite docs
    fill_qty: int = 0
    fill_timestamp: str = ""
    order_timestamp: str = ""
    exchange_timestamp: str = ""


"""
PortPos json class
"""


@dataclass_json
@dataclass
class StratPosPnl:
    inst_name: str = ""
    ltp: float = 0
    netpnl: float = 0
    pnl_real: float = 0
    pnl_unreal: float = 0
    netpos: int = 0
    long: int = 0
    short: int = 0
    numord: int = 0    
    inst_id: int = 0    
    tcost: float = 0
    cost_type: str = ""
    buy_value: float = 0
    sell_value: float = 0



"""
RunningPos - pnl and pos computer
"""


@dataclass
class RunningPos:
    instrument_token: int = 0
    inst_name : str = ""    
    ltp: float = 0
    cost_instr_type: str = ""
    num_orders: int = 0
    netpos: int = 0
    buy_total_value: float = 0
    sell_total_value: float = 0
    buy_total_qty: int = 0
    sell_total_qty: int = 0
    pnl_realized: float = 0
    pnl_unrealized: float = 0
    netpnl: float = 0
    total_tcost: float = 0

    # work states
    _buy_value: float = 0
    _sell_value: float = 0
    _buy_qty: int = 0
    _sell_qty: int = 0
    _buy_avg_px: float = 0
    _sell_avg_px: float = 0
    _running_cost: float = 0

    def reset_pos_accu(self):
        self._buy_value = 0
        self._sell_value = 0
        self._buy_avg_px = 0
        self._sell_avg_px = 0
        self._buy_qty = 0
        self._sell_qty = 0
        self._running_cost = 0

    def to_stratpospnl(self):
        return StratPosPnl(
            inst_id=self.instrument_token,
            inst_name=self.inst_name,
            ltp=self.ltp,
            netpos=self.netpos,
            netpnl=self.netpnl,
            cost_type=self.cost_instr_type,
            buy_value=self.buy_total_value,
            sell_value=self.sell_total_value,
            long=self.buy_total_qty,
            short=self.sell_total_qty,
            pnl_real=self.pnl_realized,
            pnl_unreal=self.pnl_unrealized,
            numord=self.num_orders,
            tcost=self.total_tcost,
        )


"""
Bot Redis Key Helper
"""


class BotRedisKeyHelper:
    @staticmethod
    def get_ltp_hash_key():
        return MDLtpLookup

    @staticmethod
    def get_strat_order_hash_key(botuuid: str):
        return f"{botuuid}__STRAT_ORDER_HASH"

    @staticmethod
    def get_strat_pos_hash_key(botuuid: str):
        return f"{botuuid}__STRAT_POS_HASH"

    @staticmethod
    def get_order_info_hash_key(botuuid: str):
        return f"{botuuid}__ORDER_HASH"

    @staticmethod
    def get_trade_info_hash_key(botuuid: str):
        return f"{botuuid}__TRADE_HASH"
    
    @staticmethod
    def get_strat_control_stream_key(botuuid : str):
        return f"{botuuid}__CTRL_STREAM"

    @staticmethod
    def get_strat_status_hash(botuuid : str):
        return f"{botuuid}__STRAT_STATUS_HASH"
