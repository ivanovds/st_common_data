from __future__ import annotations
import re
from typing import NamedTuple, Optional, Sequence, Union, Mapping, Any, cast

from urllib.parse import parse_qsl
from urllib.parse import unquote


__all__ = ("parse_url", "URL",)


def to_list(x: Any, default: list[Any] | None = None) -> list[Any]:
    if x is None:
        return default  # type: ignore
    elif isinstance(x, list):
        return x
    else:
        return list(x)


class URL(NamedTuple):
    drivername: str
    username: Optional[str]
    password: Optional[str]
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]

    @classmethod
    def create(
        cls,
        drivername: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        query: Mapping[str, Union[Sequence[str], str]] = {},
    ) -> URL:

        return cls(
            cls._assert_str(drivername, "drivername"),
            cls._assert_none_str(username, "username"),
            password,
            cls._assert_none_str(host, "host"),
            cls._assert_port(port),
            cls._assert_none_str(database, "database"),
        )

    @classmethod
    def _assert_port(cls, port: Optional[int]) -> Optional[int]:
        if port is None:
            return None
        try:
            return int(port)
        except TypeError:
            raise TypeError("Port argument must be an integer or None")

    @classmethod
    def _assert_str(cls, v: str, paramname: str) -> str:
        if not isinstance(v, str):
            raise TypeError("%s must be a string" % paramname)
        return v

    @classmethod
    def _assert_none_str(
        cls, v: Optional[str], paramname: str
    ) -> Optional[str]:
        if v is None:
            return v

        return cls._assert_str(v, paramname)

    def set(
        self,
        drivername: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        query: Optional[Mapping[str, Union[Sequence[str], str]]] = None,
    ) -> URL:
        kw: Dict[str, Any] = {}
        if drivername is not None:
            kw["drivername"] = drivername
        if username is not None:
            kw["username"] = username
        if password is not None:
            kw["password"] = password
        if host is not None:
            kw["host"] = host
        if port is not None:
            kw["port"] = port
        if database is not None:
            kw["database"] = database

        return self._assert_replace(**kw)

    def _assert_replace(self, **kw: Any) -> URL:
        """argument checks before calling _replace()"""

        if "drivername" in kw:
            self._assert_str(kw["drivername"], "drivername")
        for name in "username", "host", "database":
            if name in kw:
                self._assert_none_str(kw[name], name)
        if "port" in kw:
            self._assert_port(kw["port"])

        return self._replace(**kw)

    def __copy__(self) -> URL:
        return self.__class__.create(
            self.drivername,
            self.username,
            self.password,
            self.host,
            self.port,
            self.database,
        )

    def __deepcopy__(self, memo: Any) -> URL:
        return self.__copy__()

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, URL)
            and self.drivername == other.drivername
            and self.username == other.username
            and self.password == other.password
            and self.host == other.host
            and self.database == other.database
            and self.port == other.port
        )

    def __ne__(self, other: Any) -> bool:
        return not self == other

    def get_backend_name(self) -> str:
        if "+" not in self.drivername:
            return self.drivername
        else:
            return self.drivername.split("+")[0]


def parse_url(name: str) -> URL:
    pattern = re.compile(
        r"""
            (?P<name>[\w\+]+)://
            (?:
                (?P<username>[^:/]*)
                (?::(?P<password>[^@]*))?
            @)?
            (?:
                (?:
                    \[(?P<ipv6host>[^/\?]+)\] |
                    (?P<ipv4host>[^/:\?]+)
                )?
                (?::(?P<port>[^/\?]*))?
            )?
            (?:/(?P<database>[^\?]*))?
            (?:\?(?P<query>.*))?
            """,
        re.X,
    )

    m = pattern.match(name)
    if m is not None:
        components = m.groupdict()
        query: dict[str, str | list[str]] | None
        if components["query"] is not None:
            query = {}

            for key, value in parse_qsl(components["query"]):
                if key in query:
                    query[key] = util.to_list(query[key])
                    cast("list[str]", query[key]).append(value)
                else:
                    query[key] = value
        else:
            query = None
        components["query"] = query

        for comp in "username", "password", "database":
            if components[comp] is not None:
                components[comp] = unquote(components[comp])

        ipv4host = components.pop("ipv4host")
        ipv6host = components.pop("ipv6host")
        components["host"] = ipv4host or ipv6host
        name = components.pop("name")

        if components["port"]:
            components["port"] = int(components["port"])

        return URL.create(name, **components)  # type: ignore

    else:
        raise ValueError(
            "Could not parse DB URL from given URL string"
        )
