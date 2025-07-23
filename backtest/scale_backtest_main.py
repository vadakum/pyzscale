

from argparse import ArgumentParser
from common.log_helper import LogHelper
from backtest.scale_backtest_args import ScaleBacktestArgGen
from backtest.scale_backtest import ScaleBacktest

import logging
import sys

DefaultBtArgs = {
    'common': {
        'start_time': '09:15:01',
        'end_time' : '15:25:10',
    },
    'alpha': {
        'sigmult' : 0.5,
        'smoother' : {
            'TS' : {'enabled': True , 'type' : 'STABLEWIN' , 'timeperiod' : 3 * 60 },
            'UL' : {'enabled': True, 'type' : 'EMA' , 'timeperiod' : 3 * 60 },
            'CP' : {'enabled': False, 'type' : 'AGG' , 'timeperiod' : 3 * 60 },            
        }
    },
    'execution': {
        'exec_instr_type' : 'NK_F',        
        'price_type' : 'CROSS', 
        'opt_trd_offset' : 2,
        'quote_lots' : 1,
        'stop_loss': 0,
        'max_loss' : 0,
    }
}

def main():
    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument("-d", "--dump-basedir", default="./dumps/")
    parser.add_argument("-t", "--trading-date", help="YYYMMDD", type=str)
    parser.add_argument("-u", "--underlying", help="BANKNIFTY_I", type=str)
    parser.add_argument("-n", "--dump-name", help="Use this file name after resolving the directory", type=str,
                        default=None)
    LogHelper.add_log_path_argument(parser)
    args = parser.parse_args()

    # LogHelper.configure_logging(
    #     verbose=args.verbose,
    #     log_name_prefix="md_dumper",
    #     log_path=args.log_path,
    #     console=False)
    LogHelper.configure_logging(verbose=args.verbose)

    dump_base_dir = args.dump_basedir
    trading_date = args.trading_date
    underlying = str(args.underlying).upper()
    optional_dump_file_name = args.dump_name  # optional

    try:
        bt_args = ScaleBacktestArgGen.resolve_and_gen_args(
            dump_base_dir=dump_base_dir,
            underlying=underlying,
            trading_date=trading_date,
            bt_args=DefaultBtArgs,
            optional_dump_file_name=optional_dump_file_name
        )
        bt = ScaleBacktest(bt_args)
        bt.print_result(bt.run_bt())
    except Exception as ex:
        logging.exception(ex)
        sys.exit(1)


if __name__ == '__main__':
    main()
