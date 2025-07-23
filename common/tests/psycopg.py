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

def normal_test():
    with DbPool(pool_conn_info) as pool:
        with pool.connection() as conn:
            conn.row_factory = dict_row
            conn.cursor_factory = ClientCursor  # mogrify is in ClientCursor
            with conn.cursor() as cur:

                cur.execute("drop table if exists test_xx_dbtest")

                cur.execute("""
                    CREATE TABLE test_xx_dbtest (
                        id serial PRIMARY KEY,
                        num integer,
                        data text)
                    """)
                # The correct conversion (no SQL injections!)
                cur.execute("INSERT INTO test_xx_dbtest (num, data) VALUES (%s, %s) RETURNING id", (100, "abcdef"))
                data = cur.fetchone()
                print("RETURNING Test id:", data["id"])


                # Using mogrify to do multivalue inserts, but requires client cursor
                args_str = ','.join(cur.mogrify(
                    (f"(%(num)s, "
                     f"%(data)s)"), x) for x in [
                    {'num': 200, 'data': 'ak'}, {'data': 'bkk', 'num': 300}])
                cur.execute(
                    (f"INSERT INTO test_xx_dbtest "
                     f"(num, data) VALUES "
                    ) + args_str)
                print("Normal Mogrified args = ", args_str)

                conn.commit()

                # Testing rollback
                conn.transaction()
                cur.execute(
                    "INSERT INTO test_xx_dbtest (num, data) VALUES (%s, %s)", (400, "abcdef"))
                conn.rollback()

                # Fetch and display the data
                cur.execute("SELECT * FROM test_xx_dbtest")
                data = cur.fetchall()
                print(data)

print("*********Normal DB test*********")
normal_test()
