"""
企业微信应用自定义菜单
- 启动时自动创建/更新菜单
- 处理用户点击菜单按钮的事件
"""

import logging
import httpx

from commands import (
    list_tasks, list_envs, list_subscriptions, list_scripts,
    system_info, help_text, _list_deps, _list_configs, _list_logs,
    run_custom_script, list_running_tasks,
)
from settings import settings

logger = logging.getLogger("wecom")

# ============================================================
# 菜单定义（最多 3 个一级菜单，每个最多 5 个子按钮）
# ============================================================

MENU = {
    "button": [
        {
            "name": "任务",
            "sub_button": [
                {"type": "click", "name": "任务操作", "key": "ql_task_ops"},
                {"type": "click", "name": "运行中任务", "key": "ql_running_tasks"},
            ],
        },
        {
            "name": "资源",
            "sub_button": [
                {"type": "click", "name": "订阅操作", "key": "ql_sub_ops"},
                {"type": "click", "name": "脚本操作", "key": "ql_script_ops"},
                {"type": "click", "name": "依赖操作", "key": "ql_dep_ops"},
                {"type": "click", "name": "变量操作", "key": "ql_env_ops"},
                {"type": "click", "name": settings.bot.custom_script_button_name, "key": "ql_run_custom"},
            ],
        },
        {
            "name": "系统",
            "sub_button": [
                {"type": "click", "name": "系统操作", "key": "ql_sys_ops"},
                {"type": "click", "name": "日志管理", "key": "ql_log_ops"},
                {"type": "click", "name": "命令操作", "key": "ql_cmd_ops"},
                {"type": "click", "name": "查看配置", "key": "ql_config_list"},
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
        # 任务 —— 任务操作 / 运行中任务
        "ql_task_ops":       lambda: _task_ops(ql_client),
        "ql_running_tasks":  lambda: list_running_tasks(ql_client),

        # 资源 —— 各资源操作
        "ql_sub_ops":    lambda: _sub_ops(ql_client),
        "ql_script_ops": lambda: _script_ops(ql_client),
        "ql_dep_ops":    lambda: _dep_ops(ql_client),
        "ql_env_ops":    lambda: _env_ops(ql_client),
        "ql_run_custom": lambda: run_custom_script(ql_client),

        # 系统 —— 系统操作 / 日志管理 / 命令操作 / 配置 / 帮助
        "ql_sys_ops":     lambda: _sys_ops(ql_client),
        "ql_log_ops":     lambda: _log_ops(ql_client),
        "ql_cmd_ops":     lambda: _cmd_ops(ql_client),
        "ql_config_list": lambda: _config_hint(ql_client),
        "ql_help":        lambda: help_text(),
    }

    handler = handlers.get(event_key)
    return handler() if handler else None


def _task_ops(ql_client) -> str:
    """任务列表 + 全部操作提示（合并原执行/停止/日志/状态/禁用/启用/删除多个按钮）"""
    tasks = list_tasks(ql_client)
    return (
        f"{tasks}\n\n"
        f"💡 回复指令操作（序号或任务名）：\n"
        f"  执行 <序号>         运行任务\n"
        f"  停止 <序号>         停止任务\n"
        f"  日志 <序号>         查看日志\n"
        f"  状态 <序号>         查看状态\n"
        f"  禁用任务 <序号>     禁用任务\n"
        f"  启用任务 <序号>     启用任务\n"
        f"  删除任务 <序号>     删除任务\n"
        f"  修改定时 <序号> <cron>  修改任务定时\n"
        f"  运行中任务           查看运行中的任务"
    )


def _sub_ops(ql_client) -> str:
    """订阅列表 + 操作提示"""
    subs = list_subscriptions(ql_client, "")
    return (
        f"{subs}\n\n"
        f"💡 回复指令操作（订阅名）：\n"
        f"  创建订阅 <仓库URL> [别名]  添加订阅源\n"
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


def _env_ops(ql_client) -> str:
    """环境变量列表 + 全部操作提示（合并原设置变量/删除/禁用/启用等）"""
    envs = list_envs("", ql_client)
    return (
        f"{envs}\n\n"
        f"💡 回复指令操作（变量ID或名称）：\n"
        f"  设变量 <名称>=<值> [备注]    创建/更新变量\n"
        f"  查看变量 <ID>               查看变量详情\n"
        f"  删变量 <ID>                 删除变量\n"
        f"  禁用变量 <ID>               禁用变量\n"
        f"  启用变量 <ID>               启用变量"
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


def _cmd_ops(ql_client) -> str:
    """命令执行提示（运行/停止命令）"""
    return (
        "⚙ 命令管理：\n"
        "  运行命令 <shell命令>   执行任意命令\n"
        "  停止命令 <pid>         停止命令\n\n"
        "示例：\n"
        "  运行命令 ql repo https://github.com/user/repo\n"
        "  停止命令 12345"
    )


def _config_hint(ql_client) -> str:
    """配置文件列表 + 查看提示"""
    configs = _list_configs(ql_client)
    return f"{configs}\n\n💡 查看配置内容：\n查看配置 <路径>"


def _log_ops(ql_client) -> str:
    """日志列表 + 全部操作提示"""
    logs = _list_logs(ql_client)
    return (
        f"{logs}\n\n"
        f"💡 回复指令操作（日志文件名）：\n"
        f"  日志详情 <文件名>   查看日志内容\n"
        f"  删除日志 <文件名>   删除日志"
    )
