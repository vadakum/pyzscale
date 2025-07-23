


from common.walrus_redis import WalrusManager
from common.bcolors import BColors
from scale_bot.bot_common import *
from scale_bot.bot_utils import BotUtils

from argparse import ArgumentParser
from datetime import datetime
import json
import tabulate


def conv_spp(spp: StratPosPnl):
    x = {}
    x['inst_name'] = spp.inst_name
    x['ltp'] = int(spp.ltp)
    
    # Netpnl
    netpnl = int(spp.netpnl)
    if netpnl >= 0:
        x['netpnl'] = f"{BColors.UNDERLINE}{BColors.OKGREEN}{int(spp.netpnl)}{BColors.ENDC}"
    elif netpnl < 0:
        x['netpnl'] = f"{BColors.UNDERLINE}{BColors.RED}{int(spp.netpnl)}{BColors.ENDC}"
    
    # Rpnl
    rpnl = int(spp.pnl_real)
    if rpnl >= 0:
        x['rpnl'] = f"{BColors.OKGREEN}{int(spp.pnl_real)}{BColors.ENDC}"
    elif rpnl < 0:
        x['rpnl'] = f"{BColors.RED}{int(spp.pnl_real)}{BColors.ENDC}"
    
    # Upnl
    upnl = int(spp.pnl_unreal)
    if upnl >= 0:
        x['upnl'] = f"{BColors.OKGREEN}{int(spp.pnl_unreal)}{BColors.ENDC}"
    elif upnl < 0:
        x['upnl'] = f"{BColors.RED}{int(spp.pnl_unreal)}{BColors.ENDC}"
    
    # Netpos
    if spp.netpos >= 0:
        x['netpos'] = f"{BColors.OKGREEN}{spp.netpos}{BColors.ENDC}"
    elif spp.netpos < 0:
        x['netpos'] = f"{BColors.RED}{spp.netpos}{BColors.ENDC}"

    x['long'] = spp.long
    x['short'] = spp.short
    x['ords'] = spp.numord
    x['tcost'] = int(spp.tcost)
    x['ctype'] = spp.cost_type
    x['bv(lk)'] = round(spp.buy_value/100000, 2)
    x['sv(lk)'] = round(spp.sell_value/100000, 2)
    #x['inst_id'] = spp.inst_id
    return x


def print_pos_pnl(
        botid,
        wdb_strat_pos_hash,
        wdb_strat_status_hash):

    print("--------------------------------------------------------------")
    print(f"Strategy wise position for Bot: {botid}")
    print("--------------------------------------------------------------")

    BotUtils.print_strategy_status_w_params(wdb_strat_status_hash)

    # Print postion
    total_pnl = 0
    for k, v in wdb_strat_pos_hash:
        strat_id = k.decode()
        sy_json_dict = json.loads(v)
        strat_pos_pnl: dict[str, StratPosPnl] = {
            symbol: StratPosPnl.from_json(strat_pos_json)
            for symbol, strat_pos_json in sy_json_dict.items()
        }
        # Extract status from status hash
        strategy_pnl = sum([v.netpnl for v in strat_pos_pnl.values()])
        formatted_spps = [conv_spp(v) for v in strat_pos_pnl.values()]
        print(
            f"{tabulate.tabulate(formatted_spps, headers='keys', tablefmt='simple_grid')}"
        )
        spnl = int(strategy_pnl)
        spnl_str = f"{spnl}"
        if spnl > 0:
            spnl_str = f"{BColors.OKGREEN}{spnl}{BColors.ENDC}"
        elif spnl < 0:
            spnl_str = f"{BColors.RED}{spnl}{BColors.ENDC}"
        print(f" {strat_id}: PNL: ₹ {spnl_str}")
        total_pnl += strategy_pnl
    print("")
    tpnl = int(total_pnl)
    tpnl_str = f"{tpnl}"
    if total_pnl > 0:
        tpnl_str = f"{BColors.OKGREEN}{tpnl}{BColors.ENDC}"
    elif total_pnl < 0:
        tpnl_str = f"{BColors.RED}{tpnl}{BColors.ENDC}"
    print(f"### {botid} TOTAL PNL: ₹ {tpnl_str} ###")


def display(botuuid: str,
            pospnl: bool,
            orders: bool,
            ltp: bool):

    wdb = WalrusManager().get()
    ltp_hash_key = BotRedisKeyHelper.get_ltp_hash_key()
    strat_pos_hash_key = BotRedisKeyHelper.get_strat_pos_hash_key(botuuid)
    order_info_hash_key = BotRedisKeyHelper.get_order_info_hash_key(botuuid)
    strat_order_hash_key = BotRedisKeyHelper.get_strat_order_hash_key(botuuid)
    strat_status_hash_key = BotRedisKeyHelper.get_strat_status_hash(botuuid)

    wdb_ltp_hash = wdb.Hash(ltp_hash_key)
    wdb_strat_pos_hash = wdb.Hash(strat_pos_hash_key)
    wdb_order_info_hash = wdb.Hash(order_info_hash_key)
    wdb_strat_order_hash = wdb.Hash(strat_order_hash_key)
    wdb_strat_status_hash = wdb.Hash(strat_status_hash_key)

    if pospnl:
        print_pos_pnl(botuuid, wdb_strat_pos_hash,  wdb_strat_status_hash)
    if orders:
        print()
        print("*-*-*-*-*-*-[ Order Info ]-*-*-*-*-*-*")
        # order_infos = [print(v.decode()) for k, v in wdb_order_info_hash]
        ois: list[OrderInfo] = [OrderInfo.from_json(
            v) for k, v in wdb_order_info_hash]
        ois.sort(key=lambda x: x.order_timestamp)
        stripped_ois = []
        for oi in ois:
            x = {}
            x['orderid'] = oi.order_id
            x['otime'] = datetime.fromtimestamp(
                float(oi.order_timestamp)).isoformat(sep=' ')
            x['elag'] = round(float(oi.exchange_timestamp) -
                              float(oi.order_timestamp), 2)
            x['stratid'] = oi.strat_id
            x['symbol'] = oi.tradingsymbol
            x['dir'] = oi.transaction_type
            x['status'] = oi.order_status
            x['px'] = oi.price
            x['fillpx'] = oi.average_price
            x['q'] = oi.quantity
            x['Fillq'] = oi.filled_quantity
            x['Pq'] = oi.pending_quantity
            x['Xq'] = oi.cancelled_quantity
            x['ty'] = oi.order_type
            x['msg'] = oi.message
            stripped_ois.append(x)

        print(f"{tabulate.tabulate(stripped_ois, headers='keys')}")

    if ltp:
        ltp_map = {int(k.decode()): float(v.decode()) for k, v in wdb_ltp_hash}
        print(ltp_map)


def main():
    parser = ArgumentParser()
    parser.add_argument('-b', '--botid', required=True)
    parser.add_argument('-p', '--pospnl', default=False, action='store_true')
    parser.add_argument('-o', '--orders', default=False, action='store_true')
    parser.add_argument('-l', '--ltp', default=False, action='store_true')
    args = parser.parse_args()
    display(args.botid, args.pospnl, args.orders, args.ltp)


if __name__ == "__main__":
    main()
