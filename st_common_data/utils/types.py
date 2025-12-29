from typing import Union


__all__ = ("JsonType",)


JsonType = Union[str, int, float, bool, None, dict[str, "JsonType"], list["JsonType"]]
