import logging
import httpx
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse

from settings import settings
from ql_client import QLClient
from vl import WXBizMsgCrypt, parse_qyxml
from commands import process_command

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wecom")

app = FastAPI(title="Qinglong-WeCom Bridge")


def _get_ql() -> QLClient:
    return QLClient(
        settings.ql.base_url,
        token=settings.ql.token or None,
        client_id=settings.ql.client_id or None,
        client_secret=settings.ql.client_secret or None,
    )


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
    logger.info(f"收到消息: from={from_user}, content={content}, type={info.get('msg_type')}")

    if not content:
        logger.info("消息内容为空，跳过")
        return {"errcode": 0, "errmsg": "ok"}

    ql = _get_ql()
    result = process_command(content, ql)
    logger.info(f"处理结果: {result[:100] if result else 'EMPTY'}")

    if from_user:
        success = _send_text(from_user, result)
        logger.info(f"发送结果: {'成功' if success else '失败'}")

    return {"errcode": 0, "errmsg": "ok"}