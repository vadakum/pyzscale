import tabulate
import logging
from common.log_helper import LogHelper
from md.instrument_manager import (
    InstrumentManager,
    InstrumentType,
    ExpiryInd,
    InstField
)
import time

"""
Test
"""


def main():
    LogHelper.configure_logging(verbose=False)

    imgr = InstrumentManager('./instrument-20240307.dat', "20240307")


    logging.info("=== Printing active indices  ===")
    nse_indexs = imgr.get_active_indices()
    print(tabulate.tabulate(nse_indexs, headers='keys'))

    underlying = 'BANKNIFTY'
    logging.info(
        f"=== Getting future and options expiry dates for underlying {underlying}  ===")
    print(imgr.get_future_expiry_dates(underlying=underlying))
    print(imgr.get_option_expiry_dates(underlying=underlying))

    logging.info(
        f"=== Strike gap for NIFTY is {imgr.get_option_strike_gap('NIFTY')} ===")
    logging.info(
        f"=== Strike gap for {underlying} is {imgr.get_option_strike_gap(underlying)} ===")
    logging.info("=== Fetching single option === ")

    print(imgr.get_option_def_for_expiry_dt(underlying, InstrumentType.CE, '2024-03-13', 43800.0))

    logging.info("=== Instrument Def ===")
    for qg_instr in ['MIDCPNIFTY_I', 'NIFTY_F_0', 'MIDCPNIFTY_F_1', 'SBIN_EQ']:
        logging.info(f"{qg_instr} => {imgr.get_instrument_def(qg_instr)}")

    logging.info("=== Checking is_index method ===")
    is_index = imgr.is_index(imgr.get_instrument_def('SBIN_EQ')[InstField.InstrumentToken])
    logging.info(f"SBIN_EQ is_index ? {is_index}")
    is_index = imgr.is_index(imgr.get_instrument_def('MIDCPNIFTY_I')[InstField.InstrumentToken])
    logging.info(f"MIDCPNIFTY_I is_index ? {is_index}")

    logging.info(f"=== Fetch all option underlyings ===")
    underlyings = imgr.get_all_option_underlyings()
    logging.info(f"Total Underlying = {len(underlyings)}")

    ref_strike = 47900
    logging.info(
        f"=== Option instrument Resolution with Reference Strike= {ref_strike} ===")

    # Benchmark
    multi_instr = ['BANKNIFTY_C_0_99', 'BANKNIFTY_C_0_100', 'BANKNIFTY_C_0_101',
                   'BANKNIFTY_P_0_99', 'BANKNIFTY_P_0_100', 'BANKNIFTY_P_0_101',
                   ]
    for qg_instr in multi_instr:
        logging.info(
            f"{qg_instr} => {imgr.get_instrument_def(qg_instr, ref_strike)}")

    start_time = time.time()
    for qg_instr in multi_instr:
        imgr.get_instrument_def(qg_instr, ref_strike)
    logging.info(
        f"*** Time taken for 6 Option Instrument resolution = {round((time.time() - start_time) * 1000000)} us ***")

    ul_prices = [46949.5]

    atms = []
    start_time = time.time()
    for underlying_price in ul_prices:
        atms.append(imgr.calculate_atm(
            'BANKNIFTY', underlying_price=underlying_price, expiry_index=1))
    time_taken = time.time() - start_time
    logging.info(f"Atms: {atms}")
    logging.info(
        f"Time taken for computing atms : {round(time_taken * 1000000)} us ***")

    # print(underlyings)


if __name__ == "__main__":
    main()
