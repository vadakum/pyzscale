

from common.bin_file_stream import BinFileStream
from common.dt_helper import DTHelper
from md.instrument_manager import InstrumentManager, InstrumentType
from md.scale_option_chain import ScaleOptionChain
from modelservice.scale_alpha import ScaleAlpha
from backtest.scale_backtest_args import ScaleBacktestArgs, SBKeys
from backtest.scale_backtest_common import *
from modelservice.alpha_consts import SignalDirection
from backtest.oc_data_reader import OCDataReader

from dataclasses import asdict
import logging


class ScaleChainReader:
    def __init__(self, argwrap: ScaleBacktestArgs) -> None:
        self.argwrap = argwrap
        ''' create the data reader '''
        self.strat_common_args = argwrap.bt_args[SBKeys.common.value]
        self.start_time = str(self.strat_common_args[SBKeys.start_time])
        self.end_time = str(self.strat_common_args[SBKeys.end_time])
        self.inst_mgr = InstrumentManager(inst_file=argwrap.instrument_file, 
                                          trading_date=argwrap.trading_date)

    """
    read_chain single read
    """
    def read_chain(self):
        self.data_reader = OCDataReader(self.argwrap.dump_file, self.start_time, self.end_time)        
        while True:
            msg = self.data_reader.read()
            if not msg:
                return None
            yield ScaleOptionChain(msg=msg, inst_mgr=self.inst_mgr)
