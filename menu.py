"""
企业微信应用自定义菜单
- 启动时自动创建/更新菜单
- 处理用户点击菜单按钮的事件
"""

import logging
import httpx

from commands import (
    list_tasks, list_envs, list_subscriptions, list_scripts,
    system_info, help_text, _list_deps, run_custom_script,
)

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
            "name": "任务操作",
            "sub_button": [
                {"type": "click", "name": "执行任务", "key": "ql_task_run"},
                {"type": "click", "name": "停止任务", "key": "ql_task_stop"},
                {"type": "click", "name": "查看日志", "key": "ql_task_log"},
                {"type": "click", "name": "查看状态", "key": "ql_task_status"},
                {"type": "click", "name": "禁用/启用", "key": "ql_task_toggle"},
            ],
        },
        {
            "name": "更多设置",
            "sub_button": [
                {"type": "click", "name": "设置变量", "key": "ql_env_set"},
                {"type": "click", "name": "执行自定义脚本", "key": "ql_run_custom"},
                {"type": "click", "name": "删除任务", "key": "ql_task_delete"},
                {"type": "click", "name": "依赖列表", "key": "ql_dep_list"},
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

        # 任务操作 —— 先列出任务，再引导用户输入命令
        "ql_task_run":    lambda: _prompt(ql_client, "执行"),
        "ql_task_stop":   lambda: _prompt(ql_client, "停止"),
        "ql_task_log":    lambda: _prompt(ql_client, "日志"),
        "ql_task_status": lambda: _prompt(ql_client, "状态"),
        "ql_task_toggle": lambda: _prompt(ql_client, "禁用任务/启用任务"),
        "ql_task_delete": lambda: _prompt(ql_client, "删除任务"),

        # 更多 —— 给出格式提示
        "ql_env_set": lambda: (
            "➕ 设置变量格式：\n设变量 <名称>=<值> [备注]\n\n"
            "示例：设变量 MY_KEY=abc123 这是一个测试变量"
        ),
        "ql_run_custom": lambda: run_custom_script(ql_client),
        "ql_dep_list": lambda: _list_deps(ql_client),
        "ql_help": lambda: help_text(),
    }

    handler = handlers.get(event_key)
    return handler() if handler else None


def _prompt(ql_client, cmd: str) -> str:
    """返回带序号的任务列表 + 序号操作提示"""
    tasks = list_tasks(ql_client)
    return f"{tasks}\n\n💡 回复序号，如：{cmd} 1"
