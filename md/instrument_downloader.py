

from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime
from common.log_helper import LogHelper
from common.dt_helper import DTHelper
from kite_wrap.kite_connection import ClientConnection
from md.instrument_serializer import InstrumentSerializer

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

    #LogHelper.configure_logging(verbose=True)
    LogHelper.configure_logging(
        verbose=args.verbose,
        log_name_prefix="instr_download",
        log_path=args.log_path,
        console=False)

    creds = json.load(args.credfile)

    today = DTHelper.to_yyyymmdd(datetime.now())
    instr_path = Path(args.inspath) / today
    instr_path.mkdir(parents=True, exist_ok=True)
    instrument_file = instr_path / f"instrument-{DTHelper.to_yyyymmdd(datetime.now())}.dat"
    logging.info(f"Downloading instrument definitions to : {instrument_file}")

    try:
        kconn = ClientConnection(creds=creds).get()
        InstrumentSerializer(kconn).write(instrument_file)
        logging.info("Download finished!")
    except ValueError as ex:
        logging.exception(ex)
        sys.exit(1)


if __name__ == "__main__":
    main()
