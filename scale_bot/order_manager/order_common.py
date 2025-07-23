

from dataclasses import dataclass, asdict, field
from scale_bot.bot_common import *


@dataclass
class OrderParam:
    """
    For order requests by strategy
    """
    exchange: str = Exchange.NFO.value
    product_type: str = ProductType.MIS.value
    order_type: str = OrderType.MARKET.value

    trading_symbol: str = ""
    direction: str = ""
    price: float = 0
    quantity: int = 0


class OrderDetails:
    """
    Mapping wrapper strore for:
    OrderParam <= Strategy
    OrderInfo  <= Broker
    """

    def __init__(self,
                 op: OrderParam = None,
                 oi: OrderInfo = None) -> None:
        self._order_param: OrderParam = op
        self._order_info: OrderInfo = oi

    @property
    def order_param(self) -> OrderParam:
        return self._order_param

    @order_param.setter
    def order_param(self, value):
        self._order_param = value

    @property
    def order_info(self) -> OrderInfo:
        return self._order_info

    @order_info.setter
    def order_info(self, value):
        self._order_info = value
