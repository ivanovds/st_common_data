import time

from redis import Redis, exceptions as redis_exceptions

from st_common_data.health.base import AbstractComponentHealthHandler
from st_common_data.exceptions import UnhealthComponentError


__all__ = ("RedisHealthHandler",)


class RedisHealthHandler(AbstractComponentHealthHandler):
    client: Redis
    name = "redis"

    def __init__(self, url: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.client = Redis.from_url(
            url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    def ping(self) -> None:
        try:
            pong = self.client.ping()
            if not pong:
                raise UnhealthComponentError("Ping returned false")
        except redis_exceptions.TimeoutError as e:
            raise UnhealthComponentError(e)
        except redis_exceptions.RedisError as e:
            raise UnhealthComponentError(e)

    def check_write_read(self) -> None:
        key = f"healthcheck:{int(time.time())}"
        timeout = 5
        try:
            result = self.client.set(key, "1", ex=timeout, nx=True)
            if not result:
                raise UnhealthComponentError("Can't write")
        except redis_exceptions.RedisError as e:
            raise UnhealthComponentError(e)

        try:
            result = self.client.get(key)
            if not result:
                raise UnhealthComponentError("Can't read or can't find healthcheck key")
        except redis_exceptions.RedisError as e:
            raise UnhealthComponentError(e)

    def check_startup(self) -> None:
        self.ping()

    def check_live(self) -> None:
        self.ping()
        self.check_write_read()

    def check_ready(self) -> None:
        self.ping()
        self.check_write_read()


