
from common.walrus_redis import WalrusManager
from scale_bot.mp_sighandler import MultiProcSignalHandler

from md.instrument_manager import InstrumentManager
from scale_bot.bot_utils import BotUtils
from scale_bot.bot_common import *
from scale_bot.api_rate_limiter import ServiceApiRateLimiter
from multiprocessing import Process

from kiteconnect import KiteConnect
import time
import json
import logging
import tabulate
import asyncio

CheckTimeInSec = 3
LogStatusIntervalSec = 3 * 60

"""
PosPnlManager
"""


class PosPnlManager(Process):
    def __init__(
        self,
        botuuid: str,
        instr_mgr: InstrumentManager,
        kconn: KiteConnect,
        sig_handler: MultiProcSignalHandler
    ) -> None:
        super().__init__()

        self.botuuid = botuuid
        self.instr_mgr = instr_mgr
        self.kconn = kconn
        self.sig_handler = sig_handler
        self.wdb = WalrusManager().get()

        ltp_hash_key = BotRedisKeyHelper.get_ltp_hash_key()
        strat_pos_hash_key = BotRedisKeyHelper.get_strat_pos_hash_key(botuuid)
        order_info_hash_key = BotRedisKeyHelper.get_order_info_hash_key(botuuid)
        strat_order_hash_key = BotRedisKeyHelper.get_strat_order_hash_key(
            botuuid)

        self.wdb_ltp_hash = self.wdb.Hash(ltp_hash_key)
        self.wdb_strat_order_hash = self.wdb.Hash(strat_order_hash_key)
        self.wdb_strat_pos_hash = self.wdb.Hash(strat_pos_hash_key)
        self.wdb_order_info_hash = self.wdb.Hash(order_info_hash_key)

        logging.info(f"PosPnlManager: LTP Hash:       {ltp_hash_key}")
        logging.info(f"PosPnlManager: StratOrder Hash:{strat_order_hash_key}")        
        logging.info(f"PosPnlManager: Port Hash:      {strat_pos_hash_key}")
        logging.info(f"PosPnlManager: OrderInfo Hash: {order_info_hash_key}")
        self.last_log_time = time.time()


    def _get_order_id_to_strat_id_map(self) -> dict[str, str]:
        """ self.wdb_strat_order_hash is filled by the strategy process """
        return {o.decode(): s.decode() for (o, s) in self.wdb_strat_order_hash}

    def _convert_to_order_book_dict(self, order_book):
        """ 
        - Convert the list of OrderInfo to dict form
        - Note: `OrderInfo.strat_id` is not getting filled here, it will be filled 
                 later
        """
        order_info_dict = {}
        for order in order_book:
            oinfo = OrderInfo()
            oinfo.order_id = order["order_id"]
            oinfo.tradingsymbol = order["tradingsymbol"]
            oinfo.exchange = order["exchange"]
            oinfo.instrument_token = order["instrument_token"]
            oinfo.transaction_type = order["transaction_type"]
            oinfo.order_type = order["order_type"]
            oinfo.order_status = order["status"]
            oinfo.price = order["price"]
            oinfo.quantity = order["quantity"]
            oinfo.average_price = order["average_price"]
            oinfo.pending_quantity = order["pending_quantity"]
            oinfo.filled_quantity = order["filled_quantity"]
            oinfo.cancelled_quantity = order["cancelled_quantity"]
            oinfo.order_timestamp = order["order_timestamp"]
            oinfo.exchange_timestamp = order["exchange_timestamp"]
            msg = order["status_message"]
            if msg:
                oinfo.message = msg
            order_info_dict[oinfo.order_id] = oinfo
        return order_info_dict

    """
    fetch orders using api
    """

    async def _fetch_order_infos(
        self,
        bot_order_id_strat_map: dict[str, str]
    ) -> tuple[dict[str, OrderInfo], bool]:
        """
        Retrun orderid -> OrderInfo dict and reconciliation status
        Status: 
        True -> all strategy orders have been reconciled
        False : there are missing orders, caller can retry
        """
        # https://kite.trade/docs/connect/v3/orders/#retrieving-orders

        order_book = []
        try:
            order_book = await ServiceApiRateLimiter.call_api(
                lambda: self.kconn.orders())
        except Exception as ex:
            logging.error("Exception in calling method: self.kconn.orders")

        broker_book_dict = self._convert_to_order_book_dict(order_book)

        missing_order_ids = []
        order_info_dict: dict[str, OrderInfo] = {}
        
        bot_order_ids = bot_order_id_strat_map.keys()
        for strat_oid in bot_order_ids:
            if strat_oid in broker_book_dict:
                # Found the strategy order id in the broker order book
                # Copy the over OrderInfo from broker book and set the stratgy id
                order_info_dict[strat_oid] = broker_book_dict[strat_oid]
                order_info_dict[strat_oid].strat_id = bot_order_id_strat_map[strat_oid]
            else:
                missing_order_ids.append(strat_oid)

        if time.time() - self.last_log_time > LogStatusIntervalSec:
            logging.info(
                f"PosPnlManager orders : reconciled={len(order_info_dict.keys())},"
                f" missing={len(missing_order_ids)}"
            )
        return (order_info_dict, (len(missing_order_ids) == 0))

    """
    fetch trades using api. 
    Fetch the trades that are sent by the current
    instance of bot. We are handling bot specific orders and trades
    """

    async def _fetch_trades_infos(self, bot_order_id_strat_map: dict[str, str]) -> list[TradeInfo]:
        trade_infos = []
        all_trades = await ServiceApiRateLimiter.call_api(
            lambda: self.kconn.trades())
        for trade in all_trades:
            order_id = trade["order_id"]
            if order_id not in bot_order_id_strat_map:
                continue
            ti = TradeInfo()
            ti.order_id = order_id
            ti.strat_id = bot_order_id_strat_map[order_id]
            ti.trade_id = trade["trade_id"]
            ti.exchange_order_id = trade["exchange_order_id"]
            ti.tradingsymbol = trade["tradingsymbol"]
            ti.exchange = trade["exchange"]
            ti.instrument_token = trade["instrument_token"]
            ti.transaction_type = trade["transaction_type"]
            ti.price = trade["average_price"]
            ti.fill_qty = trade["filled"]
            ti.fill_timestamp = trade["fill_timestamp"]
            ti.order_timestamp = trade["order_timestamp"]
            ti.exchange_timestamp = trade["exchange_timestamp"]
            trade_infos.append(ti)
        return trade_infos

    """
    calculate transaction cost
    """
    @staticmethod
    def calc_tcost(cost_instr_type: str, turnover: float) -> float:
        if not cost_instr_type or cost_instr_type not in TCost:
            logging.error(
                f"Unable to get cost, pnl computation will not include costs!"
            )
            return 0
        cost = TCost[cost_instr_type]
        tcost = turnover * cost
        return tcost

    """
    get instrument type for cost lookup
    """
    @staticmethod
    def get_instr_type_for_cost(inst: dict) -> str:
        cost_instr_type = None
        if InstrumentManager.is_options(inst):
            cost_instr_type = ExecInstType.NK_O.value
        elif InstrumentManager.is_futures(inst):
            cost_instr_type = ExecInstType.NK_F.value
        elif InstrumentManager.is_equity(inst):
            cost_instr_type = ExecInstType.NK_E.value
        return cost_instr_type

    """
    compute pnl
    """
    @staticmethod
    def compute_pnl(oi: OrderInfo, pos: RunningPos) -> None:
        trd_value = oi.average_price * oi.filled_quantity
        if oi.transaction_type == TransactionType.BUY:
            pos._buy_value += trd_value
            pos._buy_qty += oi.filled_quantity
            pos._buy_avg_px = pos._buy_value / pos._buy_qty
            pos.buy_total_value += trd_value
            pos.buy_total_qty += oi.filled_quantity
        elif oi.transaction_type == TransactionType.SELL:
            pos._sell_value += trd_value
            pos._sell_qty += oi.filled_quantity
            pos._sell_avg_px = pos._sell_value / pos._sell_qty
            pos.sell_total_value += trd_value
            pos.sell_total_qty += oi.filled_quantity

        # Update net fields
        pos.netpos = pos.buy_total_qty - pos.sell_total_qty
        pos._running_cost = PosPnlManager.calc_tcost(
            pos.cost_instr_type, turnover=(pos._buy_value + pos._sell_value)
        )
        pos._running_cost += PerOrderCost * pos.num_orders

        upnl = 0
        if pos.netpos == 0:
            total_to = pos.buy_total_value + pos.sell_total_value
            total_cost = PosPnlManager.calc_tcost(
                pos.cost_instr_type, total_to)
            total_cost += PerOrderCost * pos.num_orders
            pos.total_tcost = total_cost
            pos.pnl_realized = (
                pos.sell_total_value - pos.buy_total_value
            ) - pos.total_tcost
            pos.reset_pos_accu()
        else:
            if pos.netpos > 0:
                # unrealized pnl
                prob_sell_px = pos.ltp
                unit_qty_cost = (
                    PosPnlManager.calc_tcost(
                        pos.cost_instr_type, prob_sell_px) + PerOrderCost
                )
                unit_pnl = prob_sell_px - pos._buy_avg_px - unit_qty_cost
                upnl = (unit_pnl * pos.netpos) - pos._running_cost
                # for cases when net pos jumps without becomeing 0
                upnl += pos._sell_qty * (pos._sell_avg_px - pos._buy_avg_px)
            elif pos.netpos < 0:
                prob_buy_px = pos.ltp
                unit_qty_cost = (
                    PosPnlManager.calc_tcost(
                        pos.cost_instr_type, prob_buy_px) + PerOrderCost
                )
                unit_pnl = pos._sell_avg_px - prob_buy_px - unit_qty_cost
                upnl = (-1 * unit_pnl * pos.netpos) - pos._running_cost
                # for cases when net pos jumps without becomeing 0
                upnl += pos._buy_qty * (pos._sell_avg_px - pos._buy_avg_px)

        pos.pnl_unrealized = upnl
        pos.netpnl = pos.pnl_realized + pos.pnl_unrealized
        pos.total_tcost += pos._running_cost

    """
    get ltp from walrus
    """

    def _get_ltp(self, instrument_token) -> float:
        bltp = self.wdb_ltp_hash.get(instrument_token)
        if not bltp:
            logging.error(f"LTP nor found for id:{instrument_token}")
            return 0
        return float(bltp)

    """
    calculate portfolio position and pnl 
    """

    def _calc_strat_pos_pnl(self, order_infos: list[OrderInfo]) -> dict[str, StratPosPnl]:
        symb_run_pos: dict[str, RunningPos] = {}
        symb_order_ids: dict[str, set] = {}
        for oi in order_infos:
            inst = self.instr_mgr.get_instrument_def_from_id(
                oi.instrument_token)
            if not inst:
                logging.error(
                    f"Unable to find {oi.instrument_token} in instrument def !"
                )
                logging.error(f"Please stop trading and investigate")
                continue
            #
            # Create / fetch Pos object for the trading symbol
            # and update the pos + pnl states
            #
            if oi.tradingsymbol not in symb_run_pos:
                symb_order_ids[oi.tradingsymbol] = set()
                cost_instr_type = PosPnlManager.get_instr_type_for_cost(inst)
                symb_run_pos[oi.tradingsymbol] = RunningPos(
                    instrument_token=oi.instrument_token,
                    inst_name=oi.tradingsymbol,
                    ltp=self._get_ltp(oi.instrument_token),
                    cost_instr_type=cost_instr_type,
                )
            pos = symb_run_pos[oi.tradingsymbol]
            symb_order_ids[oi.tradingsymbol].add(oi.order_id)
            pos.num_orders = len(symb_order_ids[oi.tradingsymbol])
            PosPnlManager.compute_pnl(oi=oi, pos=pos)
        # Copy and Summarize at strategy level
        strat_pos_pnl = {
            symbol: running_pos.to_stratpospnl()
            for symbol, running_pos in symb_run_pos.items()
        }
        return strat_pos_pnl

    def _publish_strat_pos_pnl(self, strat_id: str, strat_pos_pnl: dict[str, StratPosPnl]):
        data = {symbol: v.to_json() for symbol, v in strat_pos_pnl.items()}
        self.wdb_strat_pos_hash.update({strat_id: json.dumps(data)})

    def _publish_order_infos(self, d: dict[str, OrderInfo]):
        for key, value in d.items():
            self.wdb_order_info_hash.update({key: value.to_json()})

    def _reset_log_time(self):
        if time.time() - self.last_log_time > LogStatusIntervalSec:
            self.last_log_time = time.time()

    async def get_recon_order_info_dict(self, bot_oid_sid_ref_map) -> dict[str, OrderInfo]:
        """ returns order_id to OrderInfo dict"""
        order_info_dict = {}
        for i in range(1, 5):
            (order_info_dict, is_reconciled) = await self._fetch_order_infos(
                bot_oid_sid_ref_map)
            if is_reconciled:
                break
            await asyncio.sleep(1)
        return order_info_dict

    async def async_run(self):
        await BotUtils.wait_till_market_opens("PosPnlManager")
        while self.sig_handler.keep_processing():
            # Get strategy order list
            bot_oid_sid_ref_map = self._get_order_id_to_strat_id_map()

            # Pull order info from broker
            order_info_dict = await self.get_recon_order_info_dict(bot_oid_sid_ref_map)

            # Calculate bot portfolio position and pnl for each strategy
            unique_strat_ids = set(bot_oid_sid_ref_map.values())
            for strat_id in unique_strat_ids:
                order_infos_of_strat = [
                    oi for oi in order_info_dict.values() if oi.strat_id == strat_id]
                strat_pos_pnl = self._calc_strat_pos_pnl(order_infos_of_strat)
                self._publish_strat_pos_pnl(strat_id, strat_pos_pnl)
                if time.time() - self.last_log_time > LogStatusIntervalSec:
                    logging.info(
                        f"PosPnlManager: pos and pnl for strategy id:{strat_id}:\n"
                        f"{tabulate.tabulate(strat_pos_pnl.values(), headers='keys')}\n")
            # publish order infos
            self._publish_order_infos(order_info_dict)
            self._reset_log_time()
            await asyncio.sleep(CheckTimeInSec)
        logging.info("PosPnlManager loop exited !")

    """
    Process.run
    """

    def run(self):
        with asyncio.Runner(debug=None) as runner:
            runner.run(self.async_run())
