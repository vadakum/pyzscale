

from common.log_helper import LogHelper
from common.dt_helper import DTHelper
from kite_wrap.kite_connection import ClientConnection
from md.instrument_manager import InstrumentManager
from md.oc_market_data import OCMarketData
from common.walrus_redis import WalrusManager

from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime

import multiprocessing_logging
import logging
import json
import sys
import os


def main():
    def valid_cred_file(parser: ArgumentParser, arg: str):
        if not os.path.exists(arg):
            parser.error(f"The file {arg} does not exist!")
        else:
            return open(arg, 'r')

    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument("-c", "--credfile", default="./.creds.json", metavar="FILE",
                        type=lambda x: valid_cred_file(parser, x))
    parser.add_argument("-i", "--inspath", default=f"{os.path.expanduser('~')}/data/dumps/")
    LogHelper.add_log_path_argument(parser)
    args = parser.parse_args()
    #
    #LogHelper.configure_logging(verbose=False)
    #
    LogHelper.configure_logging(
        verbose=args.verbose,
        log_name_prefix="oc_md",
        log_path=args.log_path,
        console=False)
    multiprocessing_logging.install_mp_handler()

    logging.info(f"=== Strating OC Marketdata ===")
    creds = json.load(args.credfile)

    today = DTHelper.to_yyyymmdd(datetime.now())
    instr_path = Path(args.inspath) / today
    instrument_file = instr_path / f"instrument-{DTHelper.to_yyyymmdd(datetime.now())}.dat"

    try:
        conn = ClientConnection(creds=creds)
    except ValueError as ex:
        logging.exception(ex)
        sys.exit(1)

    inst_mgr = InstrumentManager(instrument_file)
    oc_config_list = [
        {
            'option_underlying': 'BANKNIFTY_I',
            'tradable': 'BANKNIFTY_F_0',
            'options': {'symbol': 'BANKNIFTY', 'expiry_ind': 0, 'numstrikes': 21},
        },
        {
            'option_underlying': 'NIFTY_I',
            'tradable': 'NIFTY_F_0',
            'options': {'symbol': 'NIFTY', 'expiry_ind': 0, 'numstrikes': 21},
        },
        {
            'option_underlying': 'MIDCPNIFTY_I',
            'tradable': 'MIDCPNIFTY_F_0',
            'options': {'symbol': 'MIDCPNIFTY', 'expiry_ind': 0, 'numstrikes': 21},
        },
        {
            'option_underlying': 'FINNIFTY_I',
            'tradable': 'FINNIFTY_F_0',
            'options': {'symbol': 'FINNIFTY', 'expiry_ind': 0, 'numstrikes': 21},
        }
    ]

    wm = WalrusManager()
    md = OCMarketData(
        conn=conn,
        wm=wm,
        inst_mgr=inst_mgr,
        oc_config_list=oc_config_list)
    md.start()


if __name__ == "__main__":
    main()
