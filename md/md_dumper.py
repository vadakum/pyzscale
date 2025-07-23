

from dataclasses import dataclass
from pathlib import Path
from common.walrus_redis import *
from common.bin_file_stream import BinFileStream

import logging
import signal
import time


ProgressMessageIntervalInSec = 15 * 60  # mins converted to seconds

"""
DumperArgs
"""


@dataclass
class DumperArgs:
    stream_names_lookup_key: str = "prod.daily.mdstreams.set.v1"
    dump_path: str = ""


"""
MarketDataDumper
"""


class MarketDataDumper:
    def __init__(self, args: DumperArgs) -> None:
        self.args = args
        self._register_signals()
        self.wm = WalrusManager()
        self.run_dumper = True
        self.stream_names = self._get_stream_names()
        if not self.stream_names:
            msg = "Stream Names not configured yet! May be md is down!"
            logging.error(msg)
            raise msg
        self.wnet_streams: list[WStreamReader] = []
        self.fbin_streams: list[BinFileStream] = []
        self._create_streams()
        self.last_log_time = 0

    def _get_stream_names(self):
        wm_db = self.wm.get()
        if wm_db.hash_exists(self.args.stream_names_lookup_key):
            h = wm_db.Hash(self.args.stream_names_lookup_key)
            stream_names = [stream_name.decode() for (ul, stream_name) in h]
            return stream_names
        return None

    def _create_streams(self):
        for stream_name in self.stream_names:
            self.wnet_streams.append(WStreamReader(
                self.wm, stream_name, WReaderType.Latest))
            dump_file = Path(self.args.dump_path) / f"{stream_name}.dat"
            logging.info(f"Creating dump file: {dump_file}")
            self.fbin_streams.append(BinFileStream(dump_file, "wb+"))

    def _stop_process(self, signum, frame):
        logging.info(f"Dumper stop called with signal {signum} !")
        self.run_dumper = False

    def _register_signals(self):
        signal.signal(signal.SIGUSR1, self._stop_process)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    def start(self):
        num_messages = 0
        while self.run_dumper:
            for idx, wstream in enumerate(self.wnet_streams):
                payload = wstream.fetch_one_nb()
                if payload:
                    timestamp: bytes = payload[b't']
                    data: bytes = payload[b'v']
                    self.fbin_streams[idx].write(timestamp)
                    self.fbin_streams[idx].write(data)
                    num_messages += 1

            time_elapsed = time.time() - self.last_log_time
            if time_elapsed > ProgressMessageIntervalInSec:
                logging.info(f"Messages saved till now = {num_messages}")
                self.last_log_time = time.time()
        # Closing the dumper
        logging.info(f"Messages saved till now = {num_messages}")
        logging.info("Closing all files...")
        for f_stream in self.fbin_streams:
            f_stream.close()
