import asyncio

async def producer(q: asyncio.Queue):
    num = 0
    while True:
        num = num + 1
        await q.put(num)
        print(f"Produced: {num}")
        await asyncio.sleep(0.5)


async def run_consumer(q: asyncio.Queue):
    while True:
        num = await q.get()
        print(f"Consumed: {num}")
        await asyncio.sleep(1)
        if (num % 10) == 0:
            break


async def consumer(q: asyncio.Queue):
    while True:
        await run_consumer(q)
        await asyncio.sleep(0)
        print("Re-running consumer")


async def q_size_watcher(q: asyncio.Queue):
    while True:
        print(f"Q Size: {q.qsize()}")
        await asyncio.sleep(5)


def main():
    event_loop = asyncio.get_event_loop()
    q = asyncio.Queue()
    # create_task on event loop not on asyncio directly
    tasks = [event_loop.create_task(consumer(q)),
             event_loop.create_task(producer(q)),
             event_loop.create_task(q_size_watcher(q)),
             ]
    try:
        event_loop.run_forever()
    except KeyboardInterrupt:
        [task.cancel() for task in tasks]
        asyncio.gather(*tasks, return_exceptions=True)
        pass
    finally:
        print("Closing the event loop")
        event_loop.close()


if __name__ == "__main__":
    main()
