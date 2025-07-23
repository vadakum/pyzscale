

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from common.log_helper import LogHelper
from common.dt_helper import DTHelper
from md.md_dumper import MarketDataDumper, DumperArgs
from md.md_consts import MDStreamNamesLookup

import logging
import sys

def main():
    parser = ArgumentParser()
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument("-d", "--dump-path", default="./dumps/")
    LogHelper.add_log_path_argument(parser)
    args = parser.parse_args()

    # LogHelper.configure_logging(verbose=False)
    LogHelper.configure_logging(
        verbose=args.verbose,
        log_name_prefix="md_dumper",
        log_path=args.log_path,
        console=False)

    try:
        today = DTHelper.to_yyyymmdd(datetime.now())
        dump_path = Path(args.dump_path) / today
        dump_path.mkdir(parents=True, exist_ok=True)

        dumper_args = DumperArgs(dump_path=dump_path,
                                 stream_names_lookup_key=MDStreamNamesLookup)
        mdd = MarketDataDumper(dumper_args)
        mdd.start()
    except Exception as ex:
        logging.exception(ex)
        sys.exit(1)


if __name__ == '__main__':
    main()
