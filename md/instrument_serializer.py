

from kiteconnect import KiteConnect

import json

class InstrumentSerializer:
    def __init__(self, kconn : KiteConnect) -> None:
        '''
        exchange: (NSE, BSE, NFO, CDS, BCD, MCX)
        '''
        self.instrument_cache = kconn.instruments()

    def write(self, file_name):
        with open(file_name, "w+") as ins_stream:
            for instrument in self.instrument_cache:
                ins_stream.write(json.dumps(instrument, default=str) + '\n')

