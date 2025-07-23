
import signal
from signal import Signals
from multiprocessing import Manager
import os


class MultiProcSignalHandler:
    def __init__(self,
                 exit_signals: Signals):
        for signum in exit_signals:
            signal.signal(signum, self._exit_gracefully)
        #signal.signal(signal.SIGINT, signal.SIG_IGN)
        #signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        m = Manager()

        self._processing_flag = m.list([1])

    def register_signal(self, signum, callback):
        signal(signum, callback)

    def _exit_gracefully(self, signum, frame):
        self._processing_flag[0] = 0        
        print(
            f"MultiProcSignalHandler: signum:{signum}, pid: {os.getpid()}, exiting gracefully")

    def keep_processing(self):
        return self._processing_flag[0] == 1
