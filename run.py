import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from jbot.bot_ws import WeComBot  # noqa: E402
from jbot.config import settings  # noqa: E402


if __name__ == "__main__":
    if not settings.wecom_bot.configured:
        raise SystemExit(
            "未配置企业微信智能机器人 BotID / Secret，请编辑 "
            f"{settings.config_file or 'config/bot.json'} 的 wecom_bot 节点"
        )
    asyncio.run(WeComBot(settings).run())
