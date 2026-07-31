from ql_client import QLClient


def process_command(cmd: str, ql: QLClient) -> str:
    parts = cmd.strip().split(None, 1)
    action = parts[0] if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    # ---- 任务 ----
    if action in ("任务", "任务列表", "tasks", "list"):
        return list_tasks(ql)
    if action in ("执行", "运行", "run"):
        if not arg:
            return "请指定要执行的任务名，例如：执行 签到"
        return _run_task(arg, ql)
    if action in ("停止", "stop"):
        if not arg:
            return "请指定要停止的任务名，例如：停止 签到"
        return _stop_task(arg, ql)
    if action in ("日志", "log"):
        if not arg:
            return "请指定任务的日志，例如：日志 签到"
        return _get_logs(arg, ql)
    if action in ("状态", "status"):
        return _status(arg, ql)
    if action in ("禁用任务", "disable_task"):
        if not arg:
            return "请指定任务名，例如：禁用任务 签到"
        return _disable_task(arg, ql)
    if action in ("启用任务", "enable_task"):
        if not arg:
            return "请指定任务名，例如：启用任务 签到"
        return _enable_task(arg, ql)
    if action in ("删除任务", "delete_task"):
        if not arg:
            return "请指定任务名，例如：删除任务 签到"
        return _delete_task(arg, ql)

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
    if action in ("运行订阅", "run_sub"):
        if not arg:
            return "请指定订阅名称，例如：运行订阅 网易云"
        return _run_subscription(arg, ql)

    # ---- 系统 ----
    if action in ("系统", "system"):
        return system_info(ql)
    if action in ("通知", "notify"):
        if not arg:
            return "格式：通知 <标题>=<内容>"
        return _send_notify(arg, ql)

    # ---- 脚本 ----
    if action in ("脚本", "脚本列表", "scripts"):
        return list_scripts(arg, ql)

    return help_text()


# ==================== 任务指令 ====================

def list_tasks(ql: QLClient) -> str:
    crons = ql.list_crons()
    if not crons:
        return "暂无任务"
    lines = [f"📋 任务列表（共 {len(crons)} 个）："]
    for c in crons:
        name = c.get("name", "未知")
        status = c.get("status", -1)
        is_pinned = c.get("isPinned", 0) or c.get("pinned", False)
        tag = "✅" if status == 1 else "⛔"
        pin = "📌" if is_pinned else ""
        lines.append(f"{tag}{pin} {name}")
    return "\n".join(lines)


def _run_task(name: str, ql: QLClient) -> str:
    result = ql.run_cron_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已执行任务：{name}"
    return f"❌ 执行失败：{result.get('msg', '未知错误')}"


def _stop_task(name: str, ql: QLClient) -> str:
    result = ql.stop_cron_by_name(name)
    if result.get("code") == 200:
        return f"🛑 已停止任务：{name}"
    return f"❌ 停止失败：{result.get('msg', '未知错误')}"


def _disable_task(name: str, ql: QLClient) -> str:
    result = ql.disable_cron_by_name(name)
    if result.get("code") == 200:
        return f"⛔ 已禁用任务：{name}"
    return f"❌ 禁用失败：{result.get('msg', '未知错误')}"


def _enable_task(name: str, ql: QLClient) -> str:
    result = ql.enable_cron_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已启用任务：{name}"
    return f"❌ 启用失败：{result.get('msg', '未知错误')}"


def _delete_task(name: str, ql: QLClient) -> str:
    cron = ql.get_cron_by_name(name)
    if not cron:
        return f"未找到任务：{name}"
    result = ql.delete_crons([cron["id"]])
    if result.get("code") == 200:
        return f"🗑 已删除任务：{name}"
    return f"❌ 删除失败"


def _get_logs(name: str, ql: QLClient) -> str:
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
    for f in log_files[:5]:
        filename = f.get("filename", "未知")
        lines.append(f"  · {filename}")

    return "\n".join(lines)


def _status(name: str, ql: QLClient) -> str:
    if not name:
        return "请指定任务名，例如：状态 签到"
    cron = ql.get_cron_by_name(name)
    if not cron:
        return f"未找到任务：{name}"
    status_map = {0: "已暂停", 1: "运行中", 2: "队列中"}
    st = status_map.get(cron.get("status"), str(cron.get("status")))
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


def _run_subscription(name: str, ql: QLClient) -> str:
    result = ql.run_subscription_by_name(name)
    if result.get("code") == 200:
        return f"✅ 已运行订阅：{name}"
    return f"❌ 运行失败：{result.get('msg', '未知错误')}"


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
    for s in scripts[:20]:
        name = s.get("title", s.get("name", "未知"))
        lines.append(f"  · {name}")
    if len(scripts) > 20:
        lines.append(f"  ... 还有 {len(scripts) - 20} 个")
    return "\n".join(lines)


# ==================== 帮助 ====================

def help_text() -> str:
    return (
        "📌 支持指令：\n"
        "── 任务管理 ──\n"
        "  任务 / 任务列表\n"
        "  状态 <任务名>\n"
        "  执行 <任务名>\n"
        "  停止 <任务名>\n"
        "  日志 <任务名>\n"
        "  禁用任务 <任务名>\n"
        "  启用任务 <任务名>\n"
        "  删除任务 <任务名>\n"
        "── 环境变量 ──\n"
        "  变量 / 变量列表 [关键词]\n"
        "  设变量 <名称>=<值> [备注]\n"
        "  查看变量 <ID>\n"
        "  删变量 <ID>\n"
        "  禁用变量 <ID>\n"
        "  启用变量 <ID>\n"
        "── 订阅管理 ──\n"
        "  订阅 / 订阅列表\n"
        "  运行订阅 <订阅名>\n"
        "── 脚本 ──\n"
        "  脚本 / 脚本列表\n"
        "── 系统 ──\n"
        "  系统\n"
        "  通知 <标题>=<内容>"
    )