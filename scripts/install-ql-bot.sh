#!/usr/bin/env bash
#
# 手动把当前仓库安装为青龙面板机器人插件。
#
# 适用场景：功能分支尚未合并到 main，无法直接通过 `ql bot` + BotRepoUrl 安装。
# 合并到 main 后，推荐直接使用青龙自带的 `ql bot`。
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QL_DIR="${QL_DIR:-/ql}"
QL_DATA_DIR="${QL_DATA_DIR:-${QL_DIR}/data}"
QL_LOG_DIR="${QL_LOG_DIR:-${QL_DATA_DIR}/log}"

if [[ ! -d "${QL_DATA_DIR}" ]]; then
  echo "❌ 未找到青龙数据目录: ${QL_DATA_DIR}" >&2
  echo "   请通过 QL_DATA_DIR 指定，例如: QL_DATA_DIR=/opt/ql/data $0" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1 || ! command -v pip3 >/dev/null 2>&1; then
  echo "❌ 需要 python3 和 pip3，请在青龙容器内执行本脚本" >&2
  exit 1
fi

echo "➜ 安装 Python 依赖..."
pip3 install --default-timeout=100 -r "${REPO_DIR}/jbot/requirements.txt"

echo "➜ 复制插件代码到 ${QL_DATA_DIR}/jbot ..."
rm -rf "${QL_DATA_DIR}/jbot.new"
cp -a "${REPO_DIR}/jbot" "${QL_DATA_DIR}/jbot.new"
rm -rf "${QL_DATA_DIR}/jbot"
mv "${QL_DATA_DIR}/jbot.new" "${QL_DATA_DIR}/jbot"

mkdir -p "${QL_DATA_DIR}/config" "${QL_LOG_DIR}/bot"
if [[ ! -f "${QL_DATA_DIR}/config/bot.json" ]]; then
  cp "${REPO_DIR}/config/bot.json" "${QL_DATA_DIR}/config/bot.json"
  chmod 600 "${QL_DATA_DIR}/config/bot.json"
  echo "➜ 已生成配置: ${QL_DATA_DIR}/config/bot.json"
else
  echo "➜ 保留已有配置: ${QL_DATA_DIR}/config/bot.json"
  if ! grep -q '"wecom_bot"' "${QL_DATA_DIR}/config/bot.json" 2>/dev/null; then
    echo "⚠ 当前配置不是智能机器人格式，请替换为 config/bot.json 中的 wecom_bot 配置"
  fi
fi

echo "➜ 停止旧机器人进程..."
data_dir_real="$(readlink -f "${QL_DATA_DIR}")"
for proc in /proc/[0-9]*; do
  pid="${proc##*/}"
  [[ "${pid}" == "$$" ]] && continue
  [[ -r "${proc}/cmdline" ]] || continue
  args="$(tr '\000' ' ' < "${proc}/cmdline" 2>/dev/null || true)"
  case "${args}" in
    *"python3 -m jbot"*)
      if [[ "$(readlink -f "${proc}/cwd" 2>/dev/null || true)" == "${data_dir_real}" ]]; then
        kill "${pid}" 2>/dev/null || true
      fi
      ;;
  esac
done
sleep 1

echo "➜ 启动机器人..."
export QL_DIR QL_DATA_DIR QL_LOG_DIR
cd "${QL_DATA_DIR}"
nohup python3 -m jbot >"${QL_LOG_DIR}/bot/nohup.log" 2>&1 &
bot_pid=$!
sleep 2
if kill -0 "${bot_pid}" 2>/dev/null; then
  echo "✅ 已启动，PID: ${bot_pid}"
else
  echo "❌ 机器人启动失败，日志如下：" >&2
  tail -n 50 "${QL_LOG_DIR}/bot/nohup.log" >&2 || true
  exit 1
fi
echo
echo "下一步："
echo "  1. 企业微信后台 → 管理工具 → 智能机器人 → 创建机器人 → API 模式 → 长连接"
echo "  2. 编辑 ${QL_DATA_DIR}/config/bot.json，填入 wecom_bot.bot_id / secret"
echo "  3. 重启机器人: ql bot（或重新执行本脚本）"
echo "  4. 把机器人拉进群或单聊，@机器人 发送「帮助」"
