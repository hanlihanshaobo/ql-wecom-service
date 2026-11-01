"""独立部署入口（兼容旧用法）。

实际实现位于 jbot.server，青龙机器人插件与独立服务共用同一套代码。
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from jbot.server import app, create_app  # noqa: E402,F401

__all__ = ["app", "create_app"]
