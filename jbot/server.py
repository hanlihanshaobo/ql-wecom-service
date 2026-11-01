"""FastAPI 回调服务：接收企业微信消息/菜单事件，调用青龙 API 并回复。"""

from __future__ import annotations

import asyncio
import hmac
import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from .commands import process_command
from .config import Settings, settings as default_settings
from .crypto import WXBizMsgCrypt, parse_qyxml, verify_signature
from .menu import MENU, handle_menu_click
from .ql_client import QLClient
from .wecom import WeComClient

logger = logging.getLogger("wecom")

# 企业微信回调超时为 5 秒，重复推送时用 MsgId 去重，避免脚本被执行两次。
_seen_messages: dict[str, float] = {}
_seen_lock = threading.Lock()
_SEEN_TTL = 600


def _is_duplicate(msg_id: str) -> bool:
    if not msg_id:
        return False
    now = time.time()
    with _seen_lock:
        for key, seen_at in list(_seen_messages.items()):
            if now - seen_at > _SEEN_TTL:
                _seen_messages.pop(key, None)
        if msg_id in _seen_messages:
            return True
        _seen_messages[msg_id] = now
    return False


def _make_wecom(settings: Settings) -> WeComClient:
    return WeComClient(
        corp_id=settings.wecom.corp_id,
        agent_id=settings.wecom.agent_id,
        secret=settings.wecom.corp_secret,
        api_base=settings.wecom.api_base,
    )


def _make_ql(settings: Settings) -> QLClient:
    return QLClient(
        settings.ql.base_url,
        client_id=settings.ql.client_id or None,
        client_secret=settings.ql.client_secret or None,
        host_header=settings.ql.host or None,
    )


def _strip_prefix(content: str, prefix: str) -> str:
    if not prefix:
        return content
    stripped = content.strip()
    if stripped == prefix:
        return ""
    if stripped.startswith(prefix):
        rest = stripped[len(prefix):]
        if rest[:1].isspace():
            return rest.strip()
    return content


def _secret_ok(settings: Settings, request: Request) -> bool:
    """明文回调模式下的额外共享密钥校验，防止公网 URL 被随意调用。"""
    expected = settings.callback.secret
    if not expected:
        return True
    provided = (
        request.query_params.get("secret")
        or request.query_params.get("key")
        or request.headers.get("X-Webhook-Secret", "")
    )
    return bool(provided) and hmac.compare_digest(
        provided.encode("utf-8"), expected.encode("utf-8")
    )


def _make_crypt(settings: Settings) -> WXBizMsgCrypt | None:
    try:
        return WXBizMsgCrypt(
            sToken=settings.callback.token,
            sEncodingAESKey=settings.wecom.encoding_aes_key,
            sReceiveId=settings.wecom.corp_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("初始化企业微信加解密失败: %s", exc)
        return None


def _handle_and_reply(
    settings: Settings,
    wecom: WeComClient,
    from_user: str,
    content: str,
    msg_type: str,
    event: str,
    event_key: str,
) -> None:
    """后台处理消息/事件并回复，避免阻塞企业微信回调导致超时重试。"""
    allowed = settings.bot.allowed_users
    if allowed and from_user not in allowed:
        logger.warning("未授权用户: %s", from_user)
        if from_user:
            wecom.send_text(from_user, "⛔ 无权限使用此机器人")
        return

    result = ""
    try:
        if msg_type == "event" and event == "click" and event_key:
            result = handle_menu_click(event_key, _make_ql(settings))
            if result:
                logger.info("菜单点击: key=%s, 回复长度=%s", event_key, len(result))
            else:
                result = f"未知菜单: {event_key}"
        elif content:
            content = _strip_prefix(content, settings.bot.prefix)
            if not content:
                result = "请输入指令，例如：任务、变量、系统、帮助"
            else:
                result = process_command(content, _make_ql(settings))
                logger.info("处理结果: %s", result[:100] if result else "EMPTY")
        else:
            logger.info("消息内容为空且非菜单事件，跳过")
            return
    except Exception as exc:  # noqa: BLE001 - 回复用户比抛出异常更有用
        logger.exception("处理消息异常: %s", exc)
        result = f"❌ 操作失败：{exc}\n\n请检查青龙面板连接是否正常"

    if from_user and result:
        success = wecom.send_text(from_user, result)
        logger.info("发送结果: %s", "成功" if success else "失败")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or default_settings
    wecom = _make_wecom(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("青龙企业微信机器人启动")
        logger.info("配置文件: %s", settings.config_file or "(未找到，使用环境变量/默认值)")
        logger.info("监听地址: %s:%s%s", settings.callback.host, settings.callback.port, settings.callback.path)
        if settings.callback.public_url:
            logger.info(
                "公网回调地址: %s%s",
                settings.callback.public_url.rstrip("/"),
                settings.callback.path,
            )
        logger.info("青龙 API: %s", settings.ql.base_url)
        if not (settings.ql.client_id and settings.ql.client_secret):
            logger.warning(
                "青龙 OpenAPI 客户端未配置：请在 config/bot.json 的 qinglong 节点填写 "
                "client_id / client_secret（青龙 系统设置 → 应用设置）"
            )
        if settings.wecom.plain_mode and not settings.callback.secret:
            logger.warning(
                "明文回调模式未设置 callback.secret：任何能访问回调 URL 的人都可以调用机器人。"
                "建议改用 SAFETY 加密模式，或设置 callback.secret 并在回调 URL 后追加 ?secret=..."
            )
        if settings.wecom.configured:
            try:
                await asyncio.to_thread(wecom.create_menu, MENU)
            except Exception as exc:  # noqa: BLE001
                logger.error("菜单初始化失败: %s", exc)
        else:
            logger.warning("企业微信未配置完整，跳过菜单初始化；仍可通过文本指令调用")
        yield

    app = FastAPI(title="Qinglong WeCom Bot", lifespan=lifespan)
    app.state.settings = settings
    app.state.wecom = wecom

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "bot": settings.bot.name,
            "wecom_configured": settings.wecom.configured,
            "callback_path": settings.callback.path,
            "qinglong": settings.ql.base_url,
        }

    @app.get(settings.callback.path)
    async def wecom_verify(
        request: Request,
        msg_signature: str = Query(None),
        signature: str = Query(None),
        timestamp: str = Query(None),
        nonce: str = Query(None),
        echostr: str = Query(None),
    ):
        if not _secret_ok(settings, request):
            logger.warning("回调 secret 校验失败: %s", request.client)
            return PlainTextResponse("forbidden", status_code=403)
        if not echostr:
            return PlainTextResponse("ok")

        # 优先按加密模式验证；企业微信自建应用回调实际总是加密的。
        if settings.wecom.encoding_aes_key and (msg_signature or signature):
            wxcpt = _make_crypt(settings)
            if wxcpt is None:
                return PlainTextResponse("crypto init failed", status_code=500)
            ret, echo = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
            if ret == 0:
                return PlainTextResponse(echo)
            if not settings.wecom.plain_mode:
                logger.error("企业微信 URL 验证失败: ret=%s", ret)
                return PlainTextResponse("forbidden", status_code=403)

        # 明文兼容：仅当没有可用的 AES 密钥，或加密验证失败且显式配置 NORMAL 时使用。
        if settings.wecom.plain_mode:
            if settings.callback.token:
                if msg_signature:
                    if not verify_signature(
                        settings.callback.token, msg_signature, timestamp, nonce, echostr
                    ):
                        logger.warning("明文回调签名校验失败: %s", request.client)
                        return PlainTextResponse("forbidden", status_code=403)
                elif signature:
                    if not verify_signature(
                        settings.callback.token, signature, timestamp, nonce, ""
                    ):
                        logger.warning("明文回调签名校验失败: %s", request.client)
                        return PlainTextResponse("forbidden", status_code=403)
                else:
                    logger.warning("明文回调缺少签名: %s", request.client)
                    return PlainTextResponse("forbidden", status_code=403)
            return PlainTextResponse(echostr)

        logger.error("收到无法验证的回调：未配置 encoding_aes_key")
        return PlainTextResponse("forbidden", status_code=403)

    @app.post(settings.callback.path)
    async def wecom_callback(request: Request, background_tasks: BackgroundTasks):
        if not _secret_ok(settings, request):
            logger.warning("回调 secret 校验失败: %s", request.client)
            return JSONResponse({"errcode": -1, "errmsg": "forbidden"}, status_code=403)

        body = await request.body()
        args = request.query_params
        signature = args.get("msg_signature")
        timestamp = args.get("timestamp")
        nonce = args.get("nonce")

        body_text = body.decode("utf-8", errors="replace")
        encrypted = "<Encrypt>" in body_text
        if encrypted:
            if not settings.wecom.encoding_aes_key:
                logger.error("收到加密回调，但未配置 encoding_aes_key")
                return JSONResponse(
                    {"errcode": -1, "errmsg": "missing aes key"}, status_code=403
                )
            wxcpt = _make_crypt(settings)
            if wxcpt is None:
                return JSONResponse(
                    {"errcode": -1, "errmsg": "crypto init failed"}, status_code=500
                )
            ret, msg = wxcpt.DecryptMsg(body, signature, timestamp, nonce)
            if ret != 0:
                logger.error("企业微信消息解密失败: ret=%s", ret)
                return JSONResponse(
                    {"errcode": ret, "errmsg": "decrypt failed"}, status_code=403
                )
        else:
            msg = body_text
            if not settings.wecom.plain_mode:
                logger.warning("SAFETY 模式收到未加密的回调: %s", request.client)
                return JSONResponse(
                    {"errcode": -1, "errmsg": "plaintext not allowed"}, status_code=403
                )
            if settings.callback.token:
                plain_signature = args.get("signature")
                if plain_signature:
                    if not verify_signature(
                        settings.callback.token, plain_signature, timestamp, nonce, ""
                    ):
                        logger.warning("明文回调签名校验失败: %s", request.client)
                        return JSONResponse(
                            {"errcode": -1, "errmsg": "forbidden"}, status_code=403
                        )
                elif signature:
                    if not verify_signature(
                        settings.callback.token, signature, timestamp, nonce, msg
                    ):
                        logger.warning("明文回调签名校验失败: %s", request.client)
                        return JSONResponse(
                            {"errcode": -1, "errmsg": "forbidden"}, status_code=403
                        )
                else:
                    logger.warning("明文回调缺少签名: %s", request.client)
                    return JSONResponse(
                        {"errcode": -1, "errmsg": "forbidden"}, status_code=403
                    )

        try:
            info = parse_qyxml(msg)
        except Exception as exc:  # noqa: BLE001
            logger.error("解析企业微信消息失败: %s", exc)
            return JSONResponse({"errcode": -1, "errmsg": "parse failed"})

        content = info.get("content", "").strip()
        from_user = info.get("from_user", "")
        msg_type = info.get("msg_type", "")
        event = info.get("event", "")
        event_key = info.get("event_key", "")
        msg_id = info.get("msg_id", "")

        logger.info(
            "收到消息: from=%s, type=%s, event=%s, key=%s, msg_id=%s, content=%s",
            from_user, msg_type, event, event_key, msg_id, content,
        )

        if _is_duplicate(msg_id):
            logger.info("重复消息，已忽略: msg_id=%s", msg_id)
            return JSONResponse({"errcode": 0, "errmsg": "ok"})

        if not content and not (msg_type == "event" and event == "click" and event_key):
            logger.info("消息内容为空且非菜单事件，跳过")
            return JSONResponse({"errcode": 0, "errmsg": "ok"})

        background_tasks.add_task(
            _handle_and_reply,
            settings,
            wecom,
            from_user,
            content,
            msg_type,
            event,
            event_key,
        )
        return JSONResponse({"errcode": 0, "errmsg": "ok"})

    return app


app = create_app()
