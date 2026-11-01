"""兼容旧的 `from ql_client import QLClient` 用法。"""

from jbot.ql_client import QLClient  # noqa: F401

__all__ = ["QLClient"]
