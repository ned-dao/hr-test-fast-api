from __future__ import annotations

from contextlib import contextmanager

from psycopg_pool import ConnectionPool


class PostgresManager:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: ConnectionPool | None = None

    def open(self) -> None:
        if self._pool is not None:
            return
        self._pool = ConnectionPool(
            conninfo=self._database_url,
            min_size=1,
            max_size=10,
            timeout=10,
            open=True,
        )

    def close(self) -> None:
        if self._pool is None:
            return
        self._pool.close()
        self._pool = None

    @property
    def pool(self) -> ConnectionPool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. Call open() first.")
        return self._pool

    @contextmanager
    def connection(self):
        with self.pool.connection() as conn:
            yield conn
