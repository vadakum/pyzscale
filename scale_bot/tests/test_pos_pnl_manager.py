

from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime
from common.log_helper import LogHelper
from common.dt_helper import DTHelper
from md.instrument_manager import InstrumentManager
from scale_bot.pos_pnl_manager import PosPnlManager
import logging
import json
import os

from unittest.mock import MagicMock

instrument_date = "20240404"

trade_data = [
    ['1', 'oid-1', 11, 'MIDCPNIFTY24APRFUT', 'NFO', 8961538,
        'BUY', 'MIS', 10, 1, '2024-04-04 10:00:01'],

    ['2', 'oid-2', 12, 'MIDCPNIFTY24APRFUT', 'NFO', 8961538,
        'SELL', 'MIS', 10, 1, '2024-04-04 10:00:02'],

    ['3', 'oid-2', 12, 'MIDCPNIFTY24APRFUT', 'NFO', 8961538,
        'SELL', 'MIS', 10, 1, '2024-04-04 10:00:03'],

    ['4', 'oid-3', 13, 'NIFTY24APRFUT', 'NFO', 13368834,
        'BUY', 'MIS', 9, 1, '2024-04-04 10:00:01'],
   
    ['5', 'oid-4', 14, 'NIFTY24APRFUT', 'NFO', 13368834,
        'SELL', 'MIS', 10, 1, '2024-04-04 10:00:02'],
   
    ['6', 'oid-5', 15, 'NIFTY24APRFUT', 'NFO', 13368834,
        'SELL', 'MIS', 10, 1, '2024-04-04 10:00:03'],
   
    ['7', 'oid-6', 16, 'NIFTY24APRFUT', 'NFO', 13368834,
        'BUY', 'MIS', 9, 1, '2024-04-04 10:00:03'],

    ['8', 'oid-7', 17, 'MIDCPNIFTY24APRFUT', 'NFO', 8961538,
        'BUY', 'MIS', 10, 1, '2024-04-04 10:00:03'],
]
strat_order_ids = {
    'oid-1': 's-1',
    'oid-2': 's-1',
    'oid-3': 's-1',
    'oid-4': 's-1',
    'oid-5': 's-1',
    'oid-6': 's-1',
    'oid-7': 's-1',
}

order_data = [
    ['oid-1', 'MIDCPNIFTY24APRFUT', 8961538, 'BUY', 'COMPLETE',    9, 1, 10, 0, 1, 0, 'x'],
    ['oid-2', 'MIDCPNIFTY24APRFUT', 8961538, 'SELL', 'CANCELLED', 10, 2, 11, 1, 1, 1, 'x'],

    ['oid-3', 'NIFTY24APRFUT',     13368834, 'BUY', 'COMPLETE',   9, 1, 10, 0, 1, 0, 'x'],
    ['oid-4', 'NIFTY24APRFUT',     13368834, 'SELL', 'COMPLETE',  9, 1, 10, 0, 1, 0, 'x'],    
    ['oid-5', 'NIFTY24APRFUT',     13368834, 'SELL', 'COMPLETE', 10, 1, 10, 0, 1, 0, 'x'],       
    ['oid-6', 'NIFTY24APRFUT',     13368834, 'BUY', 'COMPLETE',   9, 1, 10, 0, 1, 0, 'x'],          

    ['oid-7', 'MIDCPNIFTY24APRFUT', 8961538, 'BUY', 'COMPLETE',   9, 1, 10, 0, 1, 0, 'x'],
]

class MockKConn:
    def __init__(self) -> None:
        self.num = 1
        self.trds = self.fill_trades()
        self.ords = self.fill_orders()

    def fill_trades(self):
        trades = []
        for t in trade_data:
            trade = {}
            trade['trade_id'] = t[0]
            trade['order_id'] = t[1]
            trade['exchange_order_id'] = t[2]
            trade['tradingsymbol'] = t[3]
            trade['exchange'] = t[4]
            trade['instrument_token'] = t[5]
            trade['transaction_type'] = t[6]
            trade['product'] = t[7]
            trade['average_price'] = t[8]
            trade['filled'] = t[9]
            trade['fill_timestamp'] = t[10]
            trade['order_timestamp'] = t[10]
            trade['exchange_timestamp'] = t[10]
            trades.append(trade)
        return trades

    def fill_orders(self):
        orders = []
        for o in order_data:
            order = {}
            order['order_id'] = o[0]
            order["tradingsymbol"] = o[1]
            order["exchange"] = 'NFO'
            order["instrument_token"] = o[2]
            order["transaction_type"] = o[3]
            order["order_type"] = 'MARKET'
            order["status"] = o[4]
            order["price"] = o[5]
            order["quantity"] = o[6]
            order["average_price"] = o[7]
            order["pending_quantity"] = o[8]
            order["filled_quantity"] = o[9]
            order["cancelled_quantity"] = o[10]
            order["order_timestamp"] = '2024-04-04 10:00:03'
            order["exchange_timestamp"] = '2024-04-04 10:00:03'
            order["status_message"] = o[11]
            orders.append(order)
        return orders

    def orders(self):
        ords = self.ords[0:self.num]
        self.num = min(len(self.ords), self.num + 1)
        return ords

    def trades(self):
        trds = self.trds[0:self.num]
        self.num = min(len(self.trds), self.num + 1)
        return trds

"""
run_tests
"""
def run_tests(instr_mgr, kconn):
    ppmgr = PosPnlManager(botuuid="TEST123", instr_mgr=instr_mgr, kconn=kconn, sig_handler=None)
    ppmgr._get_ltp = MagicMock(return_value=10)
    ppmgr._get_order_id_to_strat_id_map = MagicMock(return_value=strat_order_ids)
    ppmgr.start()


def main():
    def valid_cred_file(parser: ArgumentParser, arg: str):
        if not os.path.exists(arg):
            parser.error(f"The file {arg} does not exist!")
        else:
            return open(arg, 'r')

    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument("-i", "--inspath",
                        default=f"/home/qoptrprod/data/dumps")
    args = parser.parse_args()

    LogHelper.configure_logging(verbose=True)

    today = instrument_date
    instr_path = Path(args.inspath) / today
    instrument_file = instr_path / f"instrument-{today}.dat"
    inst_mgr = InstrumentManager(instrument_file)

    kconn = MockKConn()
    run_tests(instr_mgr=inst_mgr, kconn=kconn)


if __name__ == "__main__":
    main()
