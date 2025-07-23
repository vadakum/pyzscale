

from common.dt_helper import DTHelper
from md.instrument_manager import InstrumentManager, InstrumentType
from md.scale_option_chain import ScaleOptionChain
from modelservice.scale_alpha import ScaleAlpha
from backtest.scale_backtest_args import ScaleBacktestArgs, SBKeys
from backtest.scale_backtest_common import *
from modelservice.alpha_consts import SignalDirection
from backtest.oc_data_reader import OCDataReader

from datetime import datetime, timedelta
from dataclasses import asdict
import logging


class ScaleBacktest:
    def __init__(self, argwrap: ScaleBacktestArgs) -> None:
        self.argwrap = argwrap
        self.strat_common_args = {}
        self.strat_alpha_args = {}
        self.strat_exec_args = {}
        self.last_signal_dir = None

        ''' create the data reader '''
        self.strat_common_args = argwrap.bt_args[SBKeys.common.value]
        start_time = str(self.strat_common_args[SBKeys.start_time])
        end_time = str(self.strat_common_args[SBKeys.end_time])
        self.data_reader = OCDataReader(
            argwrap.dump_file, start_time, end_time)

        ''' set strategy and alpha args '''
        self.set_strategy_args(argwrap.bt_args)
        self.inst_mgr = InstrumentManager(
            argwrap.instrument_file, trading_date=argwrap.trading_date)
        self.scale_alpha = ScaleAlpha(self.strat_alpha_args)
        self.bt_run_state_init()
        # filled only signal only processing
        self.all_signals: list[ScaleSignal] = []
        logging.info(f"Backtest init with args : {asdict(argwrap)}")

    def bt_run_state_init(self):
        self.day_result = DayResult(self.argwrap.opt_symbol,
                                    self.argwrap.trading_date,
                                    self.inst_mgr.get_opt_lot_size(
                                        self.argwrap.opt_symbol),
                                    self.quote_lots
                                    )
        self.active_entry = EntryType.Clear
        self.entry_pt = None

    def set_strategy_args(self, strat_args):
        try:
            self.strat_alpha_args = strat_args[SBKeys.alpha.value]
            self.strat_exec_args = strat_args[SBKeys.execution.value]
            self.exec_instr_type = str(
                self.strat_exec_args[SBKeys.exec_instr_type.value]).upper()
            self.exec_price_type = str(
                self.strat_exec_args[SBKeys.price_type.value]).upper()
            if self.exec_price_type not in set(item.value for item in PriceType):
                raise ValueError(f"Price type error {self.exec_price_type}")
            self.opt_trd_mness_offset = self.strat_exec_args[SBKeys.opt_trd_offset]
            self.quote_lots = self.strat_exec_args[SBKeys.quote_lots]
            self.profit_target = self.strat_exec_args[SBKeys.profit_target]

        except Exception as ex:
            logging.error(f"invalid strat args {strat_args}")
            raise ex

    """
    calc_cost
    """

    def calc_cost(self, md_up: ScaleOptionChain, value):
        cost = PerOrderCost
        if md_up.get_trd_instr_type() == InstrumentType.EQ:
            cost += (TCost['E'] * value)
        elif self.exec_instr_type in TCost:
            cost += (TCost[self.exec_instr_type] * value)
        return round(cost, 2)

    """
    price type fetch
    """

    def get_tradable_fill_price(self, side: str, md_up: ScaleOptionChain):
        if self.exec_price_type == PriceType.LTP:
            return md_up.get_trd_ltp()

        elif self.exec_price_type == PriceType.MID:
            return md_up.get_trd_midpx()

        elif self.exec_price_type == PriceType.CROSS:
            if side == Side.Buy:
                return md_up.get_trd_top_sell_px()
            elif side == Side.Sell:
                return md_up.get_trd_top_buy_px()

        elif self.exec_price_type == PriceType.BEST:
            if side == Side.Buy:
                return md_up.get_trd_top_buy_px()
            elif side == Side.Sell:
                return md_up.get_trd_top_sell_px()
        raise ValueError("Invalid fill price")

    def get_opt_fill_price(self, side: str, md_up: ScaleOptionChain, strike) -> CallPutPxNt:
        if self.exec_price_type == PriceType.LTP:
            return CallPutPxNt(
                call_px=md_up.get_opt_ltp(strike, InstrumentType.CE),
                put_px=md_up.get_opt_ltp(strike, InstrumentType.PE))

        elif self.exec_price_type == PriceType.MID:
            return CallPutPxNt(
                call_px=md_up.get_opt_midpx(strike, InstrumentType.CE),
                put_px=md_up.get_opt_midpx(strike, InstrumentType.PE))

        elif self.exec_price_type == PriceType.CROSS:
            if side == Side.Buy:
                return CallPutPxNt(
                    call_px=md_up.get_opt_top_sell_px(
                        strike, InstrumentType.CE),
                    put_px=md_up.get_opt_top_sell_px(strike, InstrumentType.PE))
            elif side == Side.Sell:
                return CallPutPxNt(
                    call_px=md_up.get_opt_top_buy_px(
                        strike, InstrumentType.CE),
                    put_px=md_up.get_opt_top_buy_px(strike, InstrumentType.PE))

        elif self.exec_price_type == PriceType.BEST:
            if side == Side.Buy:
                return CallPutPxNt(
                    call_px=md_up.get_opt_top_buy_px(
                        strike, InstrumentType.CE),
                    put_px=md_up.get_opt_top_buy_px(strike, InstrumentType.PE))

            elif side == Side.Sell:
                return CallPutPxNt(
                    call_px=md_up.get_opt_top_sell_px(
                        strike, InstrumentType.CE),
                    put_px=md_up.get_opt_top_sell_px(strike, InstrumentType.PE))

        raise ValueError("Invalid fill price")

    """
    entry_buy
    """

    def entry_buy(self, md_up: ScaleOptionChain, signal: ScaleSignal, day_result: DayResult) -> EntryNt:
        #
        # Fut -> Buy, Call -> Buy
        #
        up_time = md_up.get_ul_exch_ts()
        lot_size = md_up.get_trd_lot_size()
        exec_itype = self.exec_instr_type
        tran = Tran.Open.value
        fut_entry_px = 0
        entry_strike = 0
        call_entry_px = 0
        put_entry_px = 0
        if exec_itype == ExecInstType.NK_F:
            side = Side.Buy.value
            fut_entry_px = self.get_tradable_fill_price(side, md_up)
            to = (fut_entry_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            day_result.push_trades(
                TradeNt(inst=exec_itype, side=side, tran=tran, time=up_time,
                        price=fut_entry_px, profit=0, cost=cost, to=to, hold=None,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))
        else:
            # Buy Call at atm/itm based on offset
            opt_ty = InstrumentType.CE.value
            side = Side.Buy.value
            entry_strike = signal.atm - self.opt_trd_mness_offset * md_up.get_opt_strike_gap()
            opt_px = self.get_opt_fill_price(side, md_up, entry_strike)
            call_entry_px = opt_px.call_px
            to = (call_entry_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            day_result.push_trades(TradeNt(inst=f"{exec_itype}:{opt_ty}:{entry_strike}", side=side, tran=tran,
                                           time=up_time, price=call_entry_px, profit=0, cost=cost, to=to, hold=None,
                                           sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                                           ))

        return (EntryNt(fut_entry_px, entry_strike, call_entry_px, put_entry_px, up_time))
    """
    exit_buy
    """

    def exit_buy(self, md_up: ScaleOptionChain, signal: ScaleSignal, entry_pt: EntryNt, day_result: DayResult):
        #
        # Exit Buy:
        # Fut -> Sell, Call -> Sell
        #
        up_time = md_up.get_ul_exch_ts()
        lot_size = md_up.get_trd_lot_size()
        exec_itype = self.exec_instr_type
        hold = DTHelper.to_datetime_from_yyyy_mm_dd_hh_mm_ss(
            up_time) - DTHelper.to_datetime_from_yyyy_mm_dd_hh_mm_ss(entry_pt.entry_time)
        tran = Tran.Close.value
        if exec_itype == ExecInstType.NK_F:
            side = Side.Sell.value
            fut_exit_px = self.get_tradable_fill_price(side, md_up)
            to = (fut_exit_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            profit = round((fut_exit_px - entry_pt.fut_entry_px)
                           * lot_size * self.quote_lots, 2)
            day_result.push_trades(
                TradeNt(inst=exec_itype, side=side, tran=tran, time=up_time,
                        price=fut_exit_px, profit=profit, cost=cost, to=to, hold=hold,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))
        else:
            side = Side.Sell.value
            opt_ty = InstrumentType.CE.value
            opt_px = self.get_opt_fill_price(
                side, md_up, entry_pt.entry_strike)
            call_exit_px = opt_px.call_px
            to = (call_exit_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            profit = round(
                (call_exit_px - entry_pt.call_entry_px) * lot_size * self.quote_lots, 2)
            day_result.push_trades(
                TradeNt(inst=f"{exec_itype}:{opt_ty}:{entry_pt.entry_strike}", side=side, tran=tran,
                        time=up_time, price=call_exit_px, profit=profit, cost=cost, to=to, hold=hold,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))

    """
    entry_sell
    """

    def entry_sell(self, md_up: ScaleOptionChain, signal: ScaleSignal, day_result: DayResult) -> EntryNt:
        #
        # Fut -> Sell, Put -> Buy
        #
        up_time = md_up.get_ul_exch_ts()
        lot_size = md_up.get_trd_lot_size()
        exec_itype = self.exec_instr_type
        tran = Tran.Open.value
        fut_entry_px = 0
        entry_strike = 0
        call_entry_px = 0
        put_entry_px = 0
        if exec_itype == ExecInstType.NK_F:
            side = Side.Sell.value
            fut_entry_px = self.get_tradable_fill_price(side, md_up)
            to = (fut_entry_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            day_result.push_trades(
                TradeNt(inst=exec_itype, side=side, tran=tran, time=up_time,
                        price=fut_entry_px, profit=0, cost=cost, to=to, hold=None,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))
        else:
            opt_ty = InstrumentType.PE.value
            side = Side.Buy.value
            entry_strike = signal.atm + self.opt_trd_mness_offset * md_up.get_opt_strike_gap()
            opt_px = self.get_opt_fill_price(side, md_up, entry_strike)
            put_entry_px = opt_px.put_px
            to = (put_entry_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            day_result.push_trades(
                TradeNt(inst=f"{exec_itype}:{opt_ty}:{entry_strike}", side=side, tran=tran,
                        time=up_time, price=put_entry_px, profit=0, cost=cost, to=to, hold=None,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))

        return (EntryNt(fut_entry_px, entry_strike, call_entry_px, put_entry_px, up_time))

    """
    exit_sell
    """

    def exit_sell(self, md_up: ScaleOptionChain, signal: ScaleSignal, entry_pt: EntryNt, day_result: DayResult):
        #
        # Fut -> Buy, Put -> Sell
        #
        up_time = md_up.get_ul_exch_ts()
        lot_size = md_up.get_trd_lot_size()
        exec_itype = self.exec_instr_type
        hold = DTHelper.to_datetime_from_yyyy_mm_dd_hh_mm_ss(
            up_time) - DTHelper.to_datetime_from_yyyy_mm_dd_hh_mm_ss(entry_pt.entry_time)
        tran = Tran.Close.value
        if exec_itype == ExecInstType.NK_F:
            side = Side.Buy.value
            fut_exit_px = self.get_tradable_fill_price(side, md_up)
            to = (fut_exit_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            profit = round((entry_pt.fut_entry_px - fut_exit_px)
                           * lot_size * self.quote_lots, 2)
            day_result.push_trades(
                TradeNt(inst=exec_itype, side=side, tran=tran, time=up_time,
                        price=fut_exit_px, profit=profit, cost=cost, to=to, hold=hold,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))
        else:
            side = Side.Sell.value
            opt_ty = InstrumentType.PE.value
            opt_px = self.get_opt_fill_price(
                side, md_up, entry_pt.entry_strike)
            put_exit_px = opt_px.put_px
            to = (put_exit_px * lot_size * self.quote_lots)
            cost = self.calc_cost(md_up, to)
            profit = round((put_exit_px - entry_pt.put_entry_px)
                           * lot_size * self.quote_lots, 2)
            day_result.push_trades(
                TradeNt(inst=f"{exec_itype}:{opt_ty}:{entry_pt.entry_strike}", side=side, tran=tran,
                        time=up_time, price=put_exit_px, profit=profit, cost=cost, to=to, hold=hold,
                        sigval=signal.val, cpx=signal.cpx, ppx=signal.ppx, ulpx=signal.ulpx, atm=signal.atm
                        ))

    def _calc_exit_buy_pnl(self, md_up: ScaleOptionChain, entry_pt: EntryNt):
        lot_size = md_up.get_trd_lot_size()
        fut_exit_px = self.get_tradable_fill_price(Side.Sell.value, md_up)
        to = (fut_exit_px * lot_size * self.quote_lots)
        cost = self.calc_cost(md_up, to)
        profit = round((fut_exit_px - entry_pt.fut_entry_px)
                       * lot_size * self.quote_lots, 2)
        return (profit - cost)

    def _calc_exit_sell_pnl(self, md_up: ScaleOptionChain, entry_pt: EntryNt):
        lot_size = md_up.get_trd_lot_size()
        fut_exit_px = self.get_tradable_fill_price(Side.Buy.value, md_up)
        to = (fut_exit_px * lot_size * self.quote_lots)
        cost = self.calc_cost(md_up, to)
        profit = round((entry_pt.fut_entry_px - fut_exit_px)
                       * lot_size * self.quote_lots, 2)
        return (profit - cost)

    """
    process backtest methods
    """

    def _make_trade(self, md_up: ScaleOptionChain, signal: ScaleSignal):
        if signal.dir == SignalDirection.NONE:
            if self.profit_target > 0:
                if self.active_entry == EntryType.Buy:
                    exit_pnl = self._calc_exit_buy_pnl(md_up, self.entry_pt)
                    if exit_pnl > self.profit_target * 1.5 or exit_pnl < -self.profit_target:
                        self.exit_buy(md_up,
                                      signal=signal,
                                      entry_pt=self.entry_pt,
                                      day_result=self.day_result)
                        self.active_entry = EntryType.Clear
                elif self.active_entry == EntryType.Sell:
                    exit_pnl = self._calc_exit_sell_pnl(md_up, self.entry_pt)
                    if exit_pnl > self.profit_target * 1.5 or exit_pnl < -self.profit_target:
                        self.exit_sell(md_up,
                                       signal=signal,
                                       entry_pt=self.entry_pt,
                                       day_result=self.day_result)
                        self.active_entry = EntryType.Clear
        #
        # Buy entry or (sell exit + buy entry) processing
        #
        elif signal.dir == SignalDirection.BUY:
            if self.active_entry == EntryType.Sell:
                self.exit_sell(md_up,
                               signal=signal,
                               entry_pt=self.entry_pt,
                               day_result=self.day_result)
                self.active_entry = EntryType.Clear
            # Buy entry
            if self.active_entry != EntryType.Buy:
                self.active_entry = EntryType.Buy
                self.entry_pt = self.entry_buy(md_up, signal, self.day_result)

        #
        # Sell entry or (buy exit + sell entry) processing
        #
        elif signal.dir == SignalDirection.SELL:
            if self.active_entry == EntryType.Buy:
                self.exit_buy(md_up,
                              signal=signal,
                              entry_pt=self.entry_pt,
                              day_result=self.day_result)
                self.active_entry = EntryType.Clear
            # Sell entry
            if self.active_entry != EntryType.Sell:
                self.active_entry = EntryType.Sell
                self.entry_pt = self.entry_sell(md_up, signal, self.day_result)

    def _make_m2m(self, md_up: ScaleOptionChain, signal: ScaleSignal):
        # we are done with the loop, check if there are open positions
        if self.active_entry != EntryType.Clear:
            logging.info("Closing last position!")
            # last position was not closed
            if self.active_entry == EntryType.Sell:
                self.active_entry = EntryType.Clear
                self.exit_sell(md_up,
                               signal=signal,
                               entry_pt=self.entry_pt,
                               day_result=self.day_result)
            elif self.active_entry == EntryType.Buy:
                self.active_entry = EntryType.Clear
                self.exit_buy(md_up,
                              signal=signal,
                              entry_pt=self.entry_pt,
                              day_result=self.day_result)

    def _process_bt_update(self, msg):
        md_up = ScaleOptionChain(msg=msg, inst_mgr=self.inst_mgr)
        signal = self.scale_alpha.process_update(up=md_up)
        if not signal.is_valid:
            return
        logging.debug(f"-> signal {asdict(signal)}")
        self._make_trade(md_up=md_up, signal=signal)

    def _process_m2m(self, msg):
        md_up = ScaleOptionChain(msg=msg, inst_mgr=self.inst_mgr)
        signal = self.scale_alpha.process_update(up=md_up)
        self._make_m2m(md_up=md_up, signal=signal)

    """
    run backtest
    """

    def run_bt(self, show_trades=True):
        self.bt_run_state_init()
        self.data_reader.process(self._process_bt_update, self._process_m2m)
        return self.day_result.gen_result(show_trades)

    """
    process only signal
    """

    def _process_signal_update(self, msg):
        md_up = ScaleOptionChain(msg=msg, inst_mgr=self.inst_mgr)
        signal = self.scale_alpha.process_update(up=md_up)
        self.all_signals.append(signal)

    """
    run signals
    """

    def run_signal(self):
        self.data_reader.process(self._process_signal_update)
        return [asdict(signal) for signal in self.all_signals if signal.is_valid]

    """
    exteral print helper
    """

    def print_result(self, result):
        DayResult.print_result(result)

    """
    qoptr backtests
    """
    '''
    search returns None if not found
    '''

    def search_qoptr_signal(self, md_dt: datetime) -> int:
        last_signal_idx = -1
        for idx, external_sig_dt in enumerate(self.ext_signal_ts):
            if external_sig_dt <= md_dt:
                last_signal_idx = idx
                continue
            else:
                break
        if last_signal_idx != -1:
            return self.ext_signals[last_signal_idx]
        return None

    def _process_bt_update_on_qoptr_signal(self, msg):
        md_up = ScaleOptionChain(msg=msg, inst_mgr=self.inst_mgr)
        md_dt = datetime.fromisoformat(md_up.get_ul_exch_ts())
        qoptr_signal = self.search_qoptr_signal(md_dt)
        if qoptr_signal:
            logging.debug(f"-> signal {asdict(qoptr_signal)}, md_dt={md_dt}")
            self._make_trade(md_up=md_up, signal=qoptr_signal)

    def _process_m2m_on_qoptr_signal(self, msg):
        md_up = ScaleOptionChain(msg=msg, inst_mgr=self.inst_mgr)
        md_dt = datetime.fromisoformat(md_up.get_ul_exch_ts())
        signal = self.search_qoptr_signal(md_dt)
        if signal:
            logging.debug(f"-> signal {asdict(signal)}")
            self._make_m2m(md_up=md_up, signal=signal)

    def qoptr_to_scale_signal_convertor(self, qoptr_signals) -> list[ScaleSignal]:
        signals = []
        for qsignal in qoptr_signals:
            signals.append(ScaleSignal(is_valid=True, ulexts=qsignal['ulexts'], dir=qsignal['dir'],
                                       val=qsignal['val'], ulpx=qsignal['ulpx'], smooth_ulpx=qsignal['ulpx'],
                                       atm=qsignal['atm'], cpx=qsignal['cpx'], ppx=qsignal['ppx']))
        return signals

    def run_bt_with_qoptr_signal(self, qoptr_signals: list[dict], shift=0):
        self.bt_run_state_init()
        self.ext_signals = self.qoptr_to_scale_signal_convertor(qoptr_signals)
        self.ext_signal_ts = [datetime.fromisoformat(
            signal.ulexts) - timedelta(minutes=shift) for signal in self.ext_signals]
        self.data_reader.process(
            self._process_bt_update_on_qoptr_signal, self._process_m2m_on_qoptr_signal)
        return self.day_result.gen_result()

    @staticmethod
    def signal_merge_qoptr_to_scale(ss, qs):
        pass
