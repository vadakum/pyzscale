# class EMA(ISmoother):
#     """
#     Rolling EMA
#     """
#     def __init__(self, args: dict) -> None:
#         super().__init__()
#         self.qlen = int(args['timeperiod'])
#         self.deque = deque([], maxlen=self.qlen)

#     def add_sample(self, sample: float):
#         self.value = sample
#         if self.qlen <= 1:
#             self.ready = True
#             return
#         self.deque.append(sample)
#         if not self.ready:
#             if len(self.deque) >= self.qlen:
#                 self.ready = True

#     def get_value(self) -> float:
#         if self.qlen <= 1:
#             return self.value
#         df = pd.DataFrame({'samples' : self.deque})
#         df['ewm'] = df.ewm(span=self.qlen, adjust=False).mean()
#         self.value = float(df['ewm'].iloc[-1])
#         return self.value

#     def reset(self):
#         self.deque.clear()
#         self.ready = False

# class TEMA(ISmoother):
#     """
#     Rolling TEMA
#     """
#     def __init__(self, args: dict) -> None:
#         super().__init__()
#         self.qlen = int(args['timeperiod'])
#         self.deque = deque([], maxlen=self.qlen)

#     def add_sample(self, sample: float):
#         self.value = sample
#         if self.qlen <= 1:
#             self.ready = True
#             return
#         self.deque.append(sample)
#         if not self.ready:
#             if len(self.deque) >= self.qlen:
#                 self.ready = True

#     def get_value(self) -> float:
#         if self.qlen <= 1:
#             return self.value
#         df = pd.DataFrame({'samples' : self.deque})
#         df['ewm1'] = df['samples'].ewm(span=self.qlen, adjust=False).mean()
#         df['ewm2'] = df['ewm1'].ewm(span=self.qlen, adjust=False).mean()
#         df['ewm3'] = df['ewm2'].ewm(span=self.qlen, adjust=False).mean()
#         df['tema'] = (3 * df['ewm1']) - (3 * df['ewm2']) + df['ewm3']
#         self.value = float(df['tema'].iloc[-1])  
#         return self.value

#     def reset(self):
#         self.deque.clear()
#         self.ready = False