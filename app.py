"""旧版自建应用回调入口（可选，保留兼容）。

默认的青龙机器人插件和 Docker 镜像都使用 jbot.bot_ws 的智能机器人长连接，
不再使用这个 FastAPI 回调服务。
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from jbot.server import app, create_app  # noqa: E402,F401

__all__ = ["app", "create_app"]
