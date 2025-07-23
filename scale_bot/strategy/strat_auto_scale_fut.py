

from md.instrument_manager import InstField
from md.scale_option_chain import ScaleOptionChain
from modelservice.alpha_consts import SignalDirection
from modelservice.scale_alpha import ScaleSignal

from scale_bot.bot_common import *
from scale_bot.strategy.strat_base import BaseStrategy
from scale_bot.order_manager.order_manager import OrderManager
from scale_bot.iengine import IEngine

from typing import Final, Union
import logging
import time
import asyncio

LogStatusMessageIntervalSec: Final = 60

class StratAutoScaleFut(BaseStrategy):
    """
    StratAutoScaleFut
    """
    def __init__(
        self,
        botuuid,
        underlying,
        strat_cfg,
        order_mgr: OrderManager,
        engine: IEngine
    ):
        super().__init__(
            botuuid=botuuid,
            underlying=underlying,
            strat_cfg=strat_cfg,
            order_mgr=order_mgr,
            engine=engine)

        self.canonical = f"{underlying}_F_0"
        self.instr_def = engine.get_instrument_mgr().get_instrument_def(self.canonical)
        self.trd_symbol = self.instr_def[InstField.TradingSymbol]
        self.lot_size = self.instr_def[InstField.LotSize]
        self.quote_qty = self.quote_lots * self.lot_size
        # Internal states
        self.active_entry = EntryType.Clear
        self.exec_queue = asyncio.Queue()
        self.last_log_status_time = time.time()
        logging.info(
            f"Created Strategy: {self.strat_id} with tradable:{self.canonical}:{self.trd_symbol}, "
            f"lot_size:{self.lot_size}, quote_qty:{self.quote_qty}, "
            f"stop_loss:{self.stop_loss}, profit_target:{self.profit_target}")


    """
    Methods
    """
    def _reset_trading_state(self):
        """ To be called once base strategy signals stopped """
        self.active_entry = EntryType.Clear
        # Clean up the exec queue, we don't want to trigger any orders
        while not self.exec_queue.empty():
            self.exec_queue.get_nowait()

    def _get_tradable_fill_price(self, side: str, md_up: ScaleOptionChain):
        """ For now send market order """
        return 0

    def _get_strat_pos_pnl_for_symbol(
            self, 
            trd_symbol: str) -> Union[StratPosPnl | None]:
        """ filtered result for self.strat_pos_pnl_cache """
        if trd_symbol not in self.strat_pos_pnl_cache:
            return None
        return self.strat_pos_pnl_cache[trd_symbol]

    async def _entry_buy(self, up: ScaleOptionChain):
        """
        Fut -> Buy
        """
        fname = "entry_buy"
        up_time = up.get_ul_exch_ts()
        trd_symbol = up.get_trd_symbol()
        direction = TransactionType.BUY.value
        time_lag = up.get_curr_md_time_lag()

        await self.cancel_open_sell_orders()

        pos_pnl = self._get_strat_pos_pnl_for_symbol(trd_symbol)
        if pos_pnl:
            logging.info(
                f"{self.strat_id}: {fname} : cached pos pnl => {pos_pnl.to_json()}")
            if pos_pnl.netpos > 0:
                logging.warning(
                    f"{self.strat_id}: {fname} : invalid position!")
                return
            
        if self.get_open_order_ids(TransactionType.BUY):
            logging.warning(
                f"{self.strat_id}: {fname} : open orders already present!")
            return
            
        logging.info(
            f"{self.strat_id}:{fname}:exchts:{up_time}, tslag:{time_lag}, "
            f"trd:{trd_symbol}, ltp:{up.get_trd_ltp()}, ulpx:{up.get_ul_price()}")

        await self.send_new_order(
            self.make_order_param(
                trading_symbol=trd_symbol,
                direction=direction,
                price=0,
                quantity=abs(self.quote_qty)
            )
        )

    async def _entry_sell(self, up: ScaleOptionChain):
        """
        Fut -> Sell
        """
        fname = "entry_sell"
        up_time = up.get_ul_exch_ts()
        trd_symbol = up.get_trd_symbol()
        direction = TransactionType.SELL.value
        time_lag = up.get_curr_md_time_lag()

        await self.cancel_open_buy_orders()

        pos_pnl = self._get_strat_pos_pnl_for_symbol(trd_symbol)
        if pos_pnl:
            logging.info(
                f"{self.strat_id}:{fname}:cached pos pnl => {pos_pnl.to_json()}")
            if pos_pnl.netpos < 0:
                logging.error(f"{self.strat_id}:{fname}:invalid position!")
                return

        if self.get_open_order_ids(TransactionType.SELL):
            logging.warning(
                f"{self.strat_id}: {fname} : open orders already present!")
            return

        logging.info(
            f"{self.strat_id}:{fname}:exchts:{up_time}, tslag:{time_lag}, "
            f"trd:{trd_symbol}, ltp:{up.get_trd_ltp()}, ulpx:{up.get_ul_price()}")

        await self.send_new_order(
            self.make_order_param(
                trading_symbol=trd_symbol,
                direction=direction,
                price=0,
                quantity=abs(self.quote_qty)
            )
        )

    async def _exit_buy(self, up: ScaleOptionChain):
        """
        Fut -> Sell
        """
        fname = "exit_buy"
        up_time = up.get_ul_exch_ts()
        trd_symbol = up.get_trd_symbol()
        direction = TransactionType.SELL.value
        time_lag = up.get_curr_md_time_lag()

        await self.cancel_open_buy_orders()

        pos_pnl = self._get_strat_pos_pnl_for_symbol(trd_symbol)
        if not pos_pnl:
            logging.error(
                f"{self.strat_id}:{fname}:{trd_symbol} pos not found!")
            return

        logging.info(
            f"{self.strat_id}:{fname}:cached pos pnl => {pos_pnl.to_json()}")

        exit_pos = pos_pnl.netpos
        if exit_pos <= 0:
            logging.error(f"{self.strat_id}:{fname}:invalid position!")
            return

        logging.info(
            f"{self.strat_id}:{fname}:exchts:{up_time}, tslag:{time_lag}, "
            f"trd:{trd_symbol}, ltp:{up.get_trd_ltp()}, ulpx:{up.get_ul_price()}")

        await self.send_new_order(
            self.make_order_param(
                trading_symbol=trd_symbol,
                direction=direction,
                price=0,
                quantity=abs(exit_pos)
            )
        )

    async def _exit_sell(self, up: ScaleOptionChain):
        """
        Fut -> Buy
        """
        fname = "exit_sell"
        up_time = up.get_ul_exch_ts()
        trd_symbol = up.get_trd_symbol()
        direction = TransactionType.BUY.value
        time_lag = up.get_curr_md_time_lag()

        await self.cancel_open_sell_orders()

        pos_pnl = self._get_strat_pos_pnl_for_symbol(trd_symbol)
        if not pos_pnl:
            logging.error(
                f"{self.strat_id}:{fname}:{trd_symbol} pos not found!")
            return

        logging.info(
            f"{self.strat_id}:{fname}:cached pos pnl => {pos_pnl.to_json()}")

        exit_pos = pos_pnl.netpos
        if exit_pos >= 0:
            logging.error(f"{self.strat_id}:{fname}:invalid position!")
            return

        logging.info(
            f"{self.strat_id}:{fname}:exchts:{up_time}, tslag:{time_lag}, "
            f"trd:{trd_symbol}, ltp:{up.get_trd_ltp()}, ulpx:{up.get_ul_price()}")

        await self.send_new_order(
            self.make_order_param(
                trading_symbol=trd_symbol,
                direction=direction,
                price=0,
                quantity=abs(exit_pos)
            )
        )

    async def _enqueue_signal_fns(self,
                                 md_up: ScaleOptionChain,
                                 signal: ScaleSignal):
        """
        collect the signals for execution
        """
        if not signal.is_valid:
            return
        #
        # Buy entry or (sell exit + buy entry) processing
        #
        if signal.dir == SignalDirection.BUY:
            if self.active_entry == EntryType.Sell:
                await self.exec_queue.put(lambda: self._exit_sell(md_up))
                self.active_entry = EntryType.Clear
            # Buy entry
            if self.active_entry != EntryType.Buy:
                self.active_entry = EntryType.Buy
                await self.exec_queue.put(lambda: self._entry_buy(md_up))
        #
        # Sell entry or (buy exit + sell entry) processing
        #
        elif signal.dir == SignalDirection.SELL:
            if self.active_entry == EntryType.Buy:
                await self.exec_queue.put(lambda: self._exit_buy(md_up))
                self.active_entry = EntryType.Clear
            # Sell entry
            if self.active_entry != EntryType.Sell:
                self.active_entry = EntryType.Sell
                await self.exec_queue.put(lambda: self._entry_sell(md_up))

    async def _execute_signal_fn(self):
        if self.exec_queue.empty():
            return
        en_ex_fn = await self.exec_queue.get()
        await en_ex_fn()
        qlen = self.exec_queue.qsize()
        if qlen > 0:
            logging.info(f"{self.strat_id}: Queued signal functions:{qlen}")

    def _validate_md(self, up: ScaleOptionChain) -> bool:
        """ Make sure we are processing the right symbol (as configured) """
        if self.trd_symbol != up.get_trd_symbol():
            logging.error(
                f"{self.strat_id}: Trading symbol mismatch strat:{self.trd_symbol} md:{up.get_trd_symbol()}")
            return False
        # 
        # Just making sure that our configured lot size and that published in market data is same
        #
        if self.lot_size != up.get_trd_lot_size():
            logging.error(
                f"{self.strat_id}: Lot size mismatch strat:{self.lot_size} md:{up.get_trd_lot_size()}")
            return False
        return True

    def _log_status(self, up: ScaleOptionChain):
        """ Log status message intermittently  """
        if time.time() - self.last_log_status_time > LogStatusMessageIntervalSec:
            logging.info(
                f"{self.strat_id}:[{self.strat_state.value.upper()}], "
                f"trd:{up.get_trd_symbol()}, "
                f"exchts:{up.get_ul_exch_ts()}, "
                f"tslag:{up.get_curr_md_time_lag()}, "
                f"ulpx:{up.get_ul_price()}, ltp:{up.get_trd_ltp()} ")
            self.last_log_status_time = time.time()

    def on_stopped(self):
        """ 
        Called by the parent once square off is complete or 
        state changed to stopped. For now #super().on_stopped()
        is not required
        """
        self._reset_trading_state()
        logging.info(f"{self.strat_id} {self.trd_symbol} states reset as "
                     f"requested by base strategy")
    
    async def process(self,
                      up: ScaleOptionChain,
                      signal: ScaleSignal) -> bool:
        """
        Entry point method
        - Validate md
        - Call base process() for position sync and rms checks
        - Enqueue signals (we cannot execute multiple signals in one go due to margin)
        - Execute single signal from enqueued signals
        """
        if not self._validate_md(up):
            return False
        
        self._log_status(up)

        try:
            if await super().process():
                await self._enqueue_signal_fns(up, signal)
                await self._execute_signal_fn()
        except Exception as ex:
            logging.error(f"Caught exception: {ex}")
            return False
        return True
