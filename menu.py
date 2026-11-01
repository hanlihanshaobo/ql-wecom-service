"""兼容旧的 `import menu` 用法；实现已迁移到 jbot.menu。"""

from jbot import menu as _menu
from jbot.menu import *  # noqa: F401,F403

globals().update(
    {name: value for name, value in vars(_menu).items() if not name.startswith("__")}
)
