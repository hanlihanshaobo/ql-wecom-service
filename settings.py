from dataclasses import dataclass, field
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


@dataclass
class WecomConfig:
    corp_id: str = getenv("WE_COM_CORP_ID", "")
    agent_id: str = getenv("WE_COM_AGENT_ID", "")
    corp_secret: str = getenv("WE_COM_CORP_SECRET", "")
    encoding_aes_key: str = getenv("WE_COM_ENCODING_AES_KEY", "")
    encrypt_mode: str = getenv("WE_COM_ENCRYPT_MODE", "plain")


@dataclass
class CallbackConfig:
    host: str = getenv("CALLBACK_HOST", "0.0.0.0")
    port: int = int(getenv("CALLBACK_PORT", "3000"))
    token: str = getenv("CALLBACK_TOKEN", "")


@dataclass
class QLConfig:
    base_url: str = getenv("QL_BASE_URL", "http://127.0.0.1:5700")
    client_id: str = getenv("QL_CLIENT_ID", "")
    client_secret: str = getenv("QL_CLIENT_SECRET", "")
    host: str = getenv("QL_HOST", "")


@dataclass
class BotConfig:
    prefix: str = getenv("BOT_PREFIX", "")
    name: str = getenv("BOT_NAME", "QinglongBot")


@dataclass
class Settings:
    wecom: WecomConfig = field(default_factory=WecomConfig)
    callback: CallbackConfig = field(default_factory=CallbackConfig)
    ql: QLConfig = field(default_factory=QLConfig)
    bot: BotConfig = field(default_factory=BotConfig)


settings = Settings()