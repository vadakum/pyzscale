

from common.walrus_redis import *
from scale_bot.iengine import IEngine
from scale_bot.mp_sighandler import MultiProcSignalHandler
from scale_bot.exec_context_manager import ExecContextManager
from scale_bot.bot_common import BotRedisKeyHelper, BotKeys

from md.instrument_manager import InstrumentManager
from md.scale_option_chain import ScaleOptionChain
from md.md_consts import MDStreamNamesLookup

from kiteconnect import KiteConnect
from dataclasses import dataclass, field
import signal

import logging
import json
import zlib
import asyncio


@dataclass
class TradeEngineArgs:
    """
    TradeEngineArgs
    """    
    stream_names_lookup_key: str = MDStreamNamesLookup
    bot_config: dict = field(default_factory=dict)


class TradeEngine(IEngine):
    """
    TradeEngine
    """    
    def __init__(self,
                 targs: TradeEngineArgs,
                 instr_mgr: InstrumentManager,
                 kconn: KiteConnect,
                 sig_handler: MultiProcSignalHandler
                 ) -> None:

        super().__init__(
            instr_mgr=instr_mgr,
            kconn=kconn,
            sig_handler=sig_handler)
        #
        # Managers
        #
        self.exec_cxt_mgr = ExecContextManager(
            bot_cfg=targs.bot_config,
            engine=self)
        #
        # Configure streams
        #
        self.stream_dict = TradeEngine._get_stream_dict(
            self.wm,
            targs.stream_names_lookup_key)
        if not self.stream_dict:
            raise ValueError("Streams not configured yet!")
        ctrl_stream_name = BotRedisKeyHelper.get_strat_control_stream_key(
            targs.bot_config[BotKeys.botuuid])
        logging.info(f"Available md streams : {self.stream_dict}")
        logging.info(f"Strategy control stream: {ctrl_stream_name}")
        self.wnet_readers = self.create_wnet_readers()
        self.wnet_ctrl_reader = self.create_wnet_ctrl_reader(ctrl_stream_name)
        logging.info("TradeEngine initialized")

    @staticmethod
    def _get_stream_dict(wm: WalrusManager, stream_names_lookup_key: str):
        """
        Fetch ul => stream name mapping
        """
        wm_db = wm.get()
        if wm_db.hash_exists(stream_names_lookup_key):
            h = wm_db.Hash(stream_names_lookup_key)
            return {ul.decode(): stream_name.decode() for (ul, stream_name) in h}
        return None


    def create_wnet_readers(self) -> list[AsyncRedisStreamReader]:
        """
        Create AsyncStream MD Readers
        """
        wnet_readers: list[AsyncRedisStreamReader] = []
        self.underlyings = self.exec_cxt_mgr.get_underlyings()
        for underlying in self.underlyings:
            logging.info(
                f"Configuring stream reading for: {underlying}")
            if underlying in self.stream_dict:
                stream_name = self.stream_dict[underlying]
                wnet_readers.append(AsyncRedisStreamReader(
                    redis=self.aioredis,
                    stream_name=stream_name,
                    start_from=WReaderType.Latest))
            else:
                logging.error(
                    f"Market data not available for {underlying}, skipping this channel")
        return wnet_readers

    def create_wnet_ctrl_reader(self, stream_name):
        """ 
        Create wnet strategy control stream 
        """
        return AsyncRedisStreamReader(
                redis=self.aioredis,
                stream_name=stream_name,
                start_from=WReaderType.Latest)

    async def _process_stream(self, reader: AsyncRedisStreamReader):
        """
        Per stream MD reader loop
        """
        logging.info(f"Starting stream reader {reader.get_name()}")
        while self.sig_handler.keep_processing():
            bdata = await reader.read()
            if not bdata:
                await asyncio.sleep(0.1)
                continue
            ts = bdata[b't'].decode()
            msg = json.loads(zlib.decompress(bdata[b'v']))
            up = ScaleOptionChain(msg, self.instr_mgr)
            if not await self.exec_cxt_mgr.process_update(up):
                logging.error(
                    f"Process update returned failed status! Stopping stream {reader.get_name()}")
                return
            await asyncio.sleep(0.01)

    async def _process_ctrl_stream(self, reader : AsyncRedisStreamReader):
        """ Loop for control stream """
        logging.info(f"Starting stream reader {reader.get_name()}")
        while self.sig_handler.keep_processing():
            bdata = await reader.read()
            if not bdata:
                await asyncio.sleep(0.5)
                continue
            ts = bdata[b't'].decode()
            msg = json.loads(bdata[b'v'])
            logging.info(f"Control message received: {msg}")
            await self.exec_cxt_mgr.process_ctrl_message(msg)
            await asyncio.sleep(0.3)

    async def _run_engine(self):
        """
        Run Engine - Launch engine tasks
        """
        try:
            async with asyncio.TaskGroup() as task_group:
                for reader in self.wnet_readers:
                    task_group.create_task(self._process_stream(reader))
                task_group.create_task(self._process_ctrl_stream(
                    self.wnet_ctrl_reader))
        except* TypeError as te:
            for errors in te.exceptions:
                logging.error(errors)
        except* Exception as ex:
            logging.error(ex.exceptions)
        await self.aioredis.aclose()

    def start(self):
        """
        Start the trade engine
        """
        with asyncio.Runner(debug=None) as runner:
            runner.run(self._run_engine())
        logging.info(f"Shutting down trade engine!")
