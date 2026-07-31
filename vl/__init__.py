import hashlib
import json
import random
import socket
import struct
import time
import xml.etree.ElementTree as ET
from base64 import b64decode, b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


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
        try:
            root = ET.fromstring(sPostData)
            encrypt_elem = root.find("Encrypt")
            if encrypt_elem is None or not encrypt_elem.text:
                return WXBizMsgCrypt_ParseXml_Error, None
            encrypt = encrypt_elem.text
        except ET.ParseError:
            return WXBizMsgCrypt_ParseXml_Error, None

        ret, ok = self.get_signature(sMsgSignature, sTimeStamp, sNonce, encrypt)
        if not ok:
            return WXBizMsgCrypt_ComputeSignature_Error, None

        try:
            cipher = AES.new(self._aes_key, AES.MODE_CBC, self._aes_key[:16])
            decrypted = unpad(cipher.decrypt(b64decode(encrypt)), AES.block_size)
        except Exception:
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