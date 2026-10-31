import uvicorn

from sheepbot.config import get_settings
from sheepbot.log import setup_logging


def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    uvicorn.run(
        "sheepbot.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
        proxy_headers=True,
    )


if __name__ == "__main__":
    run()
