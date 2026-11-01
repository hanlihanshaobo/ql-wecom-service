"""青龙面板机器人插件入口：python3 -m jbot。

通过企业微信智能机器人「API 模式 → 长连接」接收消息，
不需要公网回调地址、端口映射或反向代理。
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from . import __version__


def _setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    # 青龙面板会把 stdout/stderr 重定向到 log/bot/nohup.log；
    # 再额外写一份独立日志，方便在面板日志页查看。
    log_dir = os.getenv("QL_LOG_DIR", "").strip()
    if not log_dir and os.getenv("QL_DATA_DIR", "").strip():
        log_dir = str(Path(os.getenv("QL_DATA_DIR", "").strip()) / "log")
    if log_dir:
        try:
            bot_log_dir = Path(log_dir) / "bot"
            bot_log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                bot_log_dir / "wecom.log", encoding="utf-8"
            )
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            handlers.append(file_handler)
        except OSError:
            pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def main() -> int:
    _setup_logging()
    logger = logging.getLogger("wecom")
    logger.info("启动青龙企业微信智能机器人插件 v%s", __version__)

    from .config import settings

    if not settings.wecom_bot.configured:
        logger.error(
            "未配置企业微信智能机器人 BotID / Secret，"
            "请编辑 %s 的 wecom_bot 节点",
            settings.config_file or "config/bot.json",
        )
        return 1

    if not (settings.ql.client_id and settings.ql.client_secret):
        logger.warning(
            "青龙 OpenAPI 客户端未配置：请在 %s 的 qinglong 节点填写 "
            "client_id / client_secret（青龙 系统设置 → 应用设置）",
            settings.config_file or "config/bot.json",
        )

    from .bot_ws import WeComBot

    async def run() -> None:
        bot = WeComBot(settings)
        try:
            await bot.run()
        finally:
            await bot.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("收到退出信号，机器人已停止")
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.exception("机器人运行失败: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
