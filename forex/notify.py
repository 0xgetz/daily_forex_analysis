"""Optional notification channels.

Every sender returns a boolean and never raises: a failed push must not discard a
report that was already computed and written to disk.
"""

from __future__ import annotations

import logging
from typing import Optional

from .config import TelegramConfig

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org"


def send_telegram(text: str, config: TelegramConfig, timeout: int = 20) -> bool:
    """Send a plain-text message. Returns True on success."""
    if not config.enabled:
        logger.info("Telegram push skipped: bot token or chat id missing")
        return False

    import requests

    url = f"{_TELEGRAM_API}/bot{config.bot_token}/sendMessage"
    payload = {
        "chat_id": config.chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except Exception as exc:
        logger.warning("Telegram push failed: %s", exc)
        return False

    if response.status_code >= 400:
        # Never log the token; the URL contains it.
        logger.warning("Telegram push rejected (%s): %s", response.status_code, response.text[:200])
        return False

    return True


def notify(text: str, telegram: Optional[TelegramConfig] = None) -> dict:
    """Fan out to every configured channel, reporting per-channel outcome."""
    results = {}
    if telegram is not None:
        results["telegram"] = send_telegram(text, telegram)
    return results
