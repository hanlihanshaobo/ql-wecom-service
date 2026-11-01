"""兼容旧的企业微信加解密工具导入；实现已迁移到 jbot.crypto。"""

from jbot.crypto import *  # noqa: F401,F403
from jbot.crypto import _generate_random_str, _sha1  # noqa: F401
