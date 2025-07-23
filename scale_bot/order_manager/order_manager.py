

from dataclasses import dataclass, asdict, field
from kiteconnect import KiteConnect
from scale_bot.order_manager.order_common import OrderParam
from scale_bot.api_rate_limiter import AsyncOrderApiRateLimiter

from typing import Final
import logging
import asyncio

MaxApiAttempts : Final = 10
AttemptIntervalGap : Final = 2

class OrderManager:
    """
    OrderManager
    """
    def __init__(self, kconn: KiteConnect) -> None:
        self.kconn = kconn

    # async def place_new_order(self, op: OrderParam):
    #     order_id = f"1101{self.id}"
    #     self.id +=1
    #     logging.info(f"NewOrder request placed order_id={order_id} params: {asdict(op)}")
    #     return order_id

    # async def cancel_order(self, order_id: str):
    #     logging.info(f"CancelOrder request placed order_id={order_id}")

    async def place_new_order(self, op: OrderParam):
        for attempts in range(1, MaxApiAttempts + 1):
            try:
                order_id = await AsyncOrderApiRateLimiter.call_api(
                    lambda: self.kconn.place_order(
                        variety=self.kconn.VARIETY_REGULAR,
                        validity=self.kconn.VALIDITY_DAY,
                        exchange=op.exchange,
                        tradingsymbol=op.trading_symbol,
                        order_type=op.order_type,
                        product=op.product_type,
                        transaction_type=op.direction,
                        price=op.price,
                        quantity=op.quantity,
                    ))
            except Exception as ex:
                logging.error(f"NewOrder failed, params: {asdict(op)}, exception: {ex}")
                if attempts < MaxApiAttempts:
                    logging.info(f"NewOrder Retrying after {AttemptIntervalGap} sec ...")
                    await asyncio.sleep(AttemptIntervalGap)
                    continue
                else:
                    logging.info(f"NewOrder Retry max attempts {MaxApiAttempts} exceeded")
                    raise ex
            logging.info(f"NewOrder request placed order_id={order_id} params: {asdict(op)}")
            return order_id
        raise ValueError(f"Maxattempts logic error: {MaxApiAttempts}")
        

    async def cancel_order(self, order_id: str):
        for attempts in range(1, MaxApiAttempts + 1):
            try:
                await AsyncOrderApiRateLimiter.call_api(
                    self.kconn.cancel_order(
                        variety=self.kconn.VARIETY_REGULAR,
                        order_id=order_id
                    )
                )
            except Exception as ex:
                logging.error(f"Unable to cancel order_id={order_id}, exception: {ex}")
                if attempts < MaxApiAttempts:
                    logging.info(f"CancelOrder order_id={order_id}, retrying after {AttemptIntervalGap} sec...")
                    await asyncio.sleep(AttemptIntervalGap)
                    continue
                else:
                    logging.info(f"CancelOrder order_id={order_id}, retry max attempts={MaxApiAttempts} exceeded")
                    raise ex
            logging.info(f"CancelOrder order_id={order_id} request placed")
            return
        raise ValueError(f"Maxattempts logic error: {MaxApiAttempts}")
