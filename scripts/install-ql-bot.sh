#!/usr/bin/env bash
#
# 手动把本仓库（或指定分支/仓库）安装为青龙面板机器人插件。
#
# 适用场景：功能分支尚未合并到 main，无法直接通过 `ql bot` + BotRepoUrl 安装。
# 合并到 main 后，推荐直接使用青龙自带的 `ql bot`。
#
# 用法：
#   ./scripts/install-ql-bot.sh
#   ./scripts/install-ql-bot.sh --repo https://github.com/user/repo --branch feat/wecom-ai-bot
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QL_DIR="${QL_DIR:-/ql}"
QL_DATA_DIR="${QL_DATA_DIR:-${QL_DIR}/data}"
QL_LOG_DIR="${QL_LOG_DIR:-${QL_DATA_DIR}/log}"
REPO_URL=""
BRANCH=""
SOURCE_DIR="${REPO_DIR}"
TEMP_DIR=""

usage() {
  cat <<'EOF'
用法: install-ql-bot.sh [选项]

选项:
  --repo <url>      从指定 Git 仓库安装（默认使用当前脚本所在目录）
  --branch <name>   指定分支，需配合 --repo 使用
  -h, --help        显示帮助

示例:
  ./scripts/install-ql-bot.sh
  ./scripts/install-ql-bot.sh --repo https://github.com/hanlihanshaobo/ql-wecom-service --branch feat/qinglong-bot-plugin
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "❌ --repo 需要参数" >&2; exit 1; }
      REPO_URL="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || { echo "❌ --branch 需要参数" >&2; exit 1; }
      BRANCH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "❌ 未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cleanup() {
  if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
    rm -rf "${TEMP_DIR}"
  fi
}
trap cleanup EXIT

if [[ -n "${REPO_URL}" ]]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "❌ 需要 git 才能从仓库安装" >&2
    exit 1
  fi
  TEMP_DIR="$(mktemp -d)"
  echo "➜ 拉取 ${REPO_URL}${BRANCH:+ (分支: ${BRANCH})} ..."
  if [[ -n "${BRANCH}" ]]; then
    git clone --depth=1 --branch "${BRANCH}" -- "${REPO_URL}" "${TEMP_DIR}/repo"
  else
    git clone --depth=1 -- "${REPO_URL}" "${TEMP_DIR}/repo"
  fi
  SOURCE_DIR="${TEMP_DIR}/repo"
elif [[ -n "${BRANCH}" ]]; then
  echo "❌ --branch 需要配合 --repo 使用" >&2
  exit 1
fi

if [[ ! -f "${SOURCE_DIR}/jbot/requirements.txt" || ! -f "${SOURCE_DIR}/config/bot.json" ]]; then
  echo "❌ 安装源缺少 jbot/requirements.txt 或 config/bot.json: ${SOURCE_DIR}" >&2
  exit 1
fi

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
pip3 install --default-timeout=100 -r "${SOURCE_DIR}/jbot/requirements.txt"

echo "➜ 复制插件代码到 ${QL_DATA_DIR}/jbot ..."
rm -rf "${QL_DATA_DIR}/jbot.new"
cp -a "${SOURCE_DIR}/jbot" "${QL_DATA_DIR}/jbot.new"
rm -rf "${QL_DATA_DIR}/jbot"
mv "${QL_DATA_DIR}/jbot.new" "${QL_DATA_DIR}/jbot"

mkdir -p "${QL_DATA_DIR}/config" "${QL_LOG_DIR}/bot"
if [[ ! -f "${QL_DATA_DIR}/config/bot.json" ]]; then
  cp "${SOURCE_DIR}/config/bot.json" "${QL_DATA_DIR}/config/bot.json"
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
