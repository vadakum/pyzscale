

from scale_bot.strategy.strat_base import BaseStrategy
from scale_bot.strategy.strat_auto_scale_fut import StratAutoScaleFut

class StratFactory:
    @staticmethod
    def create(name, **kwargs) -> BaseStrategy:
        if name == "AutoSFut":
            return StratAutoScaleFut(**kwargs)
        else:
            raise ValueError(
                f"invalid strategy name {name}")
