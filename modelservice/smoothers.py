

from abc import ABCMeta, abstractmethod
from collections import deque
import pandas as pd

class ISmoother(object, metaclass=ABCMeta):
    """
    ISmoother interface
    """
    def __init__(self) -> None:
        self._ready = False
        self._value = None

    @property
    def ready(self):
        return self._ready

    @ready.setter
    def ready(self, val):
        self._ready = val

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val

    @abstractmethod
    def add_sample(self, sample: float):
        pass

    @abstractmethod
    def reset(self):
        pass

    def is_ready(self) -> bool:
        return self._ready

    @abstractmethod
    def get_value(self) -> float:
        pass

class SMA(ISmoother):
    """
    Rolling SMA
    """
    def __init__(self, args: dict) -> None:
        super().__init__()
        self.qlen = int(args['timeperiod'])
        self.deque = deque([], maxlen=self.qlen)

    def add_sample(self, sample: float):
        self.value = sample
        if self.qlen <= 1:
            self.ready = True
            return
        self.deque.append(sample)
        if not self.ready:
            if len(self.deque) >= self.qlen:
                self.ready = True

    def get_value(self) -> float:
        if self.qlen <= 1:
            return self.value
        self.value = sum(self.deque) / len(self.deque)
        return self.value
        
    def reset(self):
        self.deque.clear()
        self.ready = False

class EMA(ISmoother):
    """
    Rolling EMA
    """
    def __init__(self, args: dict) -> None:
        super().__init__()
        self.span = int(args['timeperiod'])
        self.alpha = 2 / (self.span + 1)
        self.avg = None

    def add_sample(self, sample: float):
        self.value = sample
        if self.avg == None:
            self.avg = sample
            self.ready = True            
        else:
            self.avg = self.alpha * sample + (1 - self.alpha ) * self.avg
        
    def get_value(self) -> float:
        self.value = self.avg
        return self.value

    def reset(self):
        self.avg = None
        self.ready = False

class TEMA(ISmoother):
    """
    Rolling TEMA
    """
    def __init__(self, args: dict) -> None:
        super().__init__()
        self.ema1 = EMA(args)
        self.ema2 = EMA(args)
        self.ema3 = EMA(args)

    def add_sample(self, sample: float):
        self.ema1.add_sample(sample)
        self.ema2.add_sample(self.ema1.get_value())
        self.ema3.add_sample(self.ema2.get_value())
        self.ready = True

    def get_value(self) -> float:
        ema1 = self.ema1.get_value()
        ema2 = self.ema2.get_value()
        ema3 = self.ema3.get_value()
        self.value = (3 * ema1) - (3 * ema2) + ema3
        return self.value

    def reset(self):
        self.ema1.reset()
        self.ema2.reset()
        self.ema3.reset()
        self.ready = False

class StableWin(ISmoother):
    """
    StableWin
    """
    def __init__(self, args) -> None:
        super().__init__()
        self.qlen = int(args['timeperiod'])
        self.deque = deque([], maxlen=self.qlen)

    def add_sample(self, sample: float):
        self.value = False
        self.deque.append(sample)
        if not self.ready:
            if len(self.deque) >= self.qlen:
                self.ready = True

    def get_value(self) -> float:
        if not self.ready:
            return self.value
        self.value = (self.deque.count(self.deque[-1]) == self.qlen)
        return self.value
        
    def reset(self):
        self.deque.clear()
        self.ready = False


class SmootherFactory:
    """
    Smoother Factory
    """

    @staticmethod
    def create(args: dict):
        if 'type' not in args:
            raise ValueError(f"args does not have smoother `type`")
        
        stype = str(args['type']).upper()
        
        if stype == "SMA":
            return SMA(args)
        
        if stype == "EMA":
            return EMA(args)
        
        if stype == "TEMA":
            return TEMA(args)
        
        elif stype == "STABLEWIN":
            return StableWin(args)
        
        else:
            raise ValueError(
                f"invalid smoother type {stype} expecting one of [whit, ema]")
