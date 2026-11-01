"""企业微信智能机器人模板卡片菜单。"""

from __future__ import annotations

import uuid

# key -> (按钮文案, 实际执行的青龙指令, 结果附加提示)
MENU_ACTIONS: dict[str, tuple[str, str, str]] = {
    "menu:tasks": ("任务列表", "任务", "💡 回复「执行 1」「日志 1」「停止 1」操作任务"),
    "menu:running": ("运行中任务", "运行中任务", ""),
    "menu:envs": ("变量列表", "变量", "💡 回复「查看变量 1」「删变量 1」操作变量"),
    "menu:subs": ("订阅列表", "订阅", "💡 回复「运行订阅 名称」运行订阅"),
    "menu:scripts": ("脚本列表", "脚本", "💡 回复「运行脚本 文件名」运行脚本"),
    "menu:system": ("系统信息", "系统", "💡 回复「系统配置」「系统日志」查看更多"),
    "menu:task_ops": (
        "任务操作",
        "任务",
        "💡 执行 <序号> / 停止 <序号> / 日志 <序号> / 状态 <序号> / 禁用任务 <序号>",
    ),
    "menu:sub_ops": (
        "订阅操作",
        "订阅",
        "💡 运行订阅 <名称> / 停止订阅 <名称> / 订阅日志 <名称>",
    ),
    "menu:script_ops": (
        "脚本操作",
        "脚本",
        "💡 运行脚本 <文件名> / 停止脚本 <文件名> / 脚本详情 <文件名>",
    ),
    "menu:dep_ops": (
        "依赖管理",
        "依赖",
        "💡 安装依赖 <名称> <类型> / 重装依赖 <ID> / 删依赖 <ID>",
    ),
    "menu:log_ops": (
        "日志管理",
        "日志列表",
        "💡 日志详情 <文件名> / 删除日志 <文件名>",
    ),
    "menu:help": ("使用帮助", "帮助", ""),
}


def _task_id(prefix: str = "menu") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _button(text: str, key: str, style: int = 1) -> dict:
    return {"text": text, "style": style, "key": key}


def menu_card(desc: str = "点击按钮查询，或直接发送文字指令") -> dict:
    """主菜单卡片。"""
    return {
        "card_type": "button_interaction",
        "main_title": {"title": "青龙面板", "desc": desc},
        "button_list": [
            _button("任务列表", "menu:tasks"),
            _button("运行中", "menu:running"),
            _button("变量", "menu:envs"),
            _button("订阅", "menu:subs"),
            _button("脚本", "menu:scripts"),
            _button("更多", "menu:more", style=2),
        ],
        "task_id": _task_id("menu"),
    }


def more_card(desc: str = "更多青龙操作") -> dict:
    """更多操作卡片。"""
    return {
        "card_type": "button_interaction",
        "main_title": {"title": "更多操作", "desc": desc},
        "button_list": [
            _button("系统信息", "menu:system"),
            _button("任务操作", "menu:task_ops"),
            _button("订阅操作", "menu:sub_ops"),
            _button("脚本操作", "menu:script_ops"),
            _button("日志管理", "menu:log_ops"),
            _button("返回", "menu:home", style=2),
        ],
        "task_id": _task_id("menu"),
    }


def help_card(desc: str = "青龙面板操作面板") -> dict:
    """帮助入口卡片。"""
    return menu_card(desc)
