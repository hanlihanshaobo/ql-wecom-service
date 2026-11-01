"""运行时配置。

配置来源（优先级从低到高）：
1. 代码内默认值
2. config/bot.json（青龙机器人插件配置）
3. 环境变量 / .env（独立部署时使用）

这样同一套代码既可以在青龙面板里以 `python3 -m jbot` 运行，
也可以继续用 `uvicorn app:app` 独立部署。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("wecom")

try:  # 独立部署时可选；插件环境没有 dotenv 也能运行
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 只在精简环境触发
    load_dotenv = None

# 本文件位于 <项目根>/jbot/config.py 或 <QL数据目录>/jbot/config.py
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_API_BASE = "https://qyapi.weixin.qq.com"


def _load_env_files() -> None:
    if load_dotenv is None:
        return
    candidates = [BASE_DIR / ".env", Path.cwd() / ".env"]
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen or not candidate.is_file():
            continue
        seen.add(resolved)
        load_dotenv(candidate, override=False)


def _config_candidates() -> list[Path]:
    candidates: list[Path] = []
    explicit = os.getenv("BOT_CONFIG", "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())

    candidates.append(BASE_DIR / "config" / "bot.json")
    candidates.append(Path.cwd() / "config" / "bot.json")

    ql_data = os.getenv("QL_DATA_DIR", "").strip()
    if ql_data:
        candidates.append(Path(ql_data) / "config" / "bot.json")

    ql_dir = os.getenv("QL_DIR", "").strip()
    if ql_dir:
        candidates.append(Path(ql_dir) / "data" / "config" / "bot.json")

    return candidates


def _load_config_file() -> tuple[dict, Path | None]:
    seen: set[Path] = set()
    for candidate in _config_candidates():
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if not candidate.is_file():
            continue
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                logger.info("已加载机器人配置: %s", candidate)
                return data, candidate
            logger.warning("配置文件不是 JSON 对象，已忽略: %s", candidate)
        except (OSError, ValueError) as exc:
            logger.error("读取配置文件失败 %s: %s", candidate, exc)
    return {}, None


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _section(data: dict, *names: str) -> dict:
    for name in names:
        value = data.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _value(data: dict, key: str, default: str = "") -> str:
    value = data.get(key)
    if value is None:
        return default
    return str(value).strip()


def _as_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [
            item.strip()
            for item in value.replace("，", ",").split(",")
            if item.strip()
        ]
    return []


def _bind_host(callback_data: dict) -> str:
    """监听地址只认 callback.host / CALLBACK_BIND，避免把公网域名当成 bind。"""
    return _env("CALLBACK_BIND", default=_value(callback_data, "host")) or "0.0.0.0"


@dataclass
class WecomConfig:
    corp_id: str = ""
    agent_id: str = ""
    corp_secret: str = ""
    encoding_aes_key: str = ""
    encrypt_mode: str = "NORMAL"
    api_base: str = DEFAULT_API_BASE

    @property
    def plain_mode(self) -> bool:
        """NORMAL / plain / 空值都按明文模式处理。"""
        return self.encrypt_mode.strip().lower() in ("", "normal", "plain", "false", "0", "no")

    @property
    def configured(self) -> bool:
        return bool(self.corp_id and self.agent_id and self.corp_secret)


@dataclass
class CallbackConfig:
    host: str = "0.0.0.0"
    port: int = 3000
    path: str = "/wecom/callback"
    token: str = ""
    secret: str = ""
    public_url: str = ""


@dataclass
class QLConfig:
    base_url: str = "http://127.0.0.1:5700"
    client_id: str = ""
    client_secret: str = ""
    host: str = ""


@dataclass
class BotConfig:
    prefix: str = ""
    name: str = "QinglongBot"
    allowed_users: list[str] = field(default_factory=list)
    custom_script_filename: str = ""
    custom_script_path: str = ""
    custom_script_button_name: str = "执行自定义脚本"


@dataclass
class Settings:
    wecom: WecomConfig = field(default_factory=WecomConfig)
    callback: CallbackConfig = field(default_factory=CallbackConfig)
    ql: QLConfig = field(default_factory=QLConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    config_file: str = ""


def load_settings() -> Settings:
    _load_env_files()
    data, config_file = _load_config_file()

    wecom_data = _section(data, "wecom", "we_com")
    callback_data = _section(data, "callback", "server")
    ql_data = _section(data, "qinglong", "ql")
    bot_data = _section(data, "bot")

    callback_host_env = _env("CALLBACK_HOST")
    callback_path = _env(
        "CALLBACK_PATH",
        default=_value(callback_data, "path"),
    ) or "/wecom/callback"
    if not callback_path.startswith("/"):
        callback_path = "/" + callback_path
    callback_port = _as_int(
        _env("CALLBACK_PORT", default=_value(callback_data, "port")),
        3000,
    )
    if callback_port <= 0:
        callback_port = 3000

    settings = Settings(
        wecom=WecomConfig(
            corp_id=_env("WE_COM_CORP_ID", default=_value(wecom_data, "corp_id")),
            agent_id=_env("WE_COM_AGENT_ID", default=_value(wecom_data, "agent_id")),
            corp_secret=_env(
                "WE_COM_CORP_SECRET",
                default=_value(wecom_data, "corp_secret", _value(wecom_data, "secret")),
            ),
            encoding_aes_key=_env(
                "WE_COM_ENCODING_AES_KEY",
                default=_value(wecom_data, "encoding_aes_key"),
            ),
            encrypt_mode=_env(
                "WE_COM_ENCRYPT_MODE",
                default=_value(wecom_data, "encrypt_mode", "NORMAL"),
            ),
            api_base=_env(
                "WE_COM_API_BASE",
                default=_value(wecom_data, "api_base", DEFAULT_API_BASE),
            ),
        ),
        callback=CallbackConfig(
            host=_bind_host(callback_data),
            port=callback_port,
            path=callback_path,
            token=_env(
                "CALLBACK_TOKEN",
                default=_value(callback_data, "token"),
            ),
            secret=_env(
                "CALLBACK_SECRET",
                default=_value(callback_data, "secret"),
            ),
            public_url=_env(
                "CALLBACK_PUBLIC_URL",
                default=callback_host_env
                if "://" in callback_host_env
                else _value(callback_data, "public_url"),
            ),
        ),
        ql=QLConfig(
            base_url=_env(
                "QL_BASE_URL",
                default=_value(ql_data, "base_url"),
            ) or "http://127.0.0.1:5700",
            client_id=_env(
                "QL_CLIENT_ID",
                default=_value(ql_data, "client_id"),
            ),
            client_secret=_env(
                "QL_CLIENT_SECRET",
                default=_value(ql_data, "client_secret"),
            ),
            host=_env("QL_HOST", default=_value(ql_data, "host")),
        ),
        bot=BotConfig(
            prefix=_env("BOT_PREFIX", default=_value(bot_data, "prefix")),
            name=_env("BOT_NAME", default=_value(bot_data, "name", "QinglongBot")),
            allowed_users=_as_list(
                _env("BOT_ALLOWED_USERS", default=bot_data.get("allowed_users", []))
            ),
            custom_script_filename=_env(
                "CUSTOM_SCRIPT_FILENAME",
                default=_value(bot_data, "custom_script_filename"),
            ),
            custom_script_path=_env(
                "CUSTOM_SCRIPT_PATH",
                default=_value(bot_data, "custom_script_path"),
            ),
            custom_script_button_name=_env(
                "CUSTOM_SCRIPT_BUTTON_NAME",
                default=_value(
                    bot_data,
                    "custom_script_button_name",
                    "执行自定义脚本",
                ),
            ),
        ),
        config_file=str(config_file) if config_file else "",
    )

    if not settings.wecom.configured:
        logger.warning(
            "企业微信配置不完整：请在 %s 或环境变量中设置 "
            "WE_COM_CORP_ID / WE_COM_AGENT_ID / WE_COM_CORP_SECRET",
            config_file or BASE_DIR / "config" / "bot.json",
        )
    if not settings.wecom.plain_mode:
        if not settings.wecom.encoding_aes_key:
            logger.error(
                "WE_COM_ENCRYPT_MODE 为 SAFETY，但未设置 encoding_aes_key；"
                "企业微信回调将无法解密"
            )
        if not settings.callback.token:
            logger.error(
                "WE_COM_ENCRYPT_MODE 为 SAFETY，但未设置 callback.token；"
                "企业微信回调签名校验将失败"
            )
    return settings


settings = load_settings()
