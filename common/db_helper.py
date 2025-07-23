

from psycopg_pool import ConnectionPool, AsyncConnectionPool
from psycopg import Cursor, AsyncCursor
import pandas as pd

class PoolConnInfo:
    def __init__(self, host: str, port: int, database: str, user: str, password=""):
        self._conn_info = f"host={host} port={port} dbname={database} user={user}"
        if password:
            self._conn_info += f" password={password}"

    def get_conn_info(self):
        return self._conn_info


class DbPool(ConnectionPool):
    def __init__(self, pool_conn_info: PoolConnInfo):
        super().__init__(pool_conn_info.get_conn_info(), open=True)


class AsyncDbPool(AsyncConnectionPool):
    def __init__(self, pool_conn_info: PoolConnInfo):
        super().__init__(pool_conn_info.get_conn_info(), open=True)


class QueryHelper:
    @staticmethod
    def select_as_df(cur: Cursor, query, data=None):
        cur.execute(query, data)
        data = cur.fetchall()
        cols = [col[0] for col in cur.description]
        return pd.DataFrame.from_records(data, columns=cols)

    @staticmethod
    async def async_select_as_df(cur: AsyncCursor, query: str, data=None):
        await cur.execute(query, data)
        data = await cur.fetchall()
        cols = [col[0] for col in cur.description]
        return pd.DataFrame.from_records(data, columns=cols)
