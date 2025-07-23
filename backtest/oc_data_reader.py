

from common.bin_file_stream import BinFileStream
from common.dt_helper import DTStartEndTimeManager
from typing import Union
import zlib
import json


class OCDataReader:
    def __init__(self, dump_file, start_time, end_time) -> None:
        self.dump_file = dump_file
        self.dts = DTStartEndTimeManager(
            start_time=start_time, end_time=end_time)
        ''' now open the stream file'''
        self.bin_stream = BinFileStream(self.dump_file, "rb")
        self.is_started = False

    def _reached_start_time(self, refts: int):
        return self.dts.reached_start_time(refts)

    def _crossed_end_time(self, refts: int):
        return self.dts.crossed_end_time(refts)

    """
    dump custom read wrapper
    """

    def _read_dump_record(self, bin_stream: BinFileStream) -> Union[tuple[int, dict] | None]:
        tsbytes = bin_stream.read()
        if not tsbytes:
            return None
        payload = bin_stream.read()
        if not payload:
            return None
        ts = int(tsbytes)
        msg = json.loads(zlib.decompress(payload))
        return (ts, msg)

    """
    read loop wrapper
    """

    def process(self, process_cb, last_cb=None):
        numrec = 0
        last_msg_obj = None
        while True:
            rec = self._read_dump_record(self.bin_stream)
            if not rec:
                break
            (ts, msg_obj) = rec
            if not self.is_started:
                if not self._reached_start_time(ts):
                    continue
                else:
                    self.is_started = True
            last_msg_obj = msg_obj
            if self._crossed_end_time(ts):
                break
            process_cb(msg_obj)
            numrec += 1
        self.bin_stream.close()
        # M2M
        if last_msg_obj and last_cb:
            last_cb(last_msg_obj)
        print(f"Processed: {numrec} updates")

    """
    read single record
    """

    def read(self) -> Union[dict | None]:
        if not self.is_started:
            while True:
                rec = self._read_dump_record(self.bin_stream)
                if not rec:
                    return None
                (ts, msg_obj) = rec
                if not self._reached_start_time(ts):
                    continue
                else:
                    self.is_started = True
                    return msg_obj
        else:
            rec = self._read_dump_record(self.bin_stream)
            if not rec:
                return None
            (ts, msg_obj) = rec
            if self._crossed_end_time(ts):
                return None
            else:
                return msg_obj
