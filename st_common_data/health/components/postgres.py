from __future__ import annotations
import time
from typing import TypedDict

import psycopg2
from psycopg2 import Error as PsycopgError

from st_common_data.health.base import AbstractComponentHealthHandler
from st_common_data.exceptions import UnhealthComponentError
from st_common_data.utils.db import parse_url


__all__ = ("PostgresHealthHandler", "ReadOnlyPostgresHealthHandler",)


class ConnectionDictType(TypedDict):
    USER: str 
    PASSWORD: str
    HOST: str
    PORT: str
    NAME: str


class AbstractPostgresHealthHanlder(AbstractComponentHealthHandler):
    name = "postgres"

    user: str
    password: str
    host: str
    port: str
    database: str

    def __init__(
        self,
        *args,
        user: str,
        password: str,
        port: str,
        database: str,
        host: str,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.password = password
        self.port = port
        self.database = database
        self.host = host

    @classmethod
    def from_url(
        cls,
        url: str,
        name: str | None = None,
    ) -> PostgresHealthHandler:
        result = parse_url(url)
        return cls(
            user=result.username,  # type: ignore
            password=result.password,  # type: ignore
            host=result.host,  # type: ignore
            port=result.port,  # type: ignore
            database=result.database,  # type: ignore
            name=name,
        )

    @classmethod
    def from_connection_dict(
        cls,
        connection_dict: ConnectionDictType,
        name: str | None = None,
    ) -> PostgresHealthHandler:
        return cls(
            user=connection_dict["USER"],
            password=connection_dict["PASSWORD"],
            host=connection_dict["HOST"],
            port=connection_dict["PORT"],
            database=connection_dict["NAME"],
            name=name,
        )

    def ping(self) -> None:
        try:
            with psycopg2.connect(
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                host=self.host,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
        except PsycopgError as e:
            raise UnhealthComponentError(e)


class ReadOnlyPostgresHealthHandler(AbstractPostgresHealthHanlder):
    def check_startup(self) -> None:
        self.ping()

    def check_live(self) -> None:
        self.ping()

    def check_ready(self) -> None:
        self.ping()


class PostgresHealthHandler(AbstractComponentHealthHandler):

    def check_write_read(self) -> None:
        try:
            with psycopg2.connect(
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                host=self.host,
            ) as conn:
                conn.autocommit = False
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TEMP TABLE IF NOT EXISTS healthcheck_tmp (
                            id         SERIAL,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            val        TEXT
                        ) ON COMMIT DROP
                    """)

                    value = f"health-{int(time.time())}"
                    cur.execute(
                        "INSERT INTO healthcheck_tmp (val) VALUES (%s)",
                        (value,),
                    )

                    cur.execute(
                        "SELECT val FROM healthcheck_tmp "
                        "ORDER BY id DESC LIMIT 1"
                    )
                    row = cur.fetchone()
                    if not row:
                        raise UnhealthComponentError(
                            "Can't read back healthcheck row from DB"
                        )

                    (result_val,) = row
                    if result_val != value:
                        raise UnhealthComponentError(
                            "Healthcheck value mismatch when reading from DB"
                        )

                conn.rollback()
        except PsycopgError as e:
            conn.rollback()
            raise UnhealthComponentError(e)

    def check_startup(self) -> None:
        self.ping()

    def check_live(self) -> None:
        self.ping()
        self.check_write_read()

    def check_ready(self) -> None:
        self.ping()
        self.check_write_read()
