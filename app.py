import logging
import httpx
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse

from settings import settings
from ql_client import QLClient
from vl import WXBizMsgCrypt, parse_qyxml
from commands import process_command
from menu import create_menu, handle_menu_click

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wecom")

app = FastAPI(title="Qinglong-WeCom Bridge")


@app.on_event("startup")
def _setup_menu():
    """启动时自动创建/更新企业微信应用菜单"""
    try:
        create_menu(
            corp_id=settings.wecom.corp_id,
            agent_id=settings.wecom.agent_id,
            secret=settings.wecom.corp_secret,
        )
    except Exception as e:
        logger.error(f"菜单初始化失败: {e}")


def _get_ql() -> QLClient:
    return QLClient(settings.ql.base_url)


def _get_access_token() -> str:
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {"corpid": settings.wecom.corp_id, "corpsecret": settings.wecom.corp_secret}
    try:
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()
        token = data.get("access_token", "")
        if not token:
            logger.error(f"获取token失败: {data}")
        return token
    except Exception as e:
        logger.error(f"请求token异常: {e}")
        return ""


def _send_text(user_id: str, content: str) -> bool:
    token = _get_access_token()
    if not token:
        logger.error("无token，无法发送消息")
        return False
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {
        "touser": user_id,
        "msgtype": "text",
        "agentid": settings.wecom.agent_id,
        "text": {"content": content},
        "safe": 0,
    }
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        data = resp.json()
        ok = data.get("errcode") == 0
        if not ok:
            logger.error(f"发送失败: {data}")
        return ok
    except Exception as e:
        logger.error(f"发送异常: {e}")
        return False


@app.get("/wecom/callback")
async def wecom_verify(
    msg_signature: str = Query(None),
    timestamp: str = Query(None),
    nonce: str = Query(None),
    echostr: str = Query(None),
):
    if echostr and msg_signature and timestamp and nonce:
        wxcpt = WXBizMsgCrypt(
            sToken=settings.callback.token,
            sEncodingAESKey=settings.wecom.encoding_aes_key,
            sReceiveId=settings.wecom.corp_id,
        )
        ret, echo = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
        if ret == 0:
            return PlainTextResponse(echo)
    return PlainTextResponse("ok")


@app.post("/wecom/callback")
async def wecom_callback(request: Request):
    body = await request.body()
    args = request.query_params
    s_sig = args.get("msg_signature")
    s_ts = args.get("timestamp")
    s_nonce = args.get("nonce")

    # 纯文本模式：直接解析XML，跳过加解密
    if settings.wecom.encrypt_mode == "plain":
        msg = body.decode("utf-8")
    else:
        wxcpt = WXBizMsgCrypt(
            sToken=settings.callback.token,
            sEncodingAESKey=settings.wecom.encoding_aes_key,
            sReceiveId=settings.wecom.corp_id,
        )
        ret, msg = wxcpt.DecryptMsg(body, s_sig, s_ts, s_nonce)
        if ret != 0:
            logger.error(f"解密失败: ret={ret}")
            return {"errcode": ret, "errmsg": "decrypt failed"}
        logger.info(f"解密成功, msg前200字符: {msg[:200]}")

    info = parse_qyxml(msg)
    content = info.get("content", "").strip()
    from_user = info.get("from_user", "")
    msg_type = info.get("msg_type", "")
    event = info.get("event", "")
    event_key = info.get("event_key", "")
    logger.info(f"收到消息: from={from_user}, type={msg_type}, event={event}, key={event_key}, content={content}")

    ql = _get_ql()

    try:
        # 处理菜单点击事件
        if msg_type == "event" and event == "click" and event_key:
            result = handle_menu_click(event_key, ql)
            if result:
                logger.info(f"菜单点击: key={event_key}, 回复长度={len(result)}")
            else:
                result = f"未知菜单: {event_key}"
        elif content:
            result = process_command(content, ql)
            logger.info(f"处理结果: {result[:100] if result else 'EMPTY'}")
        else:
            logger.info("消息内容为空且非菜单事件，跳过")
            return {"errcode": 0, "errmsg": "ok"}
    except Exception as e:
        logger.error(f"处理消息异常: {e}")
        result = f"❌ 操作失败：{e}\n\n请检查青龙面板连接是否正常"

    if from_user and result:
        success = _send_text(from_user, result)
        logger.info(f"发送结果: {'成功' if success else '失败'}")

    return {"errcode": 0, "errmsg": "ok"}