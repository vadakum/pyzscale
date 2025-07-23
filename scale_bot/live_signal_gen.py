

from dataclasses import dataclass, field
from pathlib import Path
from common.walrus_redis import *
from modelservice.comb_alpha import CombAlpha, CombSignal
from md.scale_option_chain import ScaleOptionChain
from md.instrument_manager import InstrumentManager, InstrumentType
from md.md_consts import MDStreamNamesLookup
from common.bcolors import BColors

from typing import Final
from dataclasses import asdict
import tabulate
import logging
import signal
import time
import json
import zlib
import os

SignalPrintInterval : Final = 10
SDUlKey : Final = 'underlying'

@dataclass 
class LiveSignalGenArgs:
    stream_names_lookup_key : str = MDStreamNamesLookup
    instrument_file : str = ""
    trading_date : str = ""
    alpha_args : dict = field(default_factory=dict)

class LiveSignalGen:
    def __init__(self, args : LiveSignalGenArgs) -> None:
        self.args = args
        self._register_signals()
        self.wm = WalrusManager()        
        stream_dict = self._get_stream_dict()
        if not stream_dict:
            msg = "Streams not configured yet! May be md is down!"
            logging.error(msg)
            raise msg
        
        self.inst_mgr = InstrumentManager(
            args.instrument_file, trading_date=args.trading_date)
        self.run_process = True        
        # 
        # Configure the lookup ds 
        #
        self.wnet_streams : list[WStreamReader] = []
        self.ul_names : list[str] = []
        self.ul_scale_alpha : dict[str, CombAlpha] = {}
        self.ul_signal : dict[str, dict] = {}
        for ul, stream_name in stream_dict.items():
            if ul not in ['NIFTY', 'BANKNIFTY']:
                continue
            logging.info(f"Configuring stream reading: {ul} => {stream_name}")                
            self.wnet_streams.append(WStreamReader(self.wm, stream_name, WReaderType.Latest))
            self.ul_names.append(ul)
            self.ul_scale_alpha[ul] = CombAlpha(args.alpha_args)
            sd = {}
            # first add underlying key, this is for controlling print order
            sd[SDUlKey] = ul 
            for k, v in asdict(CombSignal(valid=False)).items():
                sd[k] = v
            self.ul_signal[ul] = sd

    def _get_stream_dict(self):
        wm_db = self.wm.get()
        if wm_db.hash_exists(self.args.stream_names_lookup_key):
            h = wm_db.Hash(self.args.stream_names_lookup_key)
            return {ul.decode() : stream_name.decode() for (ul, stream_name) in h }
        return None

    def _register_signals(self):
        signal.signal(signal.SIGTSTP, self._stop_process)
        signal.signal(signal.SIGINT, self._stop_process)

    def _stop_process(self, signum, frame):
        logging.info(f"Process stop called with signal {signum} !")
        self.run_process = False

    def print_signal_map(self):
        os.system("clear")
        # for ul_name, signal in self.ul_signal.items():
        #     print(f"{ul_name} => {signal}")        
        print(f"{tabulate.tabulate(self.ul_signal.values(), headers='keys', tablefmt='simple_grid')}")

    def start(self):
        num_messages = 0
        last_print_time = time.time()
        while self.run_process:
            for idx, wstream in enumerate(self.wnet_streams):
                ul_name = self.ul_names[idx]
                payload = wstream.fetch_one_block()
                if payload:
                    timestamp = payload[b't'].decode() 
                    data : bytes = payload[b'v']
                    msg = json.loads(zlib.decompress(data))
                    md_up = ScaleOptionChain(msg, self.inst_mgr)
                    signal = self.ul_scale_alpha[ul_name].process_update(md_up)
                    if signal.valid:
                        sd = {}
                        sd[SDUlKey] = ul_name                        
                        for k, v in asdict(signal).items():
                            if v == 'BUY':
                                sd[k] = f"{BColors.OKGREEN}{v}{BColors.ENDC}"
                            elif v == 'SELL':
                                sd[k] = f"{BColors.RED}{v}{BColors.ENDC}"
                            else:
                                sd[k] = v
                        sd['k/2'] = md_up.get_opt_strike_gap() * 0.5
                        sd['lg'] = md_up.get_curr_md_time_lag()
                        self.ul_signal[ul_name] = sd
                    else:
                        if ul_name in self.ul_signal:
                            self.ul_signal[ul_name]['valid'] = False
                    num_messages += 1
            time.sleep(0.1)
            curr_time = time.time()
            if curr_time - last_print_time > SignalPrintInterval:
                self.print_signal_map()
                last_print_time = curr_time

        logging.info(f"Shutting down the process message processed = {num_messages}")
