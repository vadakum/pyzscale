

from common.dt_helper import DTStartEndTimeManager
from md.scale_option_chain import ScaleOptionChain
from modelservice.scale_alpha import ScaleAlpha, ScaleSignal

from scale_bot.bot_common import *
from scale_bot.order_manager.order_common import *
from scale_bot.strategy.strat_factory import StratFactory
from scale_bot.strategy.strat_base import BaseStrategy
from scale_bot.order_manager.order_manager import OrderManager
from scale_bot.iengine import IEngine

from datetime import datetime
import logging

class ExecContext:
    """
    ExecContext
    """
    def __init__(self,
                 botuuid: str,
                 strat_cfg: dict,
                 engine: IEngine
                 ) -> None:

        common_args = strat_cfg[BotKeys.common]
        self.underlying = common_args[BotKeys.underlying]
        #
        # Set strategy and alpha args 
        #
        logging.info(f"Creating ExecContext with args : {strat_cfg}")        
        self.scale_alpha = ScaleAlpha(strat_cfg[BotKeys.alpha])
        strategy_name = strat_cfg[BotKeys.execution][BotKeys.strategy_name]
        self.strategy: BaseStrategy = StratFactory.create(
            strategy_name,
            botuuid=botuuid,
            underlying=self.underlying,
            strat_cfg=strat_cfg,
            order_mgr=OrderManager(engine.get_kconn()),
            engine=engine)
        #
        # States
        #
        self._last_signal: ScaleSignal = None
        self._is_active = False

    def get_underlying(self):
        """
        underlying from config
        """
        return self.underlying

    def set_active(self):
        """
        We ask strategy to start the signal processing
        - just check if its time to start the signal processing, we are not
          querying the actual strategy status
        """
        if not self._is_active:
            if self.strategy.is_start_time_reached():
                self._is_active = True
        return self._is_active

    def process_signal_update(self, up):
        """
        Get the signal from scale alpha
        """
        signal = self.scale_alpha.process_update(up)
        # log signal when it turns valid from invalid
        if signal.is_valid:
            if not self._last_signal or not self._last_signal.is_valid:
                logging.info(
                    f"SIGNAL:{self.underlying}:{str(signal)}")
        self._last_signal = signal
        return signal

    async def process(self, up: ScaleOptionChain) -> bool:
        """
        - Always Process signal, irrespective of the start/end time
          as we are not checking the signal bootup delay
        - Pass on signal to strategy based on active time
        - Signal validity will be checked in the strategy
        """
        signal = self.process_signal_update(up)
        if not self.set_active():
            return True
        return await self.strategy.process(up=up, signal=signal)

    async def process_ctrl_message(self, ctrld: dict):
        """
        Process strategy control message
        actions:
            start, stop
        """
        action = ctrld[CtrlKeys.action]
        if action == CtrlKeys.start:
            self.strategy.start_strategy()
        elif action == CtrlKeys.stop:
            self.strategy.stop_strategy("commander")
        elif action == CtrlKeys.update:
            if CtrlKeys.params in ctrld:
                self.strategy.update_params(ctrld[CtrlKeys.params])  
            else:
                logging.warning(f"CtrlMsg: update action is missing params")
        else:
            logging.warning(f"CtrlMsg: unhandled action {action}")
