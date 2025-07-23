

import logging
import os
from common.dt_helper import DTHelper
from datetime import datetime
from argparse import ArgumentParser


class LogHelper:
    @staticmethod
    def add_log_path_argument(parser: ArgumentParser):
        """
        add argument [-l / --log-path ] to commandline args
            with default and help
        """
        parser.add_argument("-l", "--log-path",
                            default=f"{os.path.join(os.path.expanduser('~'),'logs')}",
                            help=f"if LOG_PATH is not a full path, then {os.path.expanduser('~')}/<LOG_PATH> should exist")

    @staticmethod
    def configure_logging(verbose: bool,
                          log_name_prefix=None,
                          log_path=None,
                          console=False,
                          format=None) -> None:
        logging_level = logging.DEBUG if verbose else logging.INFO
        """
        Log to file or console
        """
        if console or not log_name_prefix or not log_path:
            logging.basicConfig(
                format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s - %(message)s',
                datefmt='%Y%m%d %I:%M:%S %p',
                level=logging_level)
            return
        """
        Create/Open(in append mode) log file: 
            <log_path>/<log_name_prefix>_<yyyymmdd>.log
        """
        today = DTHelper.to_yyyymmdd(datetime.now())
        log_name = f"{log_name_prefix}_{today}.log"
        log_file_with_path = ""
        if log_path[0] == '/':
            log_file_with_path = os.path.join(log_path, log_name)
        else:
            log_file_with_path = os.path.join(
                os.path.expanduser("~"), log_path, log_name)

        log_format = '%(asctime)s %(levelname)s %(filename)s:%(lineno)s - %(message)s' 
        if format:
            log_format = format
        logging.basicConfig(
            filename=log_file_with_path,
            filemode="a",
            format= log_format,
            datefmt='%Y%m%d %I:%M:%S %p',
            level=logging_level)
