

from common.dt_helper import DTStartEndTimeManager
from scale_bot.bot_common import *
from scale_bot.iengine import IEngine
from scale_bot.order_manager.order_manager import OrderManager
from scale_bot.order_manager.order_common import OrderParam, OrderDetails

from enum import StrEnum, auto
from datetime import datetime
import logging
import json
import time
import asyncio


class StratState(StrEnum):
    """
    StrategyState
    """
    Active = auto()
    SqOffInitiated = auto()
    SqOffCompleted = auto()
    Stopped = auto()


class BaseStrategy:
    """
    BaseStrategy
    """

    def __init__(
        self,
        botuuid,
        underlying,
        strat_cfg: dict,
        order_mgr: OrderManager,
        engine: IEngine,
    ) -> None:

        self.botuuid = botuuid
        self.underlying = underlying
        self.instr_mgr = engine.get_instrument_mgr()
        self.order_mgr = order_mgr
        #
        # DTS - config common section
        #
        common_args = strat_cfg[BotKeys.common]
        start_time = str(common_args[BotKeys.start_time])
        end_time = str(common_args[BotKeys.end_time])
        self.underlying = common_args[BotKeys.underlying]
        self.dts = DTStartEndTimeManager(
            start_time=start_time,
            end_time=end_time)
        #
        # Execution section of config
        #
        exec_cfg = strat_cfg[BotKeys.execution]
        self.strat_id = exec_cfg[BotKeys.strategy_id]
        # Extract common keys of execution section
        self.exchange = exec_cfg[BotKeys.exchange]
        self.product_type = exec_cfg[BotKeys.product_type]
        self.order_type = exec_cfg[BotKeys.order_type]
        # self.opt_trd_mness_offset = exec_cfg[BotKeys.opt_trd_offset]
        self.quote_lots = exec_cfg[BotKeys.quote_lots]
        self.max_pos = exec_cfg[BotKeys.max_pos]
        self.stop_loss = -1 * exec_cfg[BotKeys.stop_loss]
        self.profit_target = abs(self.stop_loss) * \
            exec_cfg[BotKeys.profit_target]
        #
        # Validate
        #
        if self.exchange not in set(item.value for item in Exchange):
            raise ValueError(f"Exchange name error in args {exec_cfg}")
        if self.product_type not in set(item.value for item in ProductType):
            raise ValueError(f"Product type error in args {exec_cfg}")
        if self.order_type not in set(item.value for item in OrderType):
            raise ValueError(f"Order type error in args {exec_cfg}")
        logging.info(f"Execution Param parsing completed: {exec_cfg}")
        #
        # Get redis keys
        #
        ltp_hash_key = BotRedisKeyHelper.get_ltp_hash_key()
        strat_order_hash_key = BotRedisKeyHelper.get_strat_order_hash_key(
            botuuid)
        strat_pos_hash_key = BotRedisKeyHelper.get_strat_pos_hash_key(botuuid)
        order_info_hash_key = BotRedisKeyHelper.get_order_info_hash_key(
            botuuid)
        strat_status_hash_key = BotRedisKeyHelper.get_strat_status_hash(
            botuuid)
        #
        # Init them per strategy, all these have stratid as keys except
        # wdb_strat_order_hash which is order id to strat id mapping
        # for position manager.
        #
        self.wdb = engine.get_wm().get()
        self.wdb_ltp_hash = self.wdb.Hash(ltp_hash_key)
        self.wdb_strat_pos_hash = self.wdb.Hash(strat_pos_hash_key)
        self.wdb_order_info_hash = self.wdb.Hash(order_info_hash_key)
        self.wdb_strat_order_hash = self.wdb.Hash(strat_order_hash_key)
        self.wdb_strat_status_hash = self.wdb.Hash(strat_status_hash_key)
        # Log
        logging.info(
            f"BaseStrategy:{self.strat_id}: LTP Hash:         {ltp_hash_key}")
        logging.info(
            f"BaseStrategy:{self.strat_id}: StratOrder Hash:  {strat_order_hash_key}")
        logging.info(
            f"BaseStrategy:{self.strat_id}: StratPos Hash:    {strat_pos_hash_key}")
        logging.info(
            f"BaseStrategy:{self.strat_id}: OrderInfo Hash:   {order_info_hash_key}")
        logging.info(
            f"BaseStrategy:{self.strat_id}: Strat Status Hash:{strat_status_hash_key}")
        #
        # Internal States
        #
        self.strat_state = StratState.Stopped
        self.sqoff_by_initiator = False
        self.rejection_count = 0
        # Order Id => OrderDetails [OrderParam, OrderInfo]
        self.order_cache: dict[str, OrderDetails] = {}
        # Tradable => Strategy Position Pnl
        self.strat_pos_pnl_cache: dict[str, StratPosPnl] = {}

    def make_order_param(
        self,
        trading_symbol: str,
        direction: str,
        price: float,
        quantity: int
    ) -> OrderParam:
        """
        make order param
        """
        return OrderParam(
            exchange=self.exchange,
            product_type=self.product_type,
            order_type=self.order_type,
            trading_symbol=trading_symbol,
            direction=direction,
            price=price,
            quantity=quantity,
        )

    async def send_new_order(self, op: OrderParam) -> None:
        """
        send new order and update the internal states
        """
        order_id = await self.order_mgr.place_new_order(op)
        #
        # Add order_id to the caches:
        # Internal cache and order hash for external lookups
        #
        self.order_cache[order_id] = OrderDetails(op=op, oi=None)
        self.wdb_strat_order_hash.update({order_id: self.strat_id})

    def remove_order_from_caches(self, order_id):
        del self.order_cache[order_id]
        self.wdb_strat_order_hash.__delitem__(order_id)

    """
    cancel order / orders
    """

    async def cancel_order(self, order_id: str):
        await self.order_mgr.cancel_order(order_id)

    async def cancel_open_buy_orders(self):
        for order_id in self.get_open_order_ids(direction=TransactionType.BUY):
            await self.cancel_order(order_id)

    async def cancel_open_sell_orders(self):
        for order_id in self.get_open_order_ids(direction=TransactionType.SELL):
            await self.cancel_order(order_id)

    async def _cancel_all_open_orders(self):
        for order_id in self.get_open_order_ids():
            await self.cancel_order(order_id)

    def _sync_ord_pos_pnl(self) -> bool:
        """
        sync order info, position and pnl from cental cache
        """
        is_reconciled = True
        #
        # Update order_cache using broker order info
        # Rejected orders and fully cancelled orders will be removed
        # from caches
        #
        sent_order_ids = self.order_cache.keys()
        for sent_oid in sent_order_ids:
            brk_oi_json = self.wdb_order_info_hash.get(sent_oid)
            if not brk_oi_json:
                logging.info(
                    f"{self.strat_id}: sync: waiting for info on order_id:{sent_oid}")
                is_reconciled = False
                continue
            # We got the strategy order id in brokers book
            brk_oi: OrderInfo = OrderInfo.from_json(brk_oi_json)
            if brk_oi.strat_id != self.strat_id:
                logging.error(
                    f"{self.strat_id}: sync: this should not happen, recon logic is broken."
                    f"order_id:{sent_oid} central_cache_stratid:{brk_oi.strat_id} "
                    f"strat_id:{self.strat_id}"
                )
            if brk_oi.order_status == OrderStatus.REJECTED:
                self.rejection_count += 1
                logging.error(
                    f"{self.strat_id}: sync: Order was rejected: order_id:{sent_oid}, reason:{brk_oi.message}")
                self.remove_order_from_caches(sent_oid)
            elif (
                brk_oi.order_status == OrderStatus.CANCELLED
                and brk_oi.filled_quantity <= 0
            ):
                # Cancelled order with filled_quanity = 0, won't contribute
                # to the position, they can be safely removed from tracking
                logging.info(
                    f"{self.strat_id}: sync: Order was cancelled: order_id={sent_oid}")
                self.remove_order_from_caches(sent_oid)
            else:
                self.order_cache[sent_oid].order_info = brk_oi
        #
        # Copy strategy position & pnl details as well
        #
        bval = self.wdb_strat_pos_hash.get(self.strat_id)
        if bval:
            symbol_json_dict = json.loads(bval)
            self.strat_pos_pnl_cache = {
                tradable: StratPosPnl.from_json(strat_pos_json)
                for tradable, strat_pos_json in symbol_json_dict.items()
            }
        return is_reconciled

    async def _sync(self):
        """
        Sync wrapper with retry
        Raises exception after max time crosses while trying to sync
        """
        sync_start_time = time.time()
        while True:
            if self._sync_ord_pos_pnl():
                break
            elapsed_time = int(time.time() - sync_start_time)
            if elapsed_time > MaxOrderPosSyncTimeSec:
                logging.error(
                    f"{self.strat_id}:, sync failed, maxtime of {MaxOrderPosSyncTimeSec} crossed")
                raise ValueError(f"{self.strat_id} _sync failed!")
            await asyncio.sleep(3)

    def get_open_order_ids(self, direction: TransactionType = None) -> list[str]:
        """
        Open orders
        try:
            all_orders = pd.DataFrame(kite.orders()).set_index("order_id")
            pending_orders = all_orders    
            pending_orders = pending_orders[pending_orders['pending_quantity']>0]
            pending_orders = pending_orders[~pending_orders['status'].str.contains("COMPLETE")]
            pending_orders = pending_orders[~pending_orders['status'].str.contains("CANCELLED")]
            pending_orders = pending_orders[~pending_orders['status'].str.contains("REJECTED")]
            run = 0
        except:
            time.sleep(1)
            print("Error in Kite.Orders(), sleeping for 1 second")
        """
        open_order_ids = []
        for _, order_details in self.order_cache.items():
            ordinfo = order_details.order_info
            if not ordinfo:
                logging.error(
                    "This case should not come, sync might have failed!")
                continue
            if not direction or (direction == ordinfo.transaction_type):
                if (
                    ordinfo.order_status != OrderStatus.CANCELLED
                    or ordinfo.order_status != OrderStatus.COMPLETE
                    or ordinfo.order_status != OrderStatus.REJECTED
                ):
                    pending_qty = ordinfo.quantity - ordinfo.filled_quantity
                    if pending_qty > 0:
                        open_order_ids.append(ordinfo.order_id)
        return open_order_ids

    def _get_strategy_net_pnl(self):
        """
        Net pnl for a given strategy. strategy may contain multiple tradables
        we sum up the pnl for all the tradable in the strategy
        """
        pnl = 0
        for _, ppos in self.strat_pos_pnl_cache.items():
            pnl += ppos.netpnl
        return pnl

    def _get_strategy_realized_pnl(self):
        """
        Realized Pnl
        """
        pnl = 0
        for _, ppos in self.strat_pos_pnl_cache.items():
            pnl += ppos.pnl_real
        return pnl

    def _get_strategy_unrealized_pnl(self):
        """
        Unrealized Pnl
        """
        pnl = 0
        for _, ppos in self.strat_pos_pnl_cache.items():
            pnl += ppos.pnl_unreal
        return pnl

    async def _square_off_open_positions(self):
        """ square off open positions """
        for tradable, ppos in self.strat_pos_pnl_cache.items():
            if ppos.netpos == 0:
                continue
            #
            # We have open position
            #
            logging.info(
                f"{self.strat_id}:{tradable}:squareoff position: "
                f"open position = {ppos.netpos}")
            if ppos.netpos < 0:
                # Short position, send buy order
                direction = TransactionType.BUY.value
            else:
                # Long position, need to send sell order
                direction = TransactionType.SELL.value
            await self.send_new_order(
                self.make_order_param(
                    trading_symbol=tradable,
                    direction=direction,
                    price=0,
                    quantity=abs(ppos.netpos),
                )
            )

    def has_open_position(self):
        for ppos in self.strat_pos_pnl_cache.values():
            if ppos.netpos != 0:
                return True
        return False

    async def _square_off_internal(self):
        if self.strat_state == StratState.Active:
            self.strat_state = StratState.SqOffInitiated
            logging.info(f"{self.strat_id}: squareoff initiated")
            await self._cancel_all_open_orders()
            await self._square_off_open_positions()

    def on_stopped(self):
        """ 
        Child strategies can override this and 
        reset their trading states 
        """
        pass

    def _publish_status_info_w_params(self):
        """
        Publish strategy status with params to the cental cache
        """
        ssinfo = {
            BotStatusKeys.status.value: self.strat_state.value,
            BotStatusKeys.underlying.value : self.underlying,
            CtrlKeys.params.value: {
                BotKeys.stop_loss.value: -self.stop_loss,
                BotKeys.profit_target.value: self.profit_target
            }
        }
        self.wdb_strat_status_hash.update({self.strat_id: json.dumps(ssinfo)})


    def _update_pub_strategy_state(self):
        """ 
        Update Strategy state: 
            Change strategy square off state, we are not going to
            automatically change strategy to Active any time, it should be
            user controlled.
        """
        if self.strat_state == StratState.SqOffInitiated:
            has_open_orders = len(self.get_open_order_ids()) > 0
            has_open_pos = self.has_open_position()
            if has_open_orders or has_open_pos:
                logging.info(
                    f"{self.strat_id}: squareoff in process open_orders={has_open_orders}, "
                    f"open_pos={has_open_pos}")
            else:
                self.strat_state = StratState.SqOffCompleted
                logging.info(f"{self.strat_id}: squareoff completed")
        elif self.strat_state == StratState.SqOffCompleted:
            self.strat_state = StratState.Stopped
            logging.info(
                f"{self.strat_id}: strategy state updated to stopped, informing child to cleanup")
            self.on_stopped()
        self._publish_status_info_w_params()

    async def _check_targets(self):
        target_hit = False
        #
        # Profit target check
        #
        netpnl = self._get_strategy_net_pnl()
        if netpnl > self.profit_target:
            logging.info(
                f"TGT-PROFIT {self.strat_id}: hit netpnl={netpnl}, target={self.profit_target}")
            target_hit = True
        return target_hit

    async def _check_rms(self) -> bool:
        """
        Run RMS checks, if checks fail, we need to square off 
        """
        is_rms_passed = True
        # Run checks only in active mode
        if self.strat_state != StratState.Active:
            return is_rms_passed
        #
        # External square off check
        #
        if self.sqoff_by_initiator:
            is_rms_passed = False
        #
        # Time check
        #
        if self.dts.crossed_end_time(datetime.now().timestamp()):
            logging.info(f"RMS: {self.strat_id}: END TIME reached")
            is_rms_passed = False
        #
        # Pnl check (realized and unrealized)
        #
        npnl = self._get_strategy_net_pnl()
        if npnl <= self.stop_loss:
            logging.error(
                f"RMS {self.strat_id}: STOPLOSS: netpnl={npnl}, stoploss={self.stop_loss}")
            is_rms_passed = False

        #
        # rejection check
        #
        if self.rejection_count > MaxRejectionCount:
            logging.error(
                f"RMS {self.strat_id}: REJECT_COUNT threshold of {MaxRejectionCount} breached!")
            is_rms_passed = False
        return is_rms_passed

    """
    External Interaction Methods
    """

    def is_start_time_reached(self):
        return self.dts.reached_start_time(datetime.now().timestamp())

    def is_enabled(self):
        return (self.strat_state == StratState.Active)

    def is_squareoff_initiated(self):
        return self.strat_state == StratState.SqOffInitiated

    def is_squaredoff(self):
        return self.strat_state == StratState.SqOffCompleted

    def start_strategy(self):
        self.sqoff_by_initiator = False
        self.strat_state = StratState.Active
        logging.info(f"{self.strat_id}: setting status to:{self.strat_state}")
        self._update_pub_strategy_state()

    def stop_strategy(self, initiator: str):
        """
        Set squareoff flag
        """
        if self.strat_state != StratState.Active:
            logging.info(
                f"{self.strat_id}: strategy state is {self.strat_state}, "
                f"cannot initiate squareoff")
        else:
            self.sqoff_by_initiator = True
            logging.info(f"{self.strat_id}: squareoff called by:{initiator}")

    def update_params(self, params: dict):
        """
        Update Strategy Params
        """
        if BotKeys.stop_loss in params:
            self.stop_loss = -1 * params[BotKeys.stop_loss]
            logging.info(f"{self.strat_id}:update params:{BotKeys.stop_loss} "
                         f"updated to {self.stop_loss}")
        if BotKeys.profit_target in params:
            self.profit_target = params[BotKeys.profit_target]
            logging.info(f"{self.strat_id}:update params:{BotKeys.profit_target} "
                         f"updated to {self.profit_target}")

    async def process(self) -> bool:
        """
        Return : True -> derived strategy can proceed with actual strategy logic
        """
        #
        # Sync orders and postions
        #
        await self._sync()
        #
        # Update / publish strategy state
        #
        self._update_pub_strategy_state()
        #
        # Run rms checks, includes external square off state
        #
        if not await self._check_rms():
            await self._square_off_internal()
        #
        # Check exit targets
        #
        if await self._check_targets():
            await self._square_off_internal()
        #
        # Return enabled flag to child
        #
        return self.is_enabled()
