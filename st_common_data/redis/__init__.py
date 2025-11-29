import logging
import random
import ssl
import urllib.parse
from typing import List, Optional, Union, Any, Dict, Tuple, Callable
import redis
from redis.cluster import RedisCluster
import asyncio
from redis import asyncio as aioredis
import functools
import time
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class MasterSlavesRedis:
    """
    Custom Redis class for sync and async communication with master-slave Redis setup.
    All write operations are done through master, while read operations can be done through slaves.
    Automatically detects if connected to a slave and finds the master.
    """

    def __init__(
        self,
        host: Union[str, List[Tuple[str, int]]],
        port: Optional[int] = 6379,
        db: int = 0,
        password: Optional[str] = None,
        cluster_mode: bool = False,
        socket_timeout: int = 15,
        socket_connect_timeout: int = 15,
        retry_on_timeout: bool = True,
        decode_responses: bool = True,
        **kwargs
    ):
        """
        Initialize MasterSlavesRedis client.

        Args:
            host: Redis host (string) or list of (host, port) tuples for cluster mode
            port: Redis port (not used in cluster mode)
            db: Redis database number
            password: Redis password
            cluster_mode: Whether to use Redis Cluster
            socket_timeout: Socket timeout
            socket_connect_timeout: Socket connection timeout
            retry_on_timeout: Whether to retry on timeout
            decode_responses: Whether to decode byte responses to strings
            **kwargs: Additional arguments to pass to Redis client
        """
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.kwargs = kwargs

        # Initialize Redis client based on mode
        if cluster_mode:
            if isinstance(host, str):
                raise ValueError("Cluster mode requires a list of (host, port) tuples")

            self.cluster = RedisCluster(
                startup_nodes=host,
                password=password,
                decode_responses=decode_responses,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                retry_on_timeout=retry_on_timeout,
                **kwargs
            )

            self.master = self.cluster
            self.slaves = self.cluster

        else:
            if isinstance(host, list):
                # If host is a list, use the first element
                host, port = host[0]

            initial_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                retry_on_timeout=retry_on_timeout,
                decode_responses=decode_responses,
                **kwargs
            )

            try:
                replication_info = initial_client.info(section='replication')
                if replication_info['role'] == 'slave':
                    logger.info(f"Connected to slave, switching to master at {replication_info['master_host']}:{replication_info['master_port']}")

                    self.master = redis.Redis(
                        host=replication_info['master_host'],
                        port=replication_info['master_port'],
                        db=db,
                        password=password,
                        socket_timeout=socket_timeout,
                        socket_connect_timeout=socket_connect_timeout,
                        retry_on_timeout=retry_on_timeout,
                        decode_responses=decode_responses,
                        **kwargs
                    )

                    self.slaves = initial_client
                else:
                    self.master = initial_client
                    self.slaves = initial_client
            except Exception as e:
                logger.warning(f"Failed to check Redis role, using as both master and slave: {e}")
                self.master = initial_client
                self.slaves = initial_client

        self.async_master = None
        self.async_slaves = None

    @classmethod
    def from_url(cls, url, **kwargs):
        """
        Create MasterSlavesRedis instance from Redis URL.

        Args:
            url: Redis URL in format redis://[[username]:[password]]@host:port/db
                 or rediss:// for SSL connection
                 Query parameters can include ssl_cert_reqs=none
            **kwargs: Additional arguments to pass to Redis client

        Returns:
            MasterSlavesRedis instance
        """
        connection_params = redis.connection.parse_url(url)

        host = connection_params.pop('host')
        port = connection_params.pop('port')
        db = connection_params.pop('db')
        password = connection_params.pop('password', None)

        ssl_enabled = url.startswith('rediss://')
        if ssl_enabled:
            connection_params['ssl'] = True

        ssl_cert_reqs = connection_params.pop('ssl_cert_reqs', None)
        if ssl_cert_reqs is not None:
            if ssl_cert_reqs.lower() == 'none':
                connection_params['ssl_cert_reqs'] = ssl.CERT_NONE
            elif ssl_cert_reqs.lower() == 'optional':
                connection_params['ssl_cert_reqs'] = ssl.CERT_OPTIONAL
            elif ssl_cert_reqs.lower() == 'required':
                connection_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
        elif ssl_enabled and 'ssl_cert_reqs' not in kwargs:
            connection_params['ssl_cert_reqs'] = ssl.CERT_NONE

        if 'connection_class' in connection_params:
            connection_params.pop('connection_class')

        return cls(
            host=host,
            port=port,
            db=db,
            password=password,
            **{**connection_params, **kwargs}
        )

    async def init_async(self):
        """
        Initialize async Redis clients.
        Must be called before using any async methods.
        """
        if self.async_master is None or self.async_slaves is None:
            master_host = self.master.connection_pool.connection_kwargs['host']
            master_port = self.master.connection_pool.connection_kwargs['port']

            ssl_enabled = self.kwargs.get('ssl', False)
            master_url = f"rediss://" if ssl_enabled else f"redis://"

            if self.password:
                master_url += f":{self.password}@"
            master_url += f"{master_host}:{master_port}/{self.db}"

            async_kwargs = self.kwargs.copy()
            if ssl_enabled:
                async_kwargs.pop('ssl', None)

            self.async_master = aioredis.from_url(
                master_url,
                decode_responses=self.decode_responses,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                **async_kwargs
            )

            if self.slaves is not self.master:
                slave_host = self.slaves.connection_pool.connection_kwargs['host']
                slave_port = self.slaves.connection_pool.connection_kwargs['port']

                slave_url = f"rediss://" if ssl_enabled else f"redis://"

                if self.password:
                    slave_url += f":{self.password}@"
                slave_url += f"{slave_host}:{slave_port}/{self.db}"

                self.async_slaves = aioredis.from_url(
                    slave_url,
                    decode_responses=self.decode_responses,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    **async_kwargs
                )
            else:
                self.async_slaves = self.async_master

            try:
                replication_info = await self.async_master.info(section='replication')
                if replication_info['role'] == 'slave':
                    logger.info(f"Async connected to slave, switching to master at {replication_info['master_host']}:{replication_info['master_port']}")

                    master_url = f"rediss://" if ssl_enabled else f"redis://"

                    if self.password:
                        master_url += f":{self.password}@"
                    master_url += f"{replication_info['master_host']}:{replication_info['master_port']}/{self.db}"

                    self.async_master = aioredis.from_url(
                        master_url,
                        decode_responses=self.decode_responses,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                        **async_kwargs
                    )
            except Exception as e:
                logger.warning(f"Failed to check async Redis role: {e}")

    def _get_client(self, use_master: bool = False):
        """Get appropriate Redis client based on use_master flag"""
        return self.master if use_master else self.slaves

    async def _get_async_client(self, use_master: bool = False):
        """Get appropriate async Redis client based on use_master flag"""
        if self.async_master is None:
            await self.init_async()
        return self.async_master if use_master else self.async_slaves

    @classmethod
    def _create_read_method(cls, method_name: str):
        """Create a read method that delegates to the appropriate client"""
        def method(self, *args, use_master: bool = False, **kwargs):
            client = self._get_client(use_master)
            return getattr(client, method_name)(*args, **kwargs)
        return method

    @classmethod
    def _create_async_read_method(cls, method_name: str):
        """Create an async read method that delegates to the appropriate client"""
        async def method(self, *args, use_master: bool = False, **kwargs):
            client = await self._get_async_client(use_master)
            return await getattr(client, method_name)(*args, **kwargs)
        return method

    @classmethod
    def _create_write_method(cls, method_name: str):
        """Create a write method with reconnection support"""
        @cls.reconnect_on_error()
        def method(self, *args, **kwargs):
            return getattr(self.master, method_name)(*args, **kwargs)
        return method

    @classmethod
    def _create_async_write_method(cls, method_name: str):
        """Create an async write method with reconnection support"""
        @cls.areconnect_on_error()
        async def method(self, *args, **kwargs):
            if self.async_master is None:
                await self.init_async()
            return await getattr(self.async_master, method_name)(*args, **kwargs)
        return method

    def reconnect_master(self):
        """
        Reconnect to the Redis master.

        Returns:
            True if reconnection was successful, False otherwise
        """
        try:
            # Try to get current master info from slaves if possible
            if self.slaves is not self.master:
                try:
                    replication_info = self.slaves.info(section='replication')
                    master_host = replication_info['master_host']
                    master_port = replication_info['master_port']
                    logger.info(f"Reconnecting to master at {master_host}:{master_port}")
                except Exception as e:
                    # If we can't get info from slaves, use the current master connection info
                    logger.warning(f"Could not get master info from slaves: {e}")
                    master_host = self.master.connection_pool.connection_kwargs['host']
                    master_port = self.master.connection_pool.connection_kwargs['port']
            else:
                # If slaves is the same as master, use the current connection info
                master_host = self.master.connection_pool.connection_kwargs['host']
                master_port = self.master.connection_pool.connection_kwargs['port']

            # Create a new Redis client for the master
            self.master = redis.Redis(
                host=master_host,
                port=master_port,
                db=self.db,
                password=self.password,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=self.decode_responses,
                **self.kwargs
            )

            # Test the connection
            self.master.ping()
            logger.info(f"Successfully reconnected to master at {master_host}:{master_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to master: {e}")
            return False

    async def areconnect_master(self):
        """
        Async reconnect to the Redis master.

        Returns:
            True if reconnection was successful, False otherwise
        """
        try:
            # Try to get current master info from slaves if possible
            if self.async_slaves is not self.async_master and self.async_slaves is not None:
                try:
                    replication_info = await self.async_slaves.info(section='replication')
                    master_host = replication_info['master_host']
                    master_port = replication_info['master_port']
                    logger.info(f"Async reconnecting to master at {master_host}:{master_port}")
                except Exception as e:
                    # If we can't get info from slaves, use the current master connection info
                    logger.warning(f"Could not get master info from async slaves: {e}")
                    if self.async_master is not None:
                        # Try to get from existing async_master
                        master_host = self.master.connection_pool.connection_kwargs['host']
                        master_port = self.master.connection_pool.connection_kwargs['port']
                    else:
                        # Fall back to sync master
                        master_host = self.master.connection_pool.connection_kwargs['host']
                        master_port = self.master.connection_pool.connection_kwargs['port']
            else:
                # If slaves is the same as master, use the current connection info
                master_host = self.master.connection_pool.connection_kwargs['host']
                master_port = self.master.connection_pool.connection_kwargs['port']

            ssl_enabled = self.kwargs.get('ssl', False)
            master_url = f"rediss://" if ssl_enabled else f"redis://"

            if self.password:
                master_url += f":{self.password}@"
            master_url += f"{master_host}:{master_port}/{self.db}"

            async_kwargs = self.kwargs.copy()
            if ssl_enabled:
                async_kwargs.pop('ssl', None)

            self.async_master = aioredis.from_url(
                master_url,
                decode_responses=self.decode_responses,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                **async_kwargs
            )

            await self.async_master.ping()
            logger.info(f"Successfully reconnected to async master at {master_host}:{master_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to async master: {e}")
            return False

    @staticmethod
    def reconnect_on_error(max_retries=3, retry_delay=1):
        """
        Decorator for Redis methods to handle connection errors by reconnecting.

        Args:
            max_retries: Maximum number of reconnection attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return func(self, *args, **kwargs)
                    except (ConnectionError, TimeoutError) as e:
                        retries += 1
                        if retries >= max_retries:
                            logger.error(f"Failed to execute {func.__name__} after {max_retries} retries: {e}")
                            raise

                        logger.warning(f"Connection error in {func.__name__}, reconnecting (attempt {retries}/{max_retries}): {e}")
                        self.reconnect_master()
                        time.sleep(retry_delay)
            return wrapper
        return decorator

    @staticmethod
    def areconnect_on_error(max_retries=3, retry_delay=1):
        """
        Async decorator for Redis methods to handle connection errors by reconnecting.

        Args:
            max_retries: Maximum number of reconnection attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Decorated async function
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return await func(self, *args, **kwargs)
                    except (ConnectionError, TimeoutError) as e:
                        retries += 1
                        if retries >= max_retries:
                            logger.error(f"Failed to execute {func.__name__} after {max_retries} retries: {e}")
                            raise

                        logger.warning(f"Connection error in {func.__name__}, reconnecting (attempt {retries}/{max_retries}): {e}")
                        await self.areconnect_master()
                        await asyncio.sleep(retry_delay)
            return wrapper
        return decorator

    async def aclose(self):
        """
        Close all async Redis connections properly.
        Should be called when finished with the client.
        """
        try:
            if hasattr(self, 'async_master') and self.async_master:
                await self.async_master.aclose()
            if (hasattr(self, 'async_slaves') and
                self.async_slaves and
                self.async_slaves is not self.async_master):
                await self.async_slaves.aclose()
        except Exception as e:
            logger.error(f"Error closing async Redis connections: {e}")

    async def __aenter__(self):
        """
        Async context manager entry.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        Ensures connections are closed properly.
        """
        await self.aclose()

    def get(self, key: str, ex: Optional[int] = None, px: Optional[int] = None, exat: Optional[int] = None, pxat: Optional[int] = None, persist: bool = False, use_master: bool = False) -> Any:
        """
        Get value by key.

        Args:
            key: Redis key
            ex: Expiry time in seconds
            px: Expiry time in milliseconds
            exat: Absolute expiry time in seconds since epoch
            pxat: Absolute expiry time in milliseconds since epoch
            persist: Whether to persist the key
            use_master: Whether to use master for read operation

        Returns:
            Value stored in Redis
        """
        if ex or px or exat or pxat or persist:
            client = self._get_client(use_master=True)
            return client.getex(key, ex=ex, px=px, exat=exat, pxat=pxat, persist=persist)
        else:
            client = self._get_client(use_master=use_master)
            return client.get(key)

    async def aget(self, key: str, ex: Optional[int] = None, px: Optional[int] = None, exat: Optional[int] = None, pxat: Optional[int] = None, persist: bool = False, use_master: bool = False) -> Any:
        """
        Async get value by key.

        Args:
            key: Redis key
            ex: Expiry time in seconds
            px: Expiry time in milliseconds
            exat: Absolute expiry time in seconds since epoch
            pxat: Absolute expiry time in milliseconds since epoch
            persist: Whether to persist the key
            use_master: Whether to use master for read operation

        Returns:
            Value stored in Redis
        """
        if ex or px or exat or pxat or persist:
            client = await self._get_async_client(use_master=True)
            return await client.getex(key, ex=ex, px=px, exat=exat, pxat=pxat, persist=persist)
        else:
            client = await self._get_async_client(use_master=use_master)
            return await client.get(key)

    @reconnect_on_error()
    def set(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """
        Set value by key.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiry time in seconds
            nx: Only set the key if it does not already exist
            xx: Only set the key if it already exists

        Returns:
            True if successful
        """
        return self.master.set(key, value, ex=ex, nx=nx, xx=xx)

    @areconnect_on_error()
    async def aset(self, key: str, value: Any, ex: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """
        Async set value by key.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiry time in seconds
            nx: Only set the key if it does not already exist
            xx: Only set the key if it already exists

        Returns:
            True if successful
        """
        if self.async_master is None:
            await self.init_async()
        return await self.async_master.set(key, value, ex=ex, nx=nx, xx=xx)

    @reconnect_on_error()
    def ping(self) -> bool:
        """
        Ping the Redis server to test connectivity.

        Sends a PING command to the Redis server and returns True if the server
        responds with "PONG".
        """
        return self.master.ping()

    @areconnect_on_error()
    async def aping(self) -> bool:
        """
        Ping the Redis server to test connectivity.

        Sends a PING command to the Redis server and returns True if the server
        responds with "PONG".
        """
        if self.async_master is None:
            await self.init_async()
        return self.async_master.ping()

#TODO: in the future, add this methods into the class
def add_redis_methods(cls):
    """Add basic methods to Redis class"""
    for method_name in ['mget', 'hget', 'hgetall', 'lrange', 'smembers', 'exists', 'ttl', 'keys', 'info']:
        setattr(cls, method_name, cls._create_read_method(method_name))
        setattr(cls, f'a{method_name}', cls._create_async_read_method(method_name))

    for method_name in ['mset', 'hset', 'lpush', 'rpush', 'lpop', 'rpop', 'sadd', 'delete', 'expire', 'incr', 'decr']:
        setattr(cls, method_name, cls._create_write_method(method_name))
        setattr(cls, f'a{method_name}', cls._create_async_write_method(method_name))
    return cls

add_redis_methods(MasterSlavesRedis)
