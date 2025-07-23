

from common.log_helper import LogHelper
from common.dt_helper import DTHelper
from kite_wrap.kite_connection import ClientConnection
from md.instrument_manager import InstrumentManager
from scale_bot.trade_engine import TradeEngine, TradeEngineArgs
from scale_bot.pos_pnl_manager import PosPnlManager
from scale_bot.mp_sighandler import MultiProcSignalHandler

import multiprocessing_logging
from typing import Final
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from datetime import datetime
from signal import SIGTSTP, SIGINT, SIGUSR1
import logging
import json
import sys
import os

DoConsoleLog: Final = False

"""
scale bot main
"""


def main():
    def arg_load_file(parser: ArgumentParser, fname: str):
        if not os.path.exists(fname):
            parser.error(f"The file {fname} does not exist!")
        else:
            return open(fname, 'r')

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbose', 
                        default=False, 
                        action='store_true')
    
    parser.add_argument("-i", "--inspath",
                        default=f"/home/qoptrprod/data/dumps",
                        help="Instrument Path ")
    
    parser.add_argument("-c", "--credfile", 
                        required=True,
                        metavar="FILE",
                        type=lambda f: arg_load_file(parser, f),
                        help="Broker login credentials")
    
    parser.add_argument("-b", "--botconfig", 
                        required=True,
                        metavar="FILE",
                        type=lambda f: arg_load_file(parser, f),
                        help="Bot config")
    
    LogHelper.add_log_path_argument(parser)
    args = parser.parse_args()
    #
    # Signal Handler
    #
    sig_handler = MultiProcSignalHandler([SIGINT, SIGTSTP])
    #
    # We need bot_config to create log name
    #
    bot_config = json.load(args.botconfig)
    botuuid = bot_config['botuuid']
    #
    # Configure Logging
    #
    if DoConsoleLog:
        LogHelper.configure_logging(verbose=False)
    else:
        LogHelper.configure_logging(
            verbose=args.verbose,
            log_name_prefix=f"scale_{botuuid}",
            log_path=args.log_path,
            console=False,
            format= '%(asctime)s %(levelname)s - %(message)s')
    multiprocessing_logging.install_mp_handler()
    #
    # Log seperator for each
    #
    logging.info(f"=== Strating SCALE BOT ===")
    #
    # Process other command line args
    #
    creds = json.load(args.credfile)
    today = DTHelper.to_yyyymmdd(datetime.now())
    instr_path = Path(args.inspath) / today
    instrument_file = instr_path / f"instrument-{today}.dat"
    #
    # Instrument Manager
    #
    instr_mgr = InstrumentManager(instrument_file, trading_date=today)
    #
    # Broker Connection
    #
    try:
        kconn = ClientConnection(creds=creds).get()
    except ValueError as ex:
        logging.exception(ex)
        sys.exit(1)
    #
    # Launch PosPnl Manager
    #
    logging.info("Creating PosPnlManager process...")
    pos_pnl_proc = PosPnlManager(
        botuuid=bot_config['botuuid'],
        instr_mgr=instr_mgr,
        kconn=kconn,
        sig_handler=sig_handler)
    
    pos_pnl_proc.start()
    #
    # Start the Trading Engine
    #
    logging.info("Creating TradeEngine...")
    TradeEngine(
        targs=TradeEngineArgs(bot_config=bot_config),
        instr_mgr=instr_mgr,
        kconn=kconn,
        sig_handler=sig_handler
    ).start()
    #
    # Wait and Cleanup
    #
    logging.info("Waiting for pos pnl to stop")
    pos_pnl_proc.join()  
    logging.info("ScaleBot stopped.")


if __name__ == "__main__":
    main()
