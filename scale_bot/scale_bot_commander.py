

from argparse import ArgumentParser
from common.walrus_redis import WalrusManager
from scale_bot.bot_common import *
from common.bcolors import BColors
from scale_bot.bot_utils import BotUtils

from datetime import datetime
from typing import Union

import json
import os


def prepare_command(cmd_str: str) -> Union[dict | None]:
    ctok = cmd_str.strip().split(' ')
    ntok = len(ctok)
    cmd = ctok[0]
    if cmd == "startall":
        return {
            CtrlKeys.strat_id.value: "all",
            CtrlKeys.msg.value: {CtrlKeys.action.value: CtrlKeys.start.value}
        }
    elif cmd == "stopall":
        return {
            CtrlKeys.strat_id.value: "all",
            CtrlKeys.msg.value: {CtrlKeys.action.value: CtrlKeys.stop.value}
        }

    elif cmd == "start" or cmd == "stop":
        if ntok > 1:
            return {
                CtrlKeys.strat_id.value: ctok[1],
                CtrlKeys.msg.value: {
                    CtrlKeys.action.value: cmd}
            }
        else:
            print(
                f"{BColors.RED}Error:{BColors.ENDC} strategy id missing in the command: {cmd}")
            return None
    elif cmd == "up":
        if ntok > 1:
            params = {}
            istr = input(
                f"-> {BColors.OKCYAN}Subc:{BColors.ENDC} Enter stoploss (enter to skip):> ")
            if istr:
                params[BotKeys.stop_loss.value] = float(istr)
            istr = input(
                f"-> {BColors.OKCYAN}Subc:{BColors.ENDC} Enter profit target (enter to skip):> ")
            if istr:
                params[BotKeys.profit_target.value] = float(istr)
            if params.keys():
                return {
                    CtrlKeys.strat_id.value: ctok[1],
                    CtrlKeys.msg.value: {
                        CtrlKeys.action.value: CtrlKeys.update.value,
                        CtrlKeys.params.value: params
                    }
                }
            else:
                print(f"{BColors.OKCYAN} command skipped {cmd}")
        else:
            print(
                f"{BColors.RED}Error:{BColors.ENDC} strategy id missing in the command: {cmd}")
        return None

    else:
        print(f"{BColors.RED}Error:{BColors.ENDC} invalid command: {cmd}")
        return None


def print_help(botuuid):
    """
    help
    """
    print(" --------------------------------")
    print(" o-o-o-[Available commands]-o-o-o")
    print(" --------------------------------")
    print(f" ?                  : strategy status with params info")
    print(f" start <strategyid> / startall : start one or all strategies")
    print(f" stop  <strategyid> / stopall  : stop one or all strategies")
    print(f" up  <strategyid> : update strategy params")


def commander(botuuid: str):
    """
    commander
    """
    wdb = WalrusManager().get()
    wdb_ctrl_stream = wdb.Stream(
        BotRedisKeyHelper.get_strat_control_stream_key(botuuid))
    wdb_strat_status_hash = wdb.Hash(
        BotRedisKeyHelper.get_strat_status_hash(botuuid))

    print_help(botuuid)
    print("")
    while True:
        print("")
        cmd_str = input(
            f"-> {BColors.OKGREEN}Command{BColors.ENDC} [ quit(q), help(h), clear(c) ]:> ")
        if cmd_str == "c" or cmd_str == "clear":
            os.system("clear")
            print_help(botuuid)
        elif cmd_str == "h":
            print_help(botuuid)
        elif cmd_str == "?":
            BotUtils.print_strategy_status_w_params(wdb_strat_status_hash)
        elif cmd_str == 'q':
            break
        else:
            cmd_dict = prepare_command(cmd_str)
            if not cmd_dict:
                continue
            wdb_ctrl_stream.add(
                {'t': int(datetime.now().timestamp()), 'v': json.dumps(cmd_dict)})
            print(
                f"{BColors.OKGREEN}Success! {BColors.ENDC} command sent to {botuuid}")


def main():
    parser = ArgumentParser()
    parser.add_argument('-b', '--botid', required=True)
    args = parser.parse_args()
    commander(args.botid)


if __name__ == "__main__":
    main()
