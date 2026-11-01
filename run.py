import logging

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from jbot.config import settings  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "jbot.server:app",
        host=settings.callback.host,
        port=settings.callback.port,
        workers=1,
    )
