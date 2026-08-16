import logging
from ql_client import QLClient
from settings import settings

logger = logging.getLogger("wecom")


def process_command(cmd: str, ql: QLClient) -> str:
    parts = cmd.strip().split(None, 1)
    action = parts[0] if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    # ---- 任务 ----
    if action in ("任务", "任务列表", "tasks", "list"):
        return list_tasks(ql)
    if action in ("执行", "运行", "run"):
        if not arg:
            return "请指定任务名或序号，例如：执行 签到 或 执行 1"
        return _run_task(arg, ql)
    if action in ("停止", "stop"):
        if not arg:
            return "请指定任务名或序号，例如：停止 签到 或 停止 1"
        return _stop_task(arg, ql)
    if action in ("日志", "log"):
        if not arg:
            return "请指定任务名或序号，例如：日志 签到 或 日志 1"
        return _get_logs(arg, ql)
    if action in ("状态", "status"):
        return _status(arg, ql) if arg else "请指定任务名或序号，例如：状态 1"
    if action in ("禁用任务", "disable_task"):
        if not arg:
            return "请指定任务名或序号，例如：禁用任务 1"
        return _disable_task(arg, ql)
    if action in ("启用任务", "enable_task"):
        if not arg:
            return "请指定任务名或序号，例如：启用任务 1"
        return _enable_task(arg, ql)
    if action in ("删除任务", "delete_task"):
        if not arg:
            return "请指定任务名或序号，例如：删除任务 1"
        return _delete_task(arg, ql)
    if action in ("运行中任务", "running"):
        return list_running_tasks(ql)
    if action in ("修改定时", "change_cron"):
        if not arg:
            return "格式：修改定时 <任务名/序号> <cron表达式>\n示例：修改定时 签到 0 8 * * *"
        return _change_schedule(arg, ql)

    # ---- 环境变量 ----
    if action in ("变量", "变量列表", "envs"):
        return list_envs(arg, ql)
    if action in ("设变量", "set_env"):
        if not arg:
            return "格式：设变量 <名称>=<值> [备注...]"
        return _set_env(arg, ql)
    if action in ("查看变量", "get_env"):
        if not arg:
            return "请指定环境变量ID，例如：查看变量 1"
        return _get_env(arg, ql)
    if action in ("删变量", "del_env"):
        if not arg:
            return "请指定要删除的环境变量ID，例如：删变量 5"
        return _del_env(arg, ql)
    if action in ("禁用变量", "disable_env"):
        if not arg:
            return "请指定要禁用的环境变量ID，例如：禁用变量 5"
        return _disable_env(arg, ql)
    if action in ("启用变量", "enable_env"):
        if not arg:
            return "请指定要启用的环境变量ID，例如：启用变量 5"
        return _enable_env(arg, ql)

    # ---- 订阅 ----
    if action in ("订阅", "订阅列表", "subscriptions"):
        return list_subscriptions(ql, arg)
    if action in ("创建订阅", "add_sub"):
        if not arg:
            return "格式：创建订阅 <仓库URL> [别名]\n示例：创建订阅 https://github.com/user/repo 我的订阅"
        return _add_subscription(arg, ql)
    if action in ("运行订阅", "run_sub"):
        if not arg:
            return "请指定订阅名称，例如：运行订阅 网易云"
        return _run_subscription(arg, ql)
    if action in ("停止订阅", "stop_sub"):
        if not arg:
            return "请指定订阅名称，例如：停止订阅 网易云"
        return _stop_subscription(arg, ql)
    if action in ("禁用订阅", "disable_sub"):
        if not arg:
            return "请指定订阅名称，例如：禁用订阅 网易云"
        return _disable_subscription(arg, ql)
    if action in ("启用订阅", "enable_sub"):
        if not arg:
            return "请指定订阅名称，例如：启用订阅 网易云"
        return _enable_subscription(arg, ql)
    if action in ("订阅日志", "sub_log"):
        if not arg:
            return "请指定订阅名称，例如：订阅日志 网易云"
        return _sub_log(arg, ql)

    # ---- 系统 ----
    if action in ("系统", "system"):
        return system_info(ql)
    if action in ("通知", "notify"):
        if not arg:
            return "格式：通知 <标题>=<内容>"
        return _send_notify(arg, ql)

    # ---- 命令管理 ----
    if action in ("命令", "命令列表", "commands"):
        return _list_commands(ql, arg)
    if action in ("新建命令", "add_cmd"):
        if not arg:
            return "格式：新建命令 <名称> <命令内容>"
        return _add_command(arg, ql)
    if action in ("命令详情", "cmd_detail"):
        if not arg:
            return "请指定命令ID，例如：命令详情 1"
        return _cmd_detail(arg, ql)
    if action in ("运行命令", "run_cmd"):
        if not arg:
            return "请指定命令ID，例如：运行命令 1"
        return _run_command(arg, ql)
    if action in ("删命令", "del_cmd"):
        if not arg:
            return "请指定命令ID，例如：删命令 1"
        return _del_command(arg, ql)

    # ---- 脚本 ----
    if action in ("脚本", "脚本列表", "scripts"):
        return list_scripts(arg, ql)
    if action in ("脚本详情", "script_detail"):
        if not arg:
            return "格式：脚本详情 <文件名> [路径]"
        return _script_detail(arg, ql)
    if action in ("运行脚本", "run_script"):
        if not arg:
            return "格式：运行脚本 <文件名> [路径]"
        return _run_script(arg, ql)
    if action in ("停止脚本", "stop_script"):
        if not arg:
            return "格式：停止脚本 <文件名> [路径]"
        return _stop_script(arg, ql)
    if action in ("删除脚本", "del_script"):
        if not arg:
            return "格式：删除脚本 <文件名> [路径]"
        return _del_script(arg, ql)
    if action in ("重命名脚本", "rename_script"):
        if not arg:
            return "格式：重命名脚本 <原文件名> <新文件名> [路径]"
        return _rename_script(arg, ql)

    # ---- 自定义脚本 ----
    if action in ("自定义脚本", "run_custom"):
        return run_custom_script(ql)

    # ---- 依赖 ----
    if action in ("依赖", "依赖列表", "deps"):
        return _list_deps(ql)
    if action in ("依赖详情", "dep_detail"):
        if not arg:
            return "请指定依赖ID，例如：依赖详情 1"
        return _dep_detail(arg, ql)
    if action in ("安装依赖", "add_dep"):
        if not arg:
            return "格式：安装依赖 <名称> <类型> [备注]\n类型: 0=NodeJs 1=Python3 2=Linux"
        return _add_dep(arg, ql)
    if action in ("删依赖", "del_dep"):
        if not arg:
            return "请指定依赖ID，例如：删依赖 5"
        return _del_dep(arg, ql)
    if action in ("重装依赖", "reinstall_dep"):
        if not arg:
            return "请指定依赖ID，例如：重装依赖 5"
        return _reinstall_dep(arg, ql)

    # ---- 配置 ----
    if action in ("配置", "配置列表", "configs"):
        return _list_configs(ql)
    if action in ("查看配置", "config_detail"):
        if not arg:
            return "请指定配置路径，例如：查看配置 config.sh"
        return _config_detail(arg, ql)

    # ---- 日志管理 ----
    if action in ("日志列表", "log_list"):
        return _list_logs(ql)
    if action in ("日志详情", "log_detail"):
        if not arg:
            return "格式：日志详情 <文件名>"
        return _log_detail(arg, ql)
    if action in ("删除日志", "del_log"):
        if not arg:
            return "格式：删除日志 <文件名>"
        return _del_log(arg, ql)
    if action in ("系统日志", "sys_log"):
        return _system_log(arg, ql)

    # ---- 系统操作 ----
    if action in ("系统配置", "sys_config"):
        return _sys_config(ql)
    if action in ("检查更新", "check_update"):
        return _check_update(ql)
    if action in ("更新系统", "update_system"):
        return _update_system(ql)
    if action in ("重载系统", "reload_system"):
        return _reload_system(ql)
    if action in ("清系统日志", "clear_sys_log"):
        return _clear_sys_log(ql)

    # ---- 导出数据 ----
    if action in ("导出数据", "export_data"):
        return _export_data(ql)

    return help_text()


# ==================== 任务指令 ====================

def _resolve_task_name(name_or_index: str, ql: QLClient) -> str:
    """将数字序号转换为实际任务名，返回 '' 表示序号无效"""
    if not name_or_index:
        return ""
    try:
        idx = int(name_or_index) - 1
        crons = ql.list_crons()
        if 0 <= idx < len(crons):
            return crons[idx].get("name", "")
    except ValueError:
        pass
    return name_or_index  # 不是数字，原样返回任务名


def _resolve_sub_name(name_or_index: str, ql: QLClient) -> str:
    """将数字序号转换为实际订阅名"""
    if not name_or_index:
        return ""
    try:
        idx = int(name_or_index) - 1
        subs = ql.list_subscriptions()
        if 0 <= idx < len(subs):
            return subs[idx].get("name", "")
    except ValueError:
        pass
    return name_or_index


def list_tasks(ql: QLClient) -> str:
    crons = ql.list_crons()
    if not crons:
        return "暂无任务"
    lines = [f"📋 任务列表（共 {len(crons)} 个）："]
    for i, c in enumerate(crons):
        name = c.get("name", "未知")
        is_pinned = c.get("isPinned", 0) or c.get("pinned", False)
        is_disabled = int(c.get("isDisabled", 0)) or int(c.get("status", 1)) == 0
        tag = "⛔" if is_disabled else "✅"
        pin = "📌" if is_pinned else ""
        lines.append(f"{i+1}. {tag}{pin} {name}")
    return "\n".join(lines)


def _run_task(name: str, ql: QLClient) -> str:
    name = _resolve_task_name(name, ql)
    result = ql.run_cron_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已执行任务：{name}"
    return f"❌ 执行失败：{result.get('msg', '未知错误')}"


def _stop_task(name: str, ql: QLClient) -> str:
    name = _resolve_task_name(name, ql)
    result = ql.stop_cron_by_name(name)
    if result.get("code") == 200:
        return f"🛑 已停止任务：{name}"
    return f"❌ 停止失败：{result.get('msg', '未知错误')}"


def _disable_task(name: str, ql: QLClient) -> str:
    name = _resolve_task_name(name, ql)
    result = ql.disable_cron_by_name(name)
    if result.get("code") == 200:
        return f"⛔ 已禁用任务：{name}"
    return f"❌ 禁用失败：{result.get('msg', '未知错误')}"


def _enable_task(name: str, ql: QLClient) -> str:
    name = _resolve_task_name(name, ql)
    result = ql.enable_cron_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已启用任务：{name}"
    return f"❌ 启用失败：{result.get('msg', '未知错误')}"


def _delete_task(name: str, ql: QLClient) -> str:
    name = _resolve_task_name(name, ql)
    cron = ql.get_cron_by_name(name)
    if not cron:
        return f"未找到任务：{name}"
    result = ql.delete_crons([cron["id"]])
    if result.get("code") == 200:
        return f"🗑 已删除任务：{name}"
    return f"❌ 删除失败"


def _get_logs(name: str, ql: QLClient) -> str:
    name = _resolve_task_name(name, ql)
    cron = ql.get_cron_by_name(name)
    if not cron:
        return f"未找到任务：{name}"

    log_files = ql.get_cron_logs(cron["id"])
    if not log_files:
        return f"📂 {name} 暂无日志"

    log_content = ql.get_cron_log_content(cron["id"])
    lines = [f"📂 {name} 最新日志："]
    if log_content:
        content = str(log_content).strip()
        if len(content) > 500:
            content = content[-500:]
        lines.append(content)
    else:
        lines.append("（无日志内容）")

    lines.append(f"\n📑 历史日志文件（共 {len(log_files)} 个）：")
    for f in log_files[:30]:
        filename = f.get("filename", "未知")
        lines.append(f"  · {filename}")
    if len(log_files) > 30:
        lines.append(f"  ... 还有 {len(log_files) - 30} 个")

    return "\n".join(lines)


def _status(name: str, ql: QLClient) -> str:
    if not name:
        return "请指定任务名或序号，例如：状态 签到 或 状态 1"
    name = _resolve_task_name(name, ql)
    cron = ql.get_cron_by_name(name)
    if not cron:
        return f"未找到任务：{name}"
    is_disabled = int(cron.get("isDisabled", 0)) or int(cron.get("status", 1)) == 0
    st = "已禁用" if is_disabled else "已启用"
    lines = [f"📌 {name}"]
    lines.append(f"   状态: {st}")
    if cron.get("schedule"):
        lines.append(f"   定时: {cron['schedule']}")
    if cron.get("command"):
        cmd_text = cron["command"][:80]
        lines.append(f"   命令: {cmd_text}")
    if cron.get("last_execution_time"):
        lines.append(f"   上次执行: {cron['last_execution_time']}")
    return "\n".join(lines)


def list_running_tasks(ql: QLClient) -> str:
    """列出当前正在运行的任务"""
    crons = ql.list_crons()
    running = []
    for c in crons:
        # 兼容不同版本字段：isRunning / is_running / 运行中的 pid
        if c.get("isRunning") or c.get("is_running") or c.get("pid"):
            running.append(c)
    if not running:
        return "🟢 当前没有运行中的任务"
    lines = [f"🏃 运行中任务（{len(running)} 个）："]
    for i, c in enumerate(running):
        name = c.get("name", "未知")
        last = c.get("last_execution_time") or c.get("lastRunningTime") or ""
        lines.append(f"{i+1}. 🏃 {name}")
        if last:
            lines.append(f"     上次执行: {last}")
    lines.append("\n💡 回复 停止 <序号> 可停止任务")
    return "\n".join(lines)


def _change_schedule(arg: str, ql: QLClient) -> str:
    """修改任务定时：修改定时 <任务名/序号> <cron表达式>"""
    parts = arg.split(None, 1)
    if len(parts) < 2:
        return "格式：修改定时 <任务名/序号> <cron表达式>\n示例：修改定时 签到 0 8 * * *"
    name = _resolve_task_name(parts[0], ql)
    schedule = parts[1].strip()
    cron = ql.get_cron_by_name(name)
    if not cron:
        return f"未找到任务：{name}"
    payload = {
        "id": cron["id"],
        "name": cron.get("name", ""),
        "command": cron.get("command", ""),
        "schedule": schedule,
    }
    result = ql.update_cron(payload)
    if result.get("code") == 200:
        return f"✅ 已修改定时：{name} → {schedule}"
    return f"❌ 修改失败：{result.get('msg', '未知错误')}"


# ==================== 变量指令 ====================

def list_envs(search: str, ql: QLClient) -> str:
    envs = ql.get_envs(search_value=search or None)
    if not envs:
        return "暂无环境变量"
    lines = [f"📦 环境变量（共 {len(envs)} 个）："]
    for e in envs:
        eid = e.get("id", "")
        name = e.get("name", "未知")
        value = e.get("value", "")
        status = e.get("status", 1)
        tag = "👁" if status == 1 else "🔒"
        masked = _mask_value(value)
        lines.append(f"{tag} [{eid}] {name} = {masked}")
    return "\n".join(lines)


def _mask_value(value: str) -> str:
    if not value:
        return "(空)"
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-3:]


def _set_env(arg: str, ql: QLClient) -> str:
    if "=" not in arg:
        return "格式：设变量 <名称>=<值> [备注...]"
    name_value, _, remarks = arg.partition(" ")
    if "=" not in name_value:
        return "格式错误，需用 NAME=VALUE 格式"
    name, _, value = name_value.partition("=")
    name = name.strip()
    value = value.strip()
    remarks = remarks.strip() if remarks else ""
    envs = ql.create_env([{"name": name, "value": value, "remarks": remarks}])
    if envs:
        return f"✅ 已创建变量：{name}"
    return f"❌ 创建变量失败：{name}"


def _get_env(arg: str, ql: QLClient) -> str:
    try:
        env_id = int(arg)
    except ValueError:
        return f"无效的ID：{arg}"
    env = ql.get_env_by_id(env_id)
    if not env:
        return f"未找到变量 ID：{env_id}"
    return (
        f"📦 环境变量详情：\n"
        f"  ID: {env.get('id')}\n"
        f"  名称: {env.get('name')}\n"
        f"  值: {env.get('value')}\n"
        f"  备注: {env.get('remarks', '')}\n"
        f"  状态: {'启用' if env.get('status') == 1 else '禁用'}"
    )


def _del_env(arg: str, ql: QLClient) -> str:
    try:
        ids = [int(x.strip()) for x in arg.split(",")]
    except ValueError:
        return f"无效的ID：{arg}"
    if not ids:
        return "请指定至少一个ID"
    result = ql.delete_envs(ids)
    return f"✅ 已删除变量 ID：{ids}" if result.get("code") == 200 else f"❌ 删除失败"


def _disable_env(arg: str, ql: QLClient) -> str:
    try:
        ids = [int(x.strip()) for x in arg.split(",")]
    except ValueError:
        return f"无效的ID：{arg}"
    result = ql.disable_envs(ids)
    return f"🔒 已禁用变量 ID：{ids}" if result.get("code") == 200 else f"❌ 禁用失败"


def _enable_env(arg: str, ql: QLClient) -> str:
    try:
        ids = [int(x.strip()) for x in arg.split(",")]
    except ValueError:
        return f"无效的ID：{arg}"
    result = ql.enable_envs(ids)
    return f"👁 已启用变量 ID：{ids}" if result.get("code") == 200 else f"❌ 启用失败"


# ==================== 订阅指令 ====================

def list_subscriptions(ql: QLClient, search: str) -> str:
    subs = ql.list_subscriptions(search=search or None)
    if not subs:
        return "暂无订阅"
    lines = [f"📡 订阅列表（共 {len(subs)} 个）："]
    for s in subs:
        name = s.get("alias") or s.get("name") or "未知"
        status = s.get("status", -1)
        tag = "✅" if status == 1 else "⛔"
        stype = s.get("type", "")
        lines.append(f"{tag} {name} ({stype})")
    return "\n".join(lines)


def _add_subscription(arg: str, ql: QLClient) -> str:
    """创建订阅：创建订阅 <仓库URL> [别名]"""
    parts = arg.split(None, 1)
    url = parts[0].strip()
    alias = parts[1].strip() if len(parts) > 1 else ""
    if not url.startswith(("http://", "https://", "git@")):
        return (
            "请提供有效的仓库地址，例如：\n"
            "  创建订阅 https://github.com/user/repo\n"
            "  创建订阅 https://github.com/user/repo 我的订阅"
        )
    if not alias:
        alias = url.rstrip("/").split("/")[-1] or "新订阅"
    sub_data = {
        "type": 1,            # 1=公开仓库 2=私有仓库 3=单脚本
        "url": url,
        "schedule_type": 2,   # 1=每分钟 2=每小时 3=每天 4=每周 5=每月
        "alias": alias,
    }
    result = ql.create_subscription(sub_data)
    if result.get("code") == 200:
        return f"✅ 订阅已创建：{alias}\n仓库: {url}\n默认每小时拉取，可在青龙面板中调整"
    return f"❌ 创建失败：{result.get('msg', '未知错误')}"


def _run_subscription(name: str, ql: QLClient) -> str:
    result = ql.run_subscription_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已运行订阅：{name}"
    return f"❌ 运行失败：{result.get('msg', '未知错误')}"


def _stop_subscription(name: str, ql: QLClient) -> str:
    name = _resolve_sub_name(name, ql)
    result = ql.stop_subscription_by_name(name)
    if result.get("code") == 200:
        return f"🛑 已停止订阅：{name}"
    return f"❌ 停止失败：{result.get('msg', '未知错误')}"


def _disable_subscription(name: str, ql: QLClient) -> str:
    name = _resolve_sub_name(name, ql)
    result = ql.disable_subscription_by_name(name)
    if result.get("code") == 200:
        return f"🚫 已禁用订阅：{name}"
    return f"❌ 禁用失败：{result.get('msg', '未知错误')}"


def _enable_subscription(name: str, ql: QLClient) -> str:
    name = _resolve_sub_name(name, ql)
    result = ql.enable_subscription_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已启用订阅：{name}"
    return f"❌ 启用失败：{result.get('msg', '未知错误')}"


def _sub_log(name: str, ql: QLClient) -> str:
    name = _resolve_sub_name(name, ql)
    sub = ql.get_subscription_by_name(name)
    if not sub:
        return f"未找到订阅：{name}"
    logs = ql.get_subscription_logs(sub["id"])
    if not logs:
        return f"暂无订阅日志：{name}"
    lines = [f"📋 订阅日志 [{name}] 最近 {len(logs)} 条："]
    for l in logs:
        ts = l.get("timestamp", "") or l.get("ts", "")
        msg = l.get("message", "") or l.get("content", "") or str(l)
        lines.append(f"  {ts} {msg}")
    return "\n".join(lines)


# ==================== 系统指令 ====================

def system_info(ql: QLClient) -> str:
    info = ql.get_system_info()
    if not info:
        return "获取系统信息失败"
    return (
        f"🖥 青龙面板系统信息：\n"
        f"  版本: {info.get('version', '未知')}\n"
        f"  分支: {info.get('branch', '未知')}\n"
        f"  已初始化: {'是' if info.get('isInitialized') else '否'}"
    )


def _send_notify(arg: str, ql: QLClient) -> str:
    if "=" not in arg:
        return "格式：通知 <标题>=<内容>"
    title, _, content = arg.partition("=")
    title = title.strip()
    content = content.strip()
    if not title or not content:
        return "标题和内容不能为空"
    result = ql.send_notify(title, content)
    if result.get("code") == 200:
        return f"✅ 通知已发送：{title}"
    return "❌ 通知发送失败"


# ==================== 脚本指令 ====================

def list_scripts(path: str, ql: QLClient) -> str:
    scripts = ql.list_scripts(path=path or None)
    if not scripts:
        return "暂无脚本"
    lines = [f"📜 脚本列表（共 {len(scripts)} 个）："]
    for s in scripts[:50]:
        name = s.get("title", s.get("name", "未知"))
        lines.append(f"  · {name}")
    if len(scripts) > 50:
        lines.append(f"  ... 还有 {len(scripts) - 50} 个")
    return "\n".join(lines)


# ==================== 脚本指令补充 ====================

def _script_detail(arg: str, ql: QLClient) -> str:
    parts = arg.rsplit(None, 1)
    filename = parts[0]
    path = parts[1] if len(parts) > 1 else None
    detail = ql.get_script_detail(filename, path)
    if not detail:
        return f"未找到脚本：{filename}"
    lines = [f"📜 {filename}"]
    for k, v in detail.items():
        if isinstance(v, str) and len(v) > 200:
            v = v[:200] + "..."
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _run_script(arg: str, ql: QLClient) -> str:
    parts = arg.rsplit(None, 1)
    filename = parts[0]
    path = parts[1] if len(parts) > 1 else None
    result = ql.run_script(filename, path)
    if result.get("code") == 200:
        return f"✅ 已运行脚本：{filename}"
    return f"❌ 运行失败"


def _stop_script(arg: str, ql: QLClient) -> str:
    parts = arg.rsplit(None, 1)
    filename = parts[0]
    path = parts[1] if len(parts) > 1 else None
    result = ql.stop_script(filename, path)
    if result.get("code") == 200:
        return f"🛑 已停止脚本：{filename}"
    return f"❌ 停止失败"


def _del_script(arg: str, ql: QLClient) -> str:
    parts = arg.rsplit(None, 1)
    filename = parts[0]
    path = parts[1] if len(parts) > 1 else None
    result = ql.delete_script(filename, path)
    if result.get("code") == 200:
        return f"🗑 已删除脚本：{filename}"
    return f"❌ 删除失败"


def _rename_script(arg: str, ql: QLClient) -> str:
    tokens = arg.split()
    if len(tokens) < 2:
        return "格式：重命名脚本 <原文件名> <新文件名> [路径]"
    filename, new_filename = tokens[0], tokens[1]
    path = tokens[2] if len(tokens) > 2 else None
    result = ql.rename_script(filename, new_filename, path)
    if result.get("code") == 200:
        return f"✅ 已重命名：{filename} → {new_filename}"
    return f"❌ 重命名失败"


# ==================== 自定义脚本 ====================

def run_custom_script(ql: QLClient) -> str:
    """运行 .env 中 CUSTOM_SCRIPT_FILENAME 指定的脚本"""
    filename = settings.bot.custom_script_filename
    if not filename:
        return "⚠ 未配置自定义脚本，请在 .env 中设置 CUSTOM_SCRIPT_FILENAME"
    path = settings.bot.custom_script_path or None

    # 先查找脚本是否存在于青龙列表（传入 path 以搜索子目录）
    try:
        scripts = ql.list_scripts(path=path)
    except Exception as e:
        logger.error(f"list_scripts 失败: {e}")
        return f"❌ 获取脚本列表失败：{e}"

    if not scripts:
        loc = path or "根目录"
        logger.info(f"在 {loc} 中未找到任何脚本")
        return f"❌ 在 {loc} 中未找到任何脚本，请检查路径配置"

    target = None
    for s in scripts:
        try:
            s_name = s.get("title", s.get("filename", s.get("name", "")))
            if s_name == filename:
                target = s
                break
        except Exception:
            continue
    if not target:
        loc = path or "根目录"
        found_names = []
        for s in scripts:
            try:
                found_names.append(s.get("title", s.get("filename", s.get("name", "?"))))
            except Exception:
                found_names.append("?")
        logger.info(f"脚本未找到，期望: {filename}，目录: {loc}，实际列表: {found_names[:10]}")
        return f"❌ 未找到脚本：{filename}\n目录 {loc} 中的脚本：{', '.join(found_names[:20])}"

    # 使用 task 命令运行脚本（比 scripts/run 更可靠）
    script_path = f"{path}/{filename}" if path else filename
    try:
        result = ql.run_command(f"task {script_path}")
    except Exception as e:
        logger.error(f"run_command 失败: {e}")
        return f"❌ 执行脚本失败：{e}"

    if result.get("code") == 200:
        return f"✅ 已执行{settings.bot.custom_script_button_name}脚本"
    return f"❌ 运行失败：{result.get('msg', '未知错误')}"


# ==================== 依赖指令 ====================

def _list_deps(ql: QLClient) -> str:
    deps = ql.list_dependencies()
    if not deps:
        return "暂无依赖"
    type_map = {0: "NodeJs", 1: "Python3", 2: "Linux"}
    lines = [f"📦 依赖列表（共 {len(deps)} 个）："]
    for d in deps:
        did = d.get("id", "")
        name = d.get("name", "未知")
        dtype = type_map.get(d.get("type"), str(d.get("type", "")))
        status = d.get("status", -1)
        tag = "✅" if status == 1 else "⛔"
        lines.append(f"{tag} [{did}] {name} ({dtype})")
    return "\n".join(lines)


def _dep_detail(arg: str, ql: QLClient) -> str:
    try:
        dep_id = int(arg)
    except ValueError:
        return f"无效的ID：{arg}"
    dep = ql.get_dependency(dep_id)
    if not dep:
        return f"未找到依赖 ID：{dep_id}"
    type_map = {0: "NodeJs", 1: "Python3", 2: "Linux"}
    return (
        f"📦 依赖详情：\n"
        f"  ID: {dep.get('id')}\n"
        f"  名称: {dep.get('name')}\n"
        f"  类型: {type_map.get(dep.get('type'), dep.get('type'))}\n"
        f"  备注: {dep.get('remark', '')}\n"
        f"  状态: {'启用' if dep.get('status') == 1 else '禁用'}"
    )


def _add_dep(arg: str, ql: QLClient) -> str:
    parts = arg.split(None, 2)
    if len(parts) < 2:
        return "格式：安装依赖 <名称> <类型> [备注]\n类型: 0=NodeJs 1=Python3 2=Linux"
    name = parts[0]
    try:
        dtype = int(parts[1])
    except ValueError:
        return f"类型须为数字：0=NodeJs 1=Python3 2=Linux，得到：{parts[1]}"
    remark = parts[2] if len(parts) > 2 else ""
    result = ql.create_dependency([{"name": name, "type": dtype, "remark": remark}])
    if result.get("code") == 200:
        return f"✅ 已创建依赖：{name}"
    return f"❌ 创建失败"


def _del_dep(arg: str, ql: QLClient) -> str:
    try:
        ids = [int(x.strip()) for x in arg.split(",")]
    except ValueError:
        return f"无效的ID：{arg}"
    result = ql.delete_dependencies(ids)
    return f"✅ 已删除依赖 ID：{ids}" if result.get("code") == 200 else f"❌ 删除失败"


def _reinstall_dep(arg: str, ql: QLClient) -> str:
    try:
        ids = [int(x.strip()) for x in arg.split(",")]
    except ValueError:
        return f"无效的ID：{arg}"
    result = ql.reinstall_dependency(ids)
    return f"✅ 已触发重装 ID：{ids}" if result.get("code") == 200 else f"❌ 重装失败"


# ==================== 配置指令 ====================

def _list_configs(ql: QLClient) -> str:
    configs = ql.list_configs()
    if not configs:
        return "暂无配置文件"
    lines = [f"⚙ 配置文件列表（共 {len(configs)} 个）："]
    for c in configs:
        lines.append(f"  · {c.get('title', c.get('value', '未知'))}")
    return "\n".join(lines)


def _config_detail(arg: str, ql: QLClient) -> str:
    detail = ql.get_config_detail(arg)
    if not detail:
        return f"未找到配置文件：{arg}"
    content = str(detail)
    if len(content) > 500:
        content = content[:500] + "..."
    return f"⚙ {arg}：\n{content}"


# ==================== 日志管理 ====================

def _list_logs(ql: QLClient) -> str:
    """列出所有日志文件"""
    logs = ql.list_logs()
    if not logs:
        return "暂无日志文件"
    lines = [f"📄 日志列表（共 {len(logs)} 个）："]
    for log in logs:
        name = log.get("title", log.get("file", "未知"))
        size = log.get("size", "")
        time = log.get("mtime", log.get("time", ""))
        info = f"  · {name}"
        if size:
            info += f" ({size})"
        if time:
            info += f" {time}"
        lines.append(info)
    return "\n".join(lines)


def _log_detail(arg: str, ql: QLClient) -> str:
    """查看指定日志文件内容"""
    content = ql.get_log_detail(file=arg)
    if not content:
        return f"未找到日志：{arg}"
    text = str(content)
    if len(text) > 2000:
        text = text[-2000:]
    return f"📄 {arg}：\n{text}"


def _del_log(arg: str, ql: QLClient) -> str:
    """删除指定日志文件"""
    result = ql.delete_logs(arg)
    if result.get("code") == 200:
        return f"✅ 日志已删除：{arg}"
    return f"❌ 删除失败：{result}"


# ==================== 命令管理 ====================

def _list_commands(ql: QLClient, search: str = "") -> str:
    """命令列表 + 操作提示"""
    cmds = ql.list_commands(search or None)
    if not cmds:
        return "📄 暂无命令\n\n💡 回复 新建命令 <名称> <命令内容> 添加命令"
    lines = [f"📄 命令列表（共 {len(cmds)} 个）："]
    for c in cmds:
        name = c.get("name") or "(无名称)"
        command = c.get("command", "")
        cid = c.get("id", "?")
        lines.append(f"  [{cid}] {name}")
        lines.append(f"      {command}")
    lines.append("\n💡 回复指令：")
    lines.append("  命令详情 <ID>      查看命令详情")
    lines.append("  运行命令 <ID>      运行命令")
    lines.append("  删命令 <ID>        删除命令")
    lines.append("  新建命令 <名称> <内容>  添加命令")
    return "\n".join(lines)


def _cmd_detail(arg: str, ql: QLClient) -> str:
    """命令详情"""
    cmd = ql.get_command(arg.strip())
    if not cmd:
        return f"未找到命令：{arg}"
    return (
        f"📄 命令详情\n"
        f"名称: {cmd.get('name', '')}\n"
        f"ID: {cmd.get('id', '')}\n"
        f"内容: {cmd.get('command', '')}\n"
        f"描述: {cmd.get('description') or '无'}\n"
        f"创建时间: {cmd.get('createTime') or '未知'}"
    )


def _add_command(arg: str, ql: QLClient) -> str:
    """新建命令：新建命令 <名称> <命令内容>"""
    parts = arg.split(None, 1)
    if len(parts) < 2:
        return "格式：新建命令 <名称> <命令内容>\n示例：新建命令 拉库 ql repo https://github.com/user/repo"
    name, command = parts[0], parts[1]
    result = ql.create_command({"name": name, "command": command})
    if result.get("code") == 200:
        return f"✅ 命令已创建：{name}"
    return f"❌ 创建失败：{result.get('msg', '未知错误')}"


def _run_command(arg: str, ql: QLClient) -> str:
    """运行命令"""
    cmd_id = arg.strip()
    cmd = ql.get_command(cmd_id)
    if not cmd:
        return f"未找到命令：{cmd_id}"
    result = ql.run_command_by_id(cmd_id)
    if result.get("code") == 200:
        return f"✅ 已开始运行：{cmd.get('name', cmd_id)}\n执行情况可在 命令详情 中查看"
    return f"❌ 运行失败：{result.get('msg', '未知错误')}"


def _del_command(arg: str, ql: QLClient) -> str:
    """删除命令"""
    cmd_id = arg.strip()
    cmd = ql.get_command(cmd_id)
    if not cmd:
        return f"未找到命令：{cmd_id}"
    result = ql.delete_commands([cmd_id])
    if result.get("code") == 200:
        return f"✅ 命令已删除：{cmd.get('name', cmd_id)}"
    return f"❌ 删除失败：{result.get('msg', '未知错误')}"


# ==================== 系统指令补充 ====================

def _system_log(arg: str, ql: QLClient) -> str:
    log = ql.get_system_log()
    if not log:
        return "暂无系统日志"
    content = str(log)
    if len(content) > 1000:
        content = content[-1000:]
    return f"📋 系统日志：\n{content}"


def _sys_config(ql: QLClient) -> str:
    cfg = ql.get_system_config()
    if not cfg:
        return "获取系统配置失败"
    lines = ["⚙ 系统配置："]
    for k, v in cfg.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _check_update(ql: QLClient) -> str:
    result = ql.check_update()
    if result.get("code") == 200:
        return f"✅ 检查更新完成：{result.get('data', '')}"
    return "❌ 检查更新失败"


def _update_system(ql: QLClient) -> str:
    result = ql.update_system()
    if result.get("code") == 200:
        return "✅ 系统更新已触发"
    return "❌ 更新失败"


def _reload_system(ql: QLClient) -> str:
    result = ql.reload_system()
    if result.get("code") == 200:
        return "✅ 系统已重载"
    return "❌ 重载失败"


def _clear_sys_log(ql: QLClient) -> str:
    result = ql.delete_system_log()
    if result.get("code") == 200:
        return "✅ 系统日志已清空"
    return "❌ 清空失败"


def _export_data(ql: QLClient) -> str:
    result = ql.export_data()
    if result.get("code") == 200:
        return f"✅ 数据导出完成：{result.get('data', '')}"
    return "❌ 导出失败"


# ==================== 帮助 ====================

def help_text() -> str:
    return (
        "📌 支持指令：\n"
        "💡 <任务名> 可用序号代替，如 执行 1\n"
        "── 任务管理 ──\n"
        "  任务 / 任务列表\n"
        "  状态 <任务名>\n"
        "  执行 <任务名>\n"
        "  停止 <任务名>\n"
        "  日志 <任务名>\n"
        "  禁用任务 <任务名>\n"
        "  启用任务 <任务名>\n"
        "  删除任务 <任务名>\n"
        "  运行中任务\n"
        "  修改定时 <任务名> <cron表达式>\n"
        "── 环境变量 ──\n"
        "  变量 / 变量列表 [关键词]\n"
        "  设变量 <名称>=<值> [备注]\n"
        "  查看变量 <ID>\n"
        "  删变量 <ID>\n"
        "  禁用变量 <ID>\n"
        "  启用变量 <ID>\n"
        "── 订阅管理 ──\n"
        "  订阅 / 订阅列表\n"
        "  创建订阅 <仓库URL> [别名]\n"
        "  运行订阅 <订阅名>\n"
        "  停止订阅 <订阅名>\n"
        "  禁用订阅 <订阅名>\n"
        "  启用订阅 <订阅名>\n"
        "  订阅日志 <订阅名>\n"
        "── 脚本 ──\n"
        "  脚本 / 脚本列表\n"
        "  脚本详情 <文件名> [路径]\n"
        "  运行脚本 <文件名> [路径]\n"
        "  停止脚本 <文件名> [路径]\n"
        "  删除脚本 <文件名> [路径]\n"
        "  重命名脚本 <原名> <新名> [路径]\n"
        "── 依赖 ──\n"
        "  依赖 / 依赖列表\n"
        "  依赖详情 <ID>\n"
        "  安装依赖 <名称> <类型> [备注]\n"
        "  删依赖 <ID>\n"
        "  重装依赖 <ID>\n"
        "── 配置 ──\n"
        "  配置 / 配置列表\n"
        "  查看配置 <路径>\n"
        "── 日志管理 ──\n"
        "  日志列表\n"
        "  日志详情 <文件名>\n"
        "  删除日志 <文件名>\n"
        "── 命令管理 ──\n"
        "  命令 / 命令列表\n"
        "  新建命令 <名称> <命令内容>\n"
        "  命令详情 <ID>\n"
        "  运行命令 <ID>\n"
        "  删命令 <ID>\n"
        "── 系统 ──\n"
        "  系统\n"
        "  系统配置\n"
        "  系统日志\n"
        "  清系统日志\n"
        "  检查更新\n"
        "  更新系统\n"
        "  重载系统\n"
        "  导出数据\n"
        "  通知 <标题>=<内容>"
    )