
from md.scale_option_chain import ScaleOptionChain
from scale_bot.exec_context import ExecContext
from scale_bot.bot_common import BotKeys, CtrlKeys
from scale_bot.iengine import IEngine

import asyncio
import logging

class ExecContextManager:
    def __init__(self,
                 bot_cfg: dict,
                 engine: IEngine
                 ) -> None:

        self.ul_exec_ctx_map: dict[str, list[ExecContext]] = {}
        self.strat_exec_map : dict[str, ExecContext] = {}

        self.botuuid = bot_cfg[BotKeys.botuuid.value]
        strat_config_list = bot_cfg[BotKeys.slist.value]
        for idx, strat_cfg in enumerate(strat_config_list):
            # Inject strategy_id int to strat_cfg
            scfg = strat_cfg
            strat_id = f"{scfg[BotKeys.execution][BotKeys.strategy_name]}_{idx + 1}"
            scfg[BotKeys.execution.value][BotKeys.strategy_id.value] = strat_id
            # ExecContext (Strategy Execution Wrapper)
            exec_cxt = ExecContext(
                botuuid=self.botuuid,
                strat_cfg=scfg,
                engine=engine)
            # 
            # Build underlying to [exec context list] map
            #
            underlying = exec_cxt.get_underlying()
            if underlying not in self.ul_exec_ctx_map:
                self.ul_exec_ctx_map[underlying] = []
            self.ul_exec_ctx_map[underlying].append(exec_cxt)
            #
            # And strategy id to execc context map 
            #
            self.strat_exec_map[strat_id] = exec_cxt

    def get_underlyings(self) -> list[str]:
        """ For option chain subscription """
        return list(self.ul_exec_ctx_map.keys())

    async def process_update(self, up: ScaleOptionChain) -> bool:
        """
        Process Market Data
        """
        exec_cxts = self.ul_exec_ctx_map[up.get_opt_symbol()]
        tasks = []
        async with asyncio.TaskGroup() as task_group:
            for cxt in exec_cxts:
                tasks.append(task_group.create_task(cxt.process(up)))
        return all(await asyncio.gather(*tasks))
    
    async def process_ctrl_message(self, ctrl_msg: dict):
        """
        Process Control Message [keys should be in CtrlKeys]
        {"strat_id" : "all", "msg" : {"action" , "start"}}
        {"strat_id" : "xxx", "msg" : {"action" , "start"}}
        {"strat_id" : "xxx", "msg" : {"action" , "stop"}}
        {"strat_id" : "xxx", "msg" : {"action" , "update", "params" : {'stop_loss': 100}}}
        """
        try:
            strat_id = ctrl_msg[CtrlKeys.strat_id]
            ctrld = ctrl_msg[CtrlKeys.msg]
            if strat_id == 'all':
                for cxt in self.strat_exec_map.values():
                    await cxt.process_ctrl_message(ctrld)
            elif strat_id in self.strat_exec_map:
                await self.strat_exec_map[strat_id].process_ctrl_message(ctrld)
            else:
                raise ValueError(f"CtrlMsg: Invalid strategy id:{strat_id}")    
        except Exception as ex:
            logging.error(f"CtrlMsg: {ex}")    

