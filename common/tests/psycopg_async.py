# Note: the module name is psycopg, not psycopg3
import asyncio
import psycopg
from psycopg import ClientCursor, AsyncClientCursor, Rollback
from psycopg.rows import dict_row
from common.db_helper import DbPool, AsyncDbPool, PoolConnInfo

db_host = "localhost"
db_port = 5432
db_name = "testdb"
db_user = "testuser"
db_pass = "testuser1234"
pool_conn_info = PoolConnInfo(
    host=db_host, port=db_port, database=db_name, user=db_user,  password=db_pass)


async def async_test():
    async with AsyncDbPool(pool_conn_info) as pool:
        async with pool.connection() as conn:
            conn.row_factory = dict_row
            conn.cursor_factory = AsyncClientCursor  # mogrify is in ClientCursor
            async with conn.cursor() as cur:

                await cur.execute("drop table if exists test_xx_dbtest")

                await cur.execute("""
                    CREATE TABLE test_xx_dbtest (
                        id serial PRIMARY KEY,
                        num integer,
                        data text)
                    """)

                # The correct conversion (no SQL injections!)
                await cur.execute("INSERT INTO test_xx_dbtest (num, data) VALUES (%s, %s) returning id", (100, "abcdef"))
                data = await cur.fetchone()
                print("RETURNING Test id:", data["id"])

                # Testing rollback
                async with conn.transaction() as inner_tran:
                    await cur.execute("INSERT INTO test_xx_dbtest (num, data) VALUES (%s, %s)", (400, "abcdef"))
                    raise Rollback(inner_tran)

                # Using mogrify to do multivalue inserts, but requires client cursor
                args_str = ','.join(cur.mogrify("(%s,%s)", x)
                                    for x in [(200, 'ak'), (300, 'bk')])
                await cur.execute("INSERT INTO test_xx_dbtest (num, data) VALUES " + args_str)
                print("Mogrified args = ", args_str)

                await conn.commit()

                print("continuing after rollback...")
                # Fetch and display the data
                await cur.execute("SELECT * FROM test_xx_dbtest")
                data = await cur.fetchall()
                print(data)

print("*********Async DB test*********")
asyncio.run(async_test())
