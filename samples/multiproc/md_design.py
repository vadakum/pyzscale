#Multiprocessing

from collections.abc import Callable
import multiprocessing as mp
import queue
from time import sleep

class Websocket:
    def __init__(self, handler, id) -> None:
        self.handler = handler
        self.id = id

    def change_id(self, id):
        self.id = id

    def start(self):
        tick_num = 0
        while True:
            self.handler.on_tick(self, self.id, tick_num)
            tick_num += 1
            sleep(0.2)
            if tick_num > 100:
                break


class ProcessWrap(mp.Process):
    def __init__(self, id, tick_q : mp.Queue, subs_q: mp.Queue):
        super().__init__()
        self.tick_q = tick_q
        self.subs_q = subs_q
        self.ws = Websocket(self, id)
    
    def run(self) -> None:
        self.ws.start()

    def on_tick(self, ws:Websocket, id, tick_num):
        try:
            data = {'id' : id, "num" : tick_num}
            self.tick_q.put_nowait(data)
            print(data)
        except queue.Full:
            print("queue is full!")
            pass
        try:
            sub = self.subs_q.get_nowait()
            ws.change_id(sub)
        except:
            pass

########################################################################
q1 = mp.Queue()
q2 = mp.Queue()
s1 = mp.Queue()
s2 = mp.Queue()
plist = [ProcessWrap(1, q1, s1), ProcessWrap(2, q2, s2)]
for p in plist:
    p.start()

while True:
    for qq in [{'q' :q1, 's' : s1}, {'q' :q2, 's' : s2}]:
        try:
            value = qq['q'].get_nowait()
            print(value)
            if value['num'] == 50:
                qq['s'].put(0.2)
        except queue.Empty:
            print("Queue is empty now!")
            pass
    sleep(0.2)