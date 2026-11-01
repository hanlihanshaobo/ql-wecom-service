"""企业微信应用 API 客户端。

只依赖 corp_id / agent_id / corp_secret，既可用于青龙面板机器人插件，
也可用于独立部署的回调服务。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Iterable

import httpx

from .text import MAX_TEXT_BYTES, split_text

logger = logging.getLogger("wecom")

DEFAULT_API_BASE = "https://qyapi.weixin.qq.com"
# 兼容旧代码中的私有函数名
_split_text = split_text


class WeComClient:
    def __init__(
        self,
        corp_id: str = "",
        agent_id: str = "",
        secret: str = "",
        api_base: str = DEFAULT_API_BASE,
        timeout: float = 15.0,
    ):
        self.corp_id = (corp_id or "").strip()
        self.agent_id = str(agent_id or "").strip()
        try:
            self._agent_id_value: int | str = int(self.agent_id)
        except (TypeError, ValueError):
            self._agent_id_value = self.agent_id
        self.secret = (secret or "").strip()
        self.api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self._token = ""
        self._expires_at = 0.0
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.corp_id and self.secret and self.agent_id)

    def get_access_token(self, force: bool = False) -> str:
        """获取 access_token，带进程内缓存（提前 5 分钟刷新）。"""
        if not self.corp_id or not self.secret:
            logger.warning("企业微信 corp_id/corp_secret 未配置，无法获取 access_token")
            return ""

        now = time.time()
        if not force and self._token and now < self._expires_at - 300:
            return self._token

        with self._lock:
            if not force and self._token and now < self._expires_at - 300:
                return self._token
            try:
                resp = self._client.get(
                    f"{self.api_base}/cgi-bin/gettoken",
                    params={"corpid": self.corp_id, "corpsecret": self.secret},
                )
                data = resp.json()
            except Exception as exc:  # noqa: BLE001 - 网络异常统一记录
                logger.error("请求企业微信 token 异常: %s", exc)
                return ""

            token = data.get("access_token", "")
            if token:
                self._token = token
                self._expires_at = now + int(data.get("expires_in", 7200))
                return token

            logger.error("获取企业微信 token 失败: %s", data)
            return ""

    def send_text(self, user_id: str, content: str) -> bool:
        """发送文本消息；超长内容自动分片，全部成功才返回 True。"""
        if not user_id or not content:
            return False
        token = self.get_access_token()
        if not token:
            return False

        chunks = _split_text(content)
        if not chunks:
            return False

        url = f"{self.api_base}/cgi-bin/message/send"
        ok = True
        for chunk in chunks:
            payload = {
                "touser": user_id,
                "msgtype": "text",
                "agentid": self._agent_id_value,
                "text": {"content": chunk},
                "safe": 0,
            }
            try:
                resp = self._client.post(url, params={"access_token": token}, json=payload)
                data = resp.json()
            except Exception as exc:  # noqa: BLE001
                logger.error("发送企业微信消息异常: %s", exc)
                ok = False
                break

            if data.get("errcode") != 0:
                logger.error("发送企业微信消息失败: %s", data)
                ok = False
                break
        return ok

    def create_menu(self, menu: dict | Iterable[dict]) -> bool:
        """创建/更新应用菜单。menu 可以是 {"button": [...]} 或按钮列表。"""
        if not self.configured:
            logger.warning("企业微信配置不完整，跳过菜单创建")
            return False

        token = self.get_access_token()
        if not token:
            logger.error("无法获取 access_token，菜单创建失败")
            return False

        body = menu if isinstance(menu, dict) else {"button": list(menu)}
        url = f"{self.api_base}/cgi-bin/menu/create"
        try:
            resp = self._client.post(
                url,
                params={"access_token": token, "agentid": self._agent_id_value},
                json=body,
            )
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("创建企业微信菜单异常: %s", exc)
            return False

        if data.get("errcode") == 0:
            logger.info("✅ 企业微信应用菜单创建成功")
            return True

        logger.error("创建企业微信菜单失败: %s", data)
        return False
