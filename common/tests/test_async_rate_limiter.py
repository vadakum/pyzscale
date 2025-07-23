from common.rate_limiter import RateLimiter, AsyncRateLimiter
from common.dt_helper import DTHelper
from datetime import datetime
import time
from threading import Thread
import asyncio

MaxCalls = 1
Period = 1


class ApiRateLimiter:
    @staticmethod
    @RateLimiter(max_calls=MaxCalls, period=Period)
    def call_api(api_call):
        return api_call()


class AsyncApiRateLimiter:
    @staticmethod
    @AsyncRateLimiter(max_calls=MaxCalls, period=Period)
    async def call_api(api_call):
        return api_call()


# ----------------------------------------------------------------------------------------------------------------
last_time = time.monotonic()


def fun(arg1, arg2):
    global last_time
    curr_time = time.monotonic()
    diff = round(curr_time - last_time, 3)
    last_time = curr_time
    print(
        f"==> Api Called with arg:{arg1} {arg2} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')} after {diff} sec")
    return f"{arg1}~{arg2}"

def threaded_test(arg):
    print("=== quick calls started ===")
    ret_vals = []
    for i in range(1, 5):
        ret_vals.append(ApiRateLimiter.call_api(lambda: fun(arg, i)))
    print(ret_vals)
    print("=== quick calls ended ===")
    time.sleep(2)
    print("== 2 seconds passed in the program, slow calls ==")
    for i in range(5, 10):
        ApiRateLimiter.call_api(lambda: fun(arg, i))
        time.sleep(0.3)

print(f"=== observe that sec field of datetime value, its number should be in sync with {MaxCalls} in {Period} sec ===")
t1 = Thread(target=threaded_test, args=("Th-1",))
#t2 = Thread(target=threaded_test, args=("Th-2",))
#t3 = Thread(target=threaded_test, args=("Th-3",))
t1.start()
#t2.start()
#t3.start()
t1.join()
#t2.join()
#t3.join()

# ----------------------------------------------------------------------------------------------------------------


async def run_limiter1():
    ret_vals = []
    for i in range(1, 10):
        ret_vals.append(await AsyncApiRateLimiter.call_api(lambda: fun("Async-1", i)))
    return ret_vals


async def run_limiter2():
    ret_vals = []
    for i in range(1, 5):
        ret_vals.append(await AsyncApiRateLimiter.call_api(lambda: fun("Async-2", i)))
    return ret_vals


async def loop():
    for i in range(1, 15):
        print("*")
        await asyncio.sleep(1)


async def test_async():
    tasks = []
    try:
        async with asyncio.TaskGroup() as tg:
            tasks.extend([
                tg.create_task(loop()),
                tg.create_task(run_limiter1()),
                tg.create_task(run_limiter2())
            ])
        final_results = await asyncio.gather(*tasks)
        print(final_results)
    except* TypeError as te:
        for errors in te.exceptions:
            print(errors)
    except* Exception as ex:
        print(ex.exceptions)


asyncio.run(test_async())
