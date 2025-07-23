

from common.rate_limiter import RateLimiter, AsyncRateLimiter
from common.dt_helper import DTHelper
from typing import Final

# https://kite.trade/docs/connect/v3/exceptions/
# API rate limit
# ----------------
# end-point	        rate-limit
# -----------------------------
# Quote	                1req/second
# Historical candle	    3req/second
# Order placement	   10req/second andd 200 orders per minute
# All other endpoints  10req/second

ZQuoteApiLimit : Final = 1
ZHistoryApiLimit : Final = 3
ZOrderApiLimit : Final = 3
ZSerivceApiLimit : Final = 5

"""
ServiceApiRateLimiter
"""
class ServiceApiRateLimiter:
    @staticmethod
    @AsyncRateLimiter(max_calls=ZSerivceApiLimit, period=1)
    async def call_api(api_call):
        return api_call()

"""
OrderApiRateLimiter
"""
class AsyncOrderApiRateLimiter:
    @staticmethod
    @AsyncRateLimiter(max_calls=ZOrderApiLimit, period=1)
    async def call_api(api_call):
        return api_call()
