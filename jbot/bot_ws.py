"""企业微信智能机器人长连接客户端（WebSocket）。

协议参考：https://developer.work.weixin.qq.com/document/path/101463
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any

import websockets

from .commands import process_command
from .config import Settings
from .ql_client import QLClient
from .text import split_text

logger = logging.getLogger("wecom")

CMD_SUBSCRIBE = "aibot_subscribe"
CMD_MSG_CALLBACK = "aibot_msg_callback"
CMD_EVENT_CALLBACK = "aibot_event_callback"
CMD_RESPOND_MSG = "aibot_respond_msg"
CMD_RESPOND_WELCOME = "aibot_respond_welcome_msg"
CMD_PING = "ping"

DEFAULT_WS_URL = "wss://openws.work.weixin.qq.com"
MAX_REPLY_CHUNKS = 5


def _req_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def _make_ql(settings: Settings) -> QLClient:
    return QLClient(
        settings.ql.base_url,
        client_id=settings.ql.client_id or None,
        client_secret=settings.ql.client_secret or None,
        host_header=settings.ql.host or None,
    )


class WeComBot:
    """维护与企业微信智能机器人的 WebSocket 长连接。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._ws: Any = None
        self._send_lock = asyncio.Lock()
        self._auth_event = asyncio.Event()
        self._fatal = False
        self._stop = False
        self._missed_pings = 0
        self._message_tasks: set[asyncio.Task] = set()
        self._seen: dict[str, float] = {}
        self._seen_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 主循环 / 重连
    # ------------------------------------------------------------------

    async def run(self) -> None:
        attempt = 0
        max_attempts = self.settings.wecom_bot.max_reconnect_attempts
        while not self._stop and not self._fatal:
            started = time.monotonic()
            try:
                await self._connect_once()
                # 连接稳定运行超过 10 秒后，重置重连计数
                if time.monotonic() - started >= 10:
                    attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                if not self._stop:
                    logger.error("WebSocket 连接异常: %s", exc)

            if self._stop or self._fatal:
                break

            attempt += 1
            if max_attempts != -1 and attempt > max_attempts:
                logger.error("WebSocket 重连次数已达上限（%s），停止重连", max_attempts)
                break
            delay = min(2 ** (attempt - 1), 30)
            logger.info("将在 %s 秒后重连（第 %s 次）...", delay, attempt)
            await asyncio.sleep(delay)

        await self._cancel_message_tasks()

    async def stop(self) -> None:
        self._stop = True
        ws = self._ws
        if ws is not None:
            try:
                await ws.close()
            except Exception:  # noqa: BLE001
                pass

    async def _connect_once(self) -> None:
        url = self.settings.wecom_bot.ws_url or DEFAULT_WS_URL
        logger.info("连接企业微信智能机器人: %s", url)
        self._auth_event.clear()
        self._missed_pings = 0

        async with websockets.connect(
            url,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=5,
            open_timeout=15,
            max_size=4 * 1024 * 1024,
        ) as ws:
            self._ws = ws
            await self._send(
                {
                    "cmd": CMD_SUBSCRIBE,
                    "headers": {"req_id": _req_id("subscribe")},
                    "body": {
                        "bot_id": self.settings.wecom_bot.bot_id,
                        "secret": self.settings.wecom_bot.secret,
                    },
                }
            )
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
            try:
                async for raw in ws:
                    await self._handle_raw(raw)
                    if self._fatal:
                        break
            finally:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
                self._ws = None

        if self._fatal:
            return
        logger.info("WebSocket 连接已关闭，准备重连")

    # ------------------------------------------------------------------
    # 发送 / 心跳
    # ------------------------------------------------------------------

    async def _send(self, frame: dict) -> None:
        ws = self._ws
        if ws is None:
            raise RuntimeError("WebSocket 未连接")
        async with self._send_lock:
            await ws.send(json.dumps(frame, ensure_ascii=False))

    async def _heartbeat_loop(self, ws: Any) -> None:
        try:
            try:
                await asyncio.wait_for(self._auth_event.wait(), timeout=20)
            except asyncio.TimeoutError:
                logger.error("企业微信智能机器人认证超时，断开重连")
                await ws.close()
                return
            interval = max(5, int(self.settings.wecom_bot.heartbeat_interval))
            while True:
                await asyncio.sleep(interval)
                if self._missed_pings >= 2:
                    logger.warning("连续 %s 次未收到心跳响应，主动断开重连", self._missed_pings)
                    await ws.close()
                    return
                self._missed_pings += 1
                try:
                    await self._send(
                        {
                            "cmd": CMD_PING,
                            "headers": {"req_id": _req_id("ping")},
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("发送心跳失败: %s", exc)
                    await ws.close()
                    return
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # 帧处理
    # ------------------------------------------------------------------

    async def _handle_raw(self, raw: Any) -> None:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            frame = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("忽略无法解析的 WebSocket 帧: %s", exc)
            return

        if not isinstance(frame, dict):
            return

        cmd = frame.get("cmd")
        if cmd == CMD_MSG_CALLBACK:
            task = asyncio.create_task(self._handle_message(frame))
            self._message_tasks.add(task)
            task.add_done_callback(self._message_tasks.discard)
            return

        if cmd == CMD_EVENT_CALLBACK:
            await self._handle_event(frame)
            return

        # 认证响应 / 心跳响应 / 回复回执
        req_id = str(frame.get("headers", {}).get("req_id", ""))
        if req_id.startswith("subscribe"):
            errcode = frame.get("errcode", 0)
            if errcode == 0:
                logger.info("✅ 企业微信智能机器人认证成功")
                self._auth_event.set()
            else:
                logger.error(
                    "企业微信智能机器人认证失败: errcode=%s, errmsg=%s",
                    errcode,
                    frame.get("errmsg"),
                )
                self._fatal = True
                await self.stop()
            return

        if req_id.startswith("ping"):
            if frame.get("errcode", 0) == 0:
                self._missed_pings = 0
            else:
                logger.warning("心跳响应异常: %s", frame)
            return

    async def _handle_event(self, frame: dict) -> None:
        body = frame.get("body", {}) or {}
        if not isinstance(body, dict):
            return
        event = body.get("event", {}) or {}
        if not isinstance(event, dict):
            event = {}
        event_type = event.get("eventtype", "")
        logger.info("收到机器人事件: %s", event_type)

        if event_type == "enter_chat":
            await self._reply(
                frame,
                {
                    "msgtype": "text",
                    "text": {"content": self.settings.wecom_bot.welcome_message},
                },
                cmd=CMD_RESPOND_WELCOME,
            )
            return

        if event_type == "disconnected_event":
            logger.warning("当前长连接已被新连接替换，停止重连")
            self._fatal = True
            await self.stop()
            return

    async def _handle_message(self, frame: dict) -> None:
        body = frame.get("body", {}) or {}
        if not isinstance(body, dict):
            return
        msg_id = str(body.get("msgid", ""))
        if await self._is_duplicate(msg_id):
            logger.info("重复消息，已忽略: %s", msg_id)
            return

        msgtype = body.get("msgtype", "")
        from_user = str(body.get("from", {}).get("userid", ""))
        chattype = body.get("chattype", "")
        logger.info(
            "收到机器人消息: from=%s, chattype=%s, msgtype=%s, msgid=%s",
            from_user,
            chattype,
            msgtype,
            msg_id,
        )

        if msgtype != "text":
            await self._reply(
                frame,
                {
                    "msgtype": "markdown",
                    "markdown": {"content": "目前仅支持文本指令，请发送「帮助」查看用法。"},
                },
            )
            return

        content = str(body.get("text", {}).get("content", "")).strip()
        content = self._strip_mention(content)
        content = self._strip_prefix(content)

        allowed = self.settings.bot.allowed_users
        if allowed and from_user not in allowed:
            logger.warning("未授权用户: %s", from_user)
            await self._reply(
                frame,
                {
                    "msgtype": "markdown",
                    "markdown": {"content": "⛔ 无权限使用此机器人"},
                },
            )
            return

        if not content:
            content = "帮助"

        try:
            def run_command() -> str:
                return process_command(content, _make_ql(self.settings))

            result = await asyncio.to_thread(run_command)
        except Exception as exc:  # noqa: BLE001
            logger.exception("处理机器人指令失败: %s", exc)
            result = f"❌ 操作失败：{exc}\n\n请检查青龙面板连接是否正常"

        logger.info("处理结果: %s", result[:100] if result else "EMPTY")
        await self._reply_text(frame, result or "✅ 操作完成")

    async def _reply_text(self, frame: dict, content: str) -> None:
        chunks = split_text(content, 1800)
        if len(chunks) > MAX_REPLY_CHUNKS:
            chunks = chunks[:MAX_REPLY_CHUNKS]
            chunks[-1] += "\n\n…（内容过长，已截断）"
        if not chunks:
            chunks = ["✅ 操作完成"]

        for chunk in chunks:
            await self._reply(
                frame,
                {
                    "msgtype": "markdown",
                    "markdown": {"content": chunk},
                },
            )

    async def _reply(self, frame: dict, body: dict, cmd: str = CMD_RESPOND_MSG) -> None:
        req_id = str(frame.get("headers", {}).get("req_id", ""))
        if not req_id:
            logger.warning("回调缺少 req_id，无法回复")
            return
        try:
            await self._send(
                {
                    "cmd": cmd,
                    "headers": {"req_id": req_id},
                    "body": body,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("发送机器人回复失败: %s", exc)

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _strip_mention(self, content: str) -> str:
        name = (self.settings.bot.name or "").strip()
        if name:
            for mention in (f"@{name}", "@" + name.replace(" ", "")):
                if content.startswith(mention):
                    return content[len(mention):].lstrip()
        return re.sub(r"^(?:@\S+\s*)+", "", content).strip()

    def _strip_prefix(self, content: str) -> str:
        prefix = (self.settings.bot.prefix or "").strip()
        if not prefix:
            return content
        if content == prefix:
            return ""
        if content.startswith(prefix):
            rest = content[len(prefix):]
            if rest[:1].isspace():
                return rest.strip()
        return content

    async def _is_duplicate(self, msg_id: str) -> bool:
        if not msg_id:
            return False
        now = time.time()
        async with self._seen_lock:
            for key, seen_at in list(self._seen.items()):
                if now - seen_at > 600:
                    self._seen.pop(key, None)
            if msg_id in self._seen:
                return True
            self._seen[msg_id] = now
        return False

    async def _cancel_message_tasks(self) -> None:
        tasks = [task for task in self._message_tasks if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
