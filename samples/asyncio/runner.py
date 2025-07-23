import asyncio
import sys

async def main():
    sleep_seconds = 1
    print(f"Sleeping for {sleep_seconds} seconds")
    await asyncio.sleep(sleep_seconds)
    print("Done sleeping")


async def test():
    await asyncio.sleep(0)
    return "This was async test function"

#################################
# simple test to run a coroutine direcly
result = asyncio.run(test())    
print(result)
#################################

#################################
# Runner test
print("Testing asyncio...")
print(f"Python system version={sys.version_info}")
print("Runner is available from 3.11 onwards only!")
with asyncio.Runner(debug=None) as runner:
    runner.run(main())


# These two below methods are also available
# [1]
# import asyncio
# import uvloop
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# [2]
# import asyncio
# import uvloop
# loop = uvloop.new_event_loop()
# asyncio.set_event_loop(loop)
