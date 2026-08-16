"""
企业微信应用自定义菜单
- 启动时自动创建/更新菜单
- 处理用户点击菜单按钮的事件
"""

import logging
import httpx

from commands import (
    list_tasks, list_envs, list_subscriptions, list_scripts,
    system_info, help_text, _list_deps, _list_configs, run_custom_script,
)
from settings import settings

logger = logging.getLogger("wecom")

# ============================================================
# 菜单定义（最多 3 个一级菜单，每个最多 5 个子按钮）
# ============================================================

MENU = {
    "button": [
        {
            "name": "常用查询",
            "sub_button": [
                {"type": "click", "name": "任务列表", "key": "ql_task_list"},
                {"type": "click", "name": "变量列表", "key": "ql_env_list"},
                {"type": "click", "name": "订阅列表", "key": "ql_sub_list"},
                {"type": "click", "name": "脚本列表", "key": "ql_script_list"},
                {"type": "click", "name": "系统信息", "key": "ql_system_info"},
            ],
        },
        {
            "name": "操作中心",
            "sub_button": [
                {"type": "click", "name": "任务操作", "key": "ql_task_ops"},
                {"type": "click", "name": "订阅操作", "key": "ql_sub_ops"},
                {"type": "click", "name": "脚本操作", "key": "ql_script_ops"},
                {"type": "click", "name": "依赖操作", "key": "ql_dep_ops"},
                {"type": "click", "name": "系统操作", "key": "ql_sys_ops"},
            ],
        },
        {
            "name": "更多设置",
            "sub_button": [
                {"type": "click", "name": "设置变量", "key": "ql_env_set"},
                {"type": "click", "name": "发送通知", "key": "ql_notify"},
                {"type": "click", "name": "查看配置", "key": "ql_config_list"},
                {"type": "click", "name": settings.bot.custom_script_button_name, "key": "ql_run_custom"},
                {"type": "click", "name": "使用帮助", "key": "ql_help"},
            ],
        },
    ]
}


# ============================================================
# 菜单创建
# ============================================================

def create_menu(corp_id: str, agent_id: str, secret: str) -> bool:
    """创建/更新企业微信应用菜单（幂等，每次启动时调用）"""
    token = _fetch_token(corp_id, secret)
    if not token:
        logger.error("无法获取access_token，菜单创建失败")
        return False

    url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/create?access_token={token}&agentid={agent_id}"
    try:
        resp = httpx.post(url, json=MENU, timeout=10)
        data = resp.json()
        if data.get("errcode") == 0:
            logger.info("✅ 应用菜单创建成功")
            return True
        else:
            logger.error(f"菜单创建失败: {data}")
            return False
    except Exception as e:
        logger.error(f"菜单创建异常: {e}")
        return False


def _fetch_token(corp_id: str, secret: str) -> str:
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {"corpid": corp_id, "corpsecret": secret}
    try:
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()
        return data.get("access_token", "")
    except Exception as e:
        logger.error(f"获取token失败: {e}")
        return ""


# ============================================================
# 菜单点击事件处理
# ============================================================

def handle_menu_click(event_key: str, ql_client) -> str | None:
    """根据 EventKey 返回对应的回复文本，无匹配时返回 None"""
    handlers = {
        # 常用查询 —— 直接返回数据
        "ql_task_list":    lambda: list_tasks(ql_client),
        "ql_env_list":     lambda: list_envs("", ql_client),
        "ql_sub_list":     lambda: list_subscriptions(ql_client, ""),
        "ql_script_list":  lambda: list_scripts("", ql_client),
        "ql_system_info":  lambda: system_info(ql_client),

        # 操作中心 —— 列表 + 全部操作提示
        "ql_task_ops":   lambda: _task_ops(ql_client),
        "ql_sub_ops":    lambda: _sub_ops(ql_client),
        "ql_script_ops": lambda: _script_ops(ql_client),
        "ql_dep_ops":    lambda: _dep_ops(ql_client),
        "ql_sys_ops":    lambda: _sys_ops(ql_client),

        # 更多设置 —— 给出格式提示
        "ql_env_set": lambda: (
            "➕ 设置变量格式：\n设变量 <名称>=<值> [备注]\n\n"
            "示例：设变量 MY_KEY=abc123 这是一个测试变量"
        ),
        "ql_notify": lambda: _notify_hint(),
        "ql_config_list": lambda: _config_hint(ql_client),
        "ql_run_custom": lambda: run_custom_script(ql_client),
        "ql_help": lambda: help_text(),
    }

    handler = handlers.get(event_key)
    return handler() if handler else None


def _task_ops(ql_client) -> str:
    """任务列表 + 全部操作提示（合并原执行/停止/日志/状态/禁用/启用/删除多个按钮）"""
    tasks = list_tasks(ql_client)
    return (
        f"{tasks}\n\n"
        f"💡 回复指令操作（序号或任务名）：\n"
        f"  执行 <序号>       运行任务\n"
        f"  停止 <序号>       停止任务\n"
        f"  日志 <序号>       查看日志\n"
        f"  状态 <序号>       查看状态\n"
        f"  禁用任务 <序号>   禁用任务\n"
        f"  启用任务 <序号>   启用任务\n"
        f"  删除任务 <序号>   删除任务"
    )


def _sub_ops(ql_client) -> str:
    """订阅列表 + 操作提示"""
    subs = list_subscriptions(ql_client, "")
    return (
        f"{subs}\n\n"
        f"💡 回复指令操作（订阅名）：\n"
        f"  运行订阅 <名称>     运行订阅\n"
        f"  停止订阅 <名称>     停止订阅\n"
        f"  禁用订阅 <名称>     禁用订阅\n"
        f"  启用订阅 <名称>     启用订阅\n"
        f"  订阅日志 <名称>     查看订阅日志"
    )


def _script_ops(ql_client) -> str:
    """脚本列表 + 操作提示"""
    scripts = list_scripts("", ql_client)
    return (
        f"{scripts}\n\n"
        f"💡 回复指令操作（文件名 [路径]）：\n"
        f"  脚本详情 <文件名> [路径]       查看详情\n"
        f"  运行脚本 <文件名> [路径]       运行脚本\n"
        f"  停止脚本 <文件名> [路径]       停止脚本\n"
        f"  删除脚本 <文件名> [路径]       删除脚本\n"
        f"  重命名脚本 <原名> <新名> [路径]  重命名"
    )


def _dep_ops(ql_client) -> str:
    """依赖列表 + 操作提示"""
    deps = _list_deps(ql_client)
    return (
        f"{deps}\n\n"
        f"💡 回复指令操作（依赖ID）：\n"
        f"  依赖详情 <ID>                  查看详情\n"
        f"  安装依赖 <名称> <类型> [备注]    安装依赖\n"
        f"  删依赖 <ID>                    删除依赖\n"
        f"  重装依赖 <ID>                  重装依赖\n"
        f"  （类型: 0=NodeJs 1=Python3 2=Linux）"
    )


def _sys_ops(ql_client) -> str:
    """系统信息 + 操作提示"""
    info = system_info(ql_client)
    return (
        f"{info}\n\n"
        f"💡 回复指令：\n"
        f"  系统配置          查看系统配置\n"
        f"  系统日志          查看系统日志\n"
        f"  清系统日志        清空系统日志\n"
        f"  检查更新          检查更新\n"
        f"  更新系统          更新系统\n"
        f"  重载系统          重载系统\n"
        f"  导出数据          导出数据\n"
        f"  通知 <标题>=<内容>  发送通知"
    )


def _notify_hint() -> str:
    """发送通知格式提示"""
    return (
        "📢 发送通知格式：\n"
        "通知 <标题>=<内容>\n\n"
        "示例：通知 打卡提醒=记得打卡哦"
    )


def _config_hint(ql_client) -> str:
    """配置文件列表 + 查看提示"""
    configs = _list_configs(ql_client)
    return f"{configs}\n\n💡 查看配置内容：\n查看配置 <路径>"
