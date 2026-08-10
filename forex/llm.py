"""Optional LLM commentary over the computed technical picture.

The model never sees raw candles and is never the source of numbers. It receives
the already-computed indicator readings and is asked to interpret them. If no API
key is configured, :func:`generate_commentary` returns ``None`` and the report is
still produced from deterministic analysis alone.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from .config import LLMConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an FX market analyst. You will be given pre-computed technical readings \
for one or more currency pairs across multiple timeframes.

Rules:
- Interpret only the data provided. Never invent price levels, economic data, \
news events, or numbers that are not in the input.
- Reference the session context: FX liquidity and behaviour differ between the \
Tokyo, London and New York windows.
- Quote distances in pips, matching the input.
- When timeframes conflict, say so plainly rather than forcing a directional call.
- Be concise and specific. No filler, no disclaimers about being an AI.
- This is technical commentary for educational purposes, not investment advice. \
Do not tell the user to buy or sell; describe conditions, levels and risks.

Structure your answer as:
1. Market context (one short paragraph)
2. Per-pair reading (one short paragraph each, naming the key levels)
3. What would invalidate each read
"""


class LLMError(RuntimeError):
    """The LLM call failed."""


def _post_chat_completion(config: LLMConfig, messages: list[dict]) -> str:
    import requests

    url = f"{config.base_url}/chat/completions"
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=config.timeout)
    except Exception as exc:
        raise LLMError(f"request to {url} failed: {exc}") from exc

    if response.status_code >= 400:
        # Surface the provider's message; it usually names the real problem.
        raise LLMError(f"{response.status_code} from {url}: {response.text[:400]}")

    try:
        body = response.json()
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError(f"unexpected response shape: {response.text[:400]}") from exc


def build_user_prompt(payload: Dict[str, Any]) -> str:
    """Render the analysis payload as the user message."""
    return (
        "Here is the computed technical data as JSON.\n\n"
        f"```json\n{json.dumps(payload, indent=2, default=str)}\n```\n\n"
        "Write the commentary as instructed."
    )


def generate_commentary(payload: Dict[str, Any], config: LLMConfig) -> Optional[str]:
    """Return LLM commentary, or ``None`` when disabled or failing.

    Failure is non-fatal by design: losing optional prose must not discard a
    successfully computed report.
    """
    if not config.enabled:
        logger.info("LLM commentary skipped: no API key configured")
        return None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(payload)},
    ]

    try:
        text = _post_chat_completion(config, messages)
    except LLMError as exc:
        logger.warning("LLM commentary unavailable: %s", exc)
        return None

    text = text.strip()
    return text or None
