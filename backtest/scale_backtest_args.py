

from common.dt_helper import DTHelper
from enum import StrEnum, auto
from pathlib import Path
from dataclasses import dataclass, field


"""
Key names for Scale Backest Dynamic args
"""


class SBKeys(StrEnum):
    ''' The main section'''
    common = auto()
    alpha = auto()
    execution = auto()
    ''' common : keys '''
    start_time = auto()
    end_time = auto()
    ''' execution keys '''
    exec_instr_type = auto()
    price_type = auto()
    opt_trd_offset = auto()
    quote_lots = auto()
    profit_target = auto()


"""
Run Args
"""


@dataclass
class ScaleBacktestArgs:
    dump_file: str = ""
    instrument_file: str = ""
    trading_date: str = ""
    opt_symbol: str = ""
    bt_args: dict = field(default_factory=dict)


"""
Helper class
"""


class ScaleBacktestArgGen:
    @staticmethod
    def resolve_and_gen_args(
            dump_base_dir: str,
            underlying: str,
            trading_date: str,
            bt_args: dict,
            optional_dump_file_name: str = None) -> ScaleBacktestArgs:

        if not DTHelper.validate_date(trading_date):
            raise ValueError(f"Invalid trading date {trading_date} passed.")

        dump_with_path = None
        if optional_dump_file_name:
            dump_with_path = Path(dump_base_dir) / \
                Path(trading_date) / optional_dump_file_name
        else:
            dump_with_path = Path(
                dump_base_dir) / Path(trading_date) / f"CHAIN_{underlying.upper()}_{trading_date}.dat"
        instrument_file = Path(
            dump_base_dir) / Path(trading_date) / f"instrument-{trading_date}.dat"

        if not dump_with_path.exists():
            raise ValueError(f"Dump file {dump_with_path} does not exist!")
        if not instrument_file.exists():
            raise ValueError(
                f"Instrument file {instrument_file} does not exist!")

        opt_symbol = underlying.upper().split('_')[0]

        return ScaleBacktestArgs(
            dump_file=dump_with_path,
            instrument_file=instrument_file,
            trading_date=trading_date,
            opt_symbol=opt_symbol,
            bt_args=bt_args
        )
