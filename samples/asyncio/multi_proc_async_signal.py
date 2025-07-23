import asyncio
import threading
import concurrent.futures
import time
import os
from signal import SIGINT, signal
from multiprocessing import Manager, Process
import logging

from common.log_helper import LogHelper
import multiprocessing_logging

class MultiProcSignalHandler:
    def __init__(self):
        signal(SIGINT, self.exit_gracefully)
        m = Manager()
        self.processing_flag = m.list([1])

    def exit_gracefully(self, signum, frame):
        print(f"Signal{signum}, Exiting gracefully pid: {os.getpid()}")
        self.processing_flag[0] = 0

    def keep_processing(self):
        return self.processing_flag[0] == 1


class NewProc(Process):
    def __init__(self, msg, signal_handler) -> None:
        super().__init__()
        self.msg = msg
        self.lock = threading.Lock() # This is to test new Process pickle issue
        self.signal_handler = sig_handler

    async def async_inside_new_proc(self):
        num = 0
        while self.signal_handler.keep_processing():
            num += 1
            logging.info(f"* pid:{os.getpid()} msg:{self.msg} num:{num}")
            with self.lock:
                await asyncio.sleep(0.1)

    def run(self):
        with asyncio.Runner(debug=None) as runner:
            runner.run(self.async_inside_new_proc())


class AsyncRun:
    def __init__(self) -> None:
        pass

    async def run(self, signal_handler: MultiProcSignalHandler):
        num = 0
        while signal_handler.keep_processing():
            num += 1
            logging.info(f"@ pid:{os.getpid()} msg:Direct Async num:{num}")
            await asyncio.sleep(0.15)

# """
# This code is not working
# Launching a new process using asyncio loop.run_in_executor doesn't work
# if the the class/method we are going to fork has threading.lock object
# """
# async def main(sig_handler):
#     print(f"Async main pid = {os.getpid()}")
#     loop = asyncio.get_running_loop()
#     astest = ASTest()
#     new_proc = NewProc("Running As Separate proc")
#     with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
#         tasks = []
#         async with asyncio.TaskGroup() as tg:
#             tasks.extend([
#                 loop.run_in_executor(pool, new_proc.run, sig_handler),
#                 tg.create_task(astest.run(sig_handler))
#             ])
#         asyncio.gather(*tasks)


async def main(sig_handler):
    logging.info(f"Async main pid = {os.getpid()}")
    astest = AsyncRun()
    tasks = []
    async with asyncio.TaskGroup() as tg:
        tasks.extend([
            tg.create_task(astest.run(sig_handler))
        ])
    asyncio.gather(*tasks)


if __name__ == '__main__':
    #LogHelper.configure_logging(verbose=False)
    LogHelper.configure_logging(
        verbose=True,
        log_name_prefix="ma_test",
        log_path="./",
        console=False)
    multiprocessing_logging.install_mp_handler()

    logging.info(f"Note @ and * lines should print")
    logging.info(f"Note @ ctrl + c should gracefully stop the program")
    time.sleep(2)

    sig_handler = MultiProcSignalHandler()
    new_proc = NewProc("Running As Separate proc", sig_handler)
    new_proc.start()

    logging.info(f"Main pid = {os.getpid()}")
    with asyncio.Runner(debug=None) as runner:
        runner.run(main(sig_handler))
    new_proc.join()    
