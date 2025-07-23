

from common.algo_helper import AlgoHelper
from md.instrument_manager import (
    InstrumentManager,
    InstField,
)
from md.feed_container import FeedContainer
from md.option_chain_pub import OptionChainPub
from md.sub_unsub_const import SubUnsubKeys
from kite_wrap.kite_connection import ClientConnection
from common.walrus_redis import WalrusManager
from kite_wrap.websock_client import WebsockConfig
from md.md_consts import *

from typing import Final
import multiprocessing as mp
import time
import queue
import logging


QReadSleepInMicro: Final = 3.0/1000000.0


class FeedProcessManager:
    """
    FeedProcessManager
    """
    def __init__(self,
                 conn: ClientConnection,
                 wm: WalrusManager,
                 inst_mgr: InstrumentManager,
                 oc_config_list: list) -> None:

        self.instr_to_chain_map: dict[int, OptionChainPub] = {}
        self.chain_to_su_q: dict[OptionChainPub, mp.Queue] = {}
        self.tick_queues: list[mp.Queue] = []
        self.feed_containers: list[FeedContainer] = []
        pub_stream_names_hash = wm.get().Hash(MDStreamNamesLookup)

        all_chains = [OptionChainPub(inst_mgr=inst_mgr,
                                     wm=wm,
                                     config=config)
                      for config in oc_config_list]
        llchain: list[list[OptionChainPub]] = list(
            AlgoHelper.list_chunks(all_chains, MaxConnPerAlgoKey))
        for lchain in llchain:
            # One FeedContainer can handle a block of chains
            for chain in lchain:
                tick_q = mp.Queue()
                su_q = mp.Queue()
                inst_ids = chain.get_interested_instruments()
                self.feed_containers.append(FeedContainer(
                    tick_q=tick_q,
                    su_q=su_q,
                    instrument_ids=inst_ids,
                    ws_config=WebsockConfig(
                        api_key=conn.get().api_key, access_token=conn.get().access_token)
                ))
                # Update internal mapping
                self.tick_queues.append(tick_q)
                for inst_id in inst_ids:
                    self.instr_to_chain_map[inst_id] = chain
                self.chain_to_su_q[chain] = su_q
                (chain_ul, chain_stream_name) = chain.get_stream_ul_and_name()
                pub_stream_names_hash.update({chain_ul: chain_stream_name})
                logging.info(
                    f"Registering optsy={chain_ul} stream={chain_stream_name} "
                    f"to redis set:{MDStreamNamesLookup}")
    """
    collect ticks from ipc queues
    """
    def _fetch_ticks_from_queues(self):
        ticks = []
        for tick_q in self.tick_queues:
            try:
                t = tick_q.get_nowait()
                ticks.extend(t)
            except queue.Empty:
                continue
        # if all queues are empty we will avoid cpu throttle            
        if not ticks:
            time.sleep(QReadSleepInMicro)
        return ticks

    """
    delegate the tick to chain and track subscriptions
    """
    def _process_tick(self, tick):
        if InstField.InstrumentToken not in tick:
            return
        # We should this incoming instrument in our
        # maps
        inst_id = tick[InstField.InstrumentToken]
        if inst_id not in self.instr_to_chain_map:
            return
        # Get associated chain with instrument id
        chain = self.instr_to_chain_map[inst_id]
        sun = chain.process_tick_update(tick)
        # Update internal mapping with new sub-unsub list
        sub_list = sun[SubUnsubKeys.Sub][SubUnsubKeys.InstIds]
        unsub_list = sun[SubUnsubKeys.Unsub][SubUnsubKeys.InstIds]
        for id in sub_list:
            self.instr_to_chain_map[id] = chain
        for id in unsub_list:
            if id in self.instr_to_chain_map:
                del self.instr_to_chain_map[id]
        # Send the sub-unsub list upstream
        if sub_list or sub_list:
            logging.debug(f"Adding to su queue: {sun}")
            self.chain_to_su_q[chain].put(sun)

    """
    inprocess queue consumer
    """

    def _process_queues(self):
        logging.debug("Monitoring ws output queue...")
        time.sleep(2)
        while True:
            for tick in self._fetch_ticks_from_queues():
                self._process_tick(tick)

    """
    multiprocess container
    """

    def _start_container_processes(self):
        for i, feed_container in enumerate(self.feed_containers):
            logging.debug(f"Creating feed container: {i}")
            feed_container.start()

    """
    start multiprocess containers and in process queue consumer
    """

    def start(self):
        self._start_container_processes()
        self._process_queues()
