
from common.bcolors import BColors
from datetime import datetime
from scale_bot.bot_common import CtrlKeys, BotStatusKeys

import logging
import json
import asyncio

"""
BotUtils
"""
class BotUtils:
    """
    get_epoch
    """
    @staticmethod
    def get_epoch(dt: datetime = None):
        if dt == None:
            dt = datetime.now()
        return int(datetime.timestamp(dt))

    """
    get_market_start_time
    """
    @staticmethod
    def get_market_start_time(dt: datetime = None):
        return BotUtils.get_time_of_day(9, 15, 0, dt)

    """
    get_time_of_day
    """
    @staticmethod
    def get_time_of_day(hours: int,
                        minutes: int,
                        seconds: int,
                        dt: datetime = None):
        if dt == None:
            dt = datetime.now()
        dt = dt.replace(hour=hours, minute=minutes,
                        second=seconds, microsecond=0)
        return dt

    """
    wait_till_market_opens
    """
    @staticmethod
    async def wait_till_market_opens(who):
        now_epoch = BotUtils.get_epoch(datetime.now())
        mkt_start_epoch = BotUtils.get_epoch(BotUtils.get_market_start_time())
        wait_sec = mkt_start_epoch - now_epoch
        if wait_sec > 0:
            logging.info(
                f"{who}: Waiting for {wait_sec} secs till market opens...")
            asyncio.sleep(wait_sec)

    @staticmethod
    def print_strategy_status_w_params(wdb_strat_status_hash):
        """
        decoding BaseStrategy._publish_status_info_w_params
        """
        print("\t-*-*-*-*-[ Strategy Id => Status ]-*-*-*-*-")
        i = 1
        for k, v in wdb_strat_status_hash:
            strat_id = k.decode()
            ssinfo = json.loads(v)
            status = str(ssinfo[BotStatusKeys.status]).upper()
            underlying = ssinfo[BotStatusKeys.underlying]
            colored_status = status
            if status == "ACTIVE":
                colored_status = f"{BColors.OKGREEN}{colored_status}{BColors.ENDC}"
            if status == "STOPPED":
                colored_status = f"{BColors.RED}{colored_status}{BColors.ENDC}"
            # params
            pstr = ""
            for pk, pv in ssinfo[CtrlKeys.params].items():
                pstr += f"{pk}:{pv}, "
            pstr = pstr.strip(" ,")
            print(f"\t{i}. {strat_id} : {underlying} => {colored_status} | Params: {pstr}")
            i += 1
        print("\t----------------------------------")
