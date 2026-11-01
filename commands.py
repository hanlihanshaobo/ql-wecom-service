"""兼容旧的 `import commands` 用法；实现已迁移到 jbot.commands。"""

from jbot import commands as _commands
from jbot.commands import *  # noqa: F401,F403

# 一并导出下划线开头的辅助函数，避免旧代码 from commands import _list_deps 失效
globals().update(
    {name: value for name, value in vars(_commands).items() if not name.startswith("__")}
)
