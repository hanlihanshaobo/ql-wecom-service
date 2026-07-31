import hashlib
import json
import logging
import random
import socket
import struct
import time
import traceback
import xml.etree.ElementTree as ET
from base64 import b64decode, b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

logger = logging.getLogger("wecom")


WXBizMsgCrypt_OK = 0
WXBizMsgCrypt_ValidateSignature_Error = -40001
WXBizMsgCrypt_ParseXml_Error = -40002
WXBizMsgCrypt_ComputeSignature_Error = -40003
WXBizMsgCrypt_IllegalAesKey = -40004
WXBizMsgCrypt_ValidateCorpid_Error = -40005
WXBizMsgCrypt_DecryptAES_Error = -40007


def _sha1(token, timestamp, nonce, encrypt):
    sortlist = [token, timestamp, nonce, encrypt]
    sortlist.sort()
    raw = "".join(sortlist)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _generate_random_str(length=16):
    return "".join([str(random.randint(0, 9)) for _ in range(length)])


class WXBizMsgCrypt:
    def __init__(self, sToken, sEncodingAESKey, sReceiveId):
        self.token = sToken
        self.encoding_aes_key = sEncodingAESKey
        self.receive_id = sReceiveId
        self._aes_key = None
        if sEncodingAESKey:
            self._aes_key = b64decode(sEncodingAESKey + "=")

    def get_signature(self, sMsgSignature, sTimeStamp, sNonce, sEchoStr=""):
        if sMsgSignature:
            return 0, sMsgSignature == _sha1(self.token, sTimeStamp, sNonce, sEchoStr)
        return 0, True

    def VerifyURL(self, sMsgSignature, sTimeStamp, sNonce, sEchoStr):
        ret, ok = self.get_signature(sMsgSignature, sTimeStamp, sNonce, sEchoStr)
        if not ok:
            return WXBizMsgCrypt_ComputeSignature_Error, None
        # 解密 echostr 返回明文，IV 为 key 前 16 字节
        try:
            cipher = AES.new(self._aes_key, AES.MODE_CBC, self._aes_key[:16])
            decrypted = unpad(cipher.decrypt(b64decode(sEchoStr)), AES.block_size)
            # 格式: random(16) | msg_len(4) | msg | receive_id
            msg_len = struct.unpack(">I", decrypted[16:20])[0]
            plain = decrypted[20:20 + msg_len].decode("utf-8")
            return WXBizMsgCrypt_OK, plain
        except Exception:
            return WXBizMsgCrypt_DecryptAES_Error, None

    def DecryptMsg(self, sPostData, sMsgSignature, sTimeStamp, sNonce):
        logger.info(f"DecryptMsg: body_len={len(sPostData)}, sig={sMsgSignature}, ts={sTimeStamp}, nonce={sNonce}")
        try:
            root = ET.fromstring(sPostData)
            encrypt_elem = root.find("Encrypt")
            if encrypt_elem is None or not encrypt_elem.text:
                logger.error(f"XML解析后找不到Encrypt字段: root_tag={root.tag}")
                return WXBizMsgCrypt_ParseXml_Error, None
            encrypt = encrypt_elem.text
            logger.info(f"encrypt密文前80字符: {encrypt[:80]}")
        except ET.ParseError as e:
            logger.error(f"XML解析失败: {e}")
            return WXBizMsgCrypt_ParseXml_Error, None

        ret, ok = self.get_signature(sMsgSignature, sTimeStamp, sNonce, encrypt)
        if not ok:
            logger.error(f"签名验证失败")
            return WXBizMsgCrypt_ComputeSignature_Error, None
        logger.info("签名验证通过")

        logger.info(f"aes_key前8字节: {self._aes_key[:8].hex()}, 长度: {len(self._aes_key)}")
        try:
            raw = b64decode(encrypt)
            logger.info(f"base64解码后长度: {len(raw)}")
            cipher = AES.new(self._aes_key, AES.MODE_CBC, self._aes_key[:16])
            decrypted = cipher.decrypt(raw)
            logger.info(f"AES解密后前32字节hex: {decrypted[:32].hex()}")
            logger.info(f"AES解密后最后32字节hex: {decrypted[-32:].hex()}")
            decrypted = unpad(decrypted, AES.block_size)
        except Exception as e:
            logger.error(f"AES解密/去填充失败: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            return WXBizMsgCrypt_DecryptAES_Error, None

        # 格式: random(16) | msg_len(4) | msg | receive_id
        msg_len = struct.unpack(">I", decrypted[16:20])[0]
        msg = decrypted[20:20 + msg_len].decode("utf-8")
        receive_id = decrypted[20 + msg_len:].decode("utf-8")

        if receive_id != self.receive_id:
            return WXBizMsgCrypt_ValidateCorpid_Error, None

        return WXBizMsgCrypt_OK, msg


def parse_qyxml(xml_str):
    root = ET.fromstring(xml_str)
    return {
        "msg_type": root.findtext("MsgType", ""),
        "content": root.findtext("Content", ""),
        "from_user": root.findtext("FromUserName", ""),
        "to_user": root.findtext("ToUserName", ""),
        "event": root.findtext("Event", ""),
        "event_key": root.findtext("EventKey", ""),
        "agent_id": root.findtext("AgentID", ""),
    }