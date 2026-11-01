"""兼容旧配置导入；实现已迁移到 jbot.config。"""

from jbot.config import (  # noqa: F401
    BotConfig,
    CallbackConfig,
    QLConfig,
    Settings,
    WecomConfig,
    settings,
)

__all__ = [
    "WecomConfig",
    "CallbackConfig",
    "QLConfig",
    "BotConfig",
    "Settings",
    "settings",
]
