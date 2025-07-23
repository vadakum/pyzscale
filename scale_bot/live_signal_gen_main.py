
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from common.log_helper import LogHelper
from common.dt_helper import DTHelper
from scale_bot.live_signal_gen import LiveSignalGen, LiveSignalGenArgs
from md.md_consts import MDStreamNamesLookup

import logging
import sys
import os

AlphaArgs = {
    'sigmult': 0.5,
    'smoother': {
        'TS': {'enabled': False, 'type': 'STABLEWIN', 'timeperiod': 0},
        'UL': {'enabled': True, 'type': 'EMA', 'timeperiod': 3 * 60},
        'CP': {'enabled': True, 'type': 'SMA', 'timeperiod': 3 * 60},
        'MACD' : {'enabled': True, 'dfast' : 2*60, 'dslow' : 5*60, 'dsig' : 3*60, 'timeperiod' : 'macd2' },
    }
}


def main():
    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument("-i", "--inspath",
                        default=f"{os.path.expanduser('~')}/data/dumps/")
    LogHelper.add_log_path_argument(parser)
    args = parser.parse_args()

    LogHelper.configure_logging(verbose=True)
    # LogHelper.configure_logging(
    #     verbose=args.verbose,
    #     log_name_prefix="live_sig_gen",
    #     log_path=args.log_path,
    #     console=False)

    try:
        today = DTHelper.to_yyyymmdd(datetime.now())
        instrument_file = Path(args.inspath) / \
            Path(today) / f"instrument-{today}.dat"
        if not instrument_file.exists():
            raise ValueError(
                f"Instrument file {instrument_file} does not exist!")

        live_sg_args = LiveSignalGenArgs(stream_names_lookup_key=MDStreamNamesLookup,
                                         instrument_file=instrument_file,
                                         trading_date=today,
                                         alpha_args=AlphaArgs)
        lsg = LiveSignalGen(live_sg_args)
        lsg.start()
    except Exception as ex:
        logging.exception(ex)
        sys.exit(1)


if __name__ == '__main__':
    main()
