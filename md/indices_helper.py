from enum import StrEnum
from typing import Final

"""
Indices Helper 
"""


class IndicesExchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    CDS = "CDS"
    NSEIX = "NSEIX"


"""
Check doc in instrument_manager.py
"""
IndicesExchangeToInstFileExchangeMap: Final = {
    IndicesExchange.NSE: set(["NFO", "NSE"]),
    IndicesExchange.BSE: set(["BFO", "BSE"]),
    IndicesExchange.MCX: set(["MCX"]),
    IndicesExchange.CDS: set(["CDS"]),
    IndicesExchange.NSEIX: set(["NSEIX"]),
}

"""
tradingsymbol to exchange documentation mapping
https://www.nseindia.com/products-services/equity-derivatives-list-underlyings-information
"""
IndexTradingSymbolToUnderlyingMap: Final = {
    IndicesExchange.NSE: {
        'NIFTY MID SELECT': 'MIDCPNIFTY',
        'NIFTY 50': 'NIFTY',
        'NIFTY FIN SERVICE': 'FINNIFTY',
        'NIFTY BANK': 'BANKNIFTY',
        'INDIA VIX': 'INDIAVIX',
    },
}


class IndicesHelper:
    def __init__(self, exchanges: list) -> None:
        indices_exch_key = None
        self.indices_mapping = {}
        for k, v in IndicesExchangeToInstFileExchangeMap.items():
            if not v.isdisjoint(exchanges):
                indices_exch_key = k
                break
        if indices_exch_key and indices_exch_key in IndexTradingSymbolToUnderlyingMap:
            self.indices_mapping = IndexTradingSymbolToUnderlyingMap[indices_exch_key]

    def get_indices_mapping(self):
        return self.indices_mapping
